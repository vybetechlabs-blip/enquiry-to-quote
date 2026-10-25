# enquiry-to-quote

**Status: Active, Phase 1 complete except the Claude Haiku row (needs an API key), public standard pending.**

An inbound inquiry (an email or a web-form submission) goes in. A priced draft quote comes out and waits in an approval queue. Nothing is sent until a person approves it.

The pipeline:

1. **Extract** the job into a typed record: service, frequency, sites and floor area, add-ons, anything out of scope. Each field has a confidence score, and fields that could not be read are listed as missing.
2. **Price** it with a pure function over a YAML rate card (`business/pricing.yaml`). No language model touches the price. Every quote lists the assumptions and the rule ids that produced each line.
3. **Draft** one of three replies from templates:
   - a **quote**: line items, total, the assumptions in plain words, and how long the price is valid;
   - a **clarification**: asks for exactly the missing fields and nothing else;
   - a **handoff**: an internal note for a person when the job is out of scope, the numbers fall outside the rate card's sanity band, the message tries to instruct the system, or it is not an inquiry at all.
4. **Queue** the draft for approval (one SQLite file).
5. **Send** only an approved or edited draft. The default sender writes the email to `outbox/` instead of sending it.

The business in `business/` is **fictional**: Fernwick Commercial Cleaning, a commercial cleaning company invented for this demo, with an invented rate card. The 19 inquiries in `inbox/samples/` are synthetic.

## The approval boundary

Drafts move through `drafted` → `approved` | `edited` | `rejected` → `sent`.

- `send` refuses any draft that is not `approved` or `edited` (an edit by the owner counts as approval).
- Handoff notes are never sent; they are for a person to read.
- The send log is keyed by inquiry id and draft version. A second send of the same key is refused with an error (exit code 3). It is never skipped silently.
- Every transition is logged with a timestamp and an actor.

## Run it on a fresh Windows machine

Needs Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). From PowerShell:

```powershell
git clone https://github.com/vybetechlabs-blip/enquiry-to-quote.git
cd enquiry-to-quote
uv sync
uv run pytest
```

Walk the whole pipeline with the sample inbox (no API key or account needed):

```powershell
uv run e2q ingest "inbox/samples/*.json"   # extract, price, draft, queue
uv run e2q list                            # every draft with its kind, state and total
uv run e2q show s10-two-sites              # one draft, what was extracted, its history
uv run e2q send s10-two-sites              # refused: not approved (exit code 2)
uv run e2q approve s10-two-sites
uv run e2q send s10-two-sites              # writes outbox/s10-two-sites-v1.eml
uv run e2q send s10-two-sites              # refused: already sent (exit code 3)
uv run e2q eval                            # golden set -> eval/REPORT.md
```

`e2q` expands the glob itself, because PowerShell passes `*.json` through unexpanded. The queue lives in `e2q.db` in the current folder; set `E2Q_DB` or pass `--db` to use another file. To start over, delete `e2q.db`.

Other commands: `e2q edit <id> --body-file reply.txt [--subject "..."]` saves a new version in state `edited`; `e2q reject <id> --note "..."` closes a draft for good.

## Configuration

- `business/pricing.yaml`: services and rates, frequency multipliers and visits a month, minimum charge per visit, add-ons, multi-site discount, sanity band, out-of-scope services. `area_unit` is `sqft` or `sqm`; inquiries in the other unit are converted, and the quote says so.
- `business/business.yaml`: business name, reply address, sign-off, and the keyword maps the deterministic extractor uses.
- `business/templates/`: the three reply templates.

## Evaluation

`uv run e2q eval` scores every extractor on two golden sets and writes `eval/REPORT.md`: field-level extraction accuracy, outcome accuracy (quote, clarification or handoff), whether each expected quote total matches to the cent, and whether each clarification asks for exactly the missing fields.

- **Original set** (`eval/golden.yaml`, `inbox/samples/`): written together with `RuleExtractor`, so its score shows that the pieces agree with each other, not how well they read real inquiries.
- **Held-out set** (`eval/holdout.yaml`, `inbox/holdout/`): 15 inquiries written separately, without sight of the extractor or the original samples. This is the better guide to accuracy.

`RuleExtractor`, a deterministic regex and keyword reader, is the keyless baseline. LLM rows are added with `--llm provider:model` and saved to `eval/runs/` (one pass each, with tokens, latency and the prompt hash per call), so the report can be rebuilt without calling a model again:

```powershell
uv run e2q eval --llm ollama:gpt-oss:20b          # local model; it must already be pulled
uv run e2q eval --llm anthropic:claude-haiku-5-5  # needs ANTHROPIC_API_KEY and: uv sync --extra llm
uv run e2q eval --llm ollama:gpt-oss:20b --prompt v2 --passes 3 --guard
```

## Model providers

`LLMExtractor` sends one call per inquiry through `e2q/providers.py`: Ollama at `127.0.0.1` (never pulls a model), or Anthropic when `ANTHROPIC_API_KEY` is set and a model id is given. Its prompt holds the extraction schema and the service, frequency, add-on and out-of-scope categories from `business/pricing.yaml`; the model never sees a price and never sets one. A reply that does not fit the schema sends the inquiry to a person.

`uv run e2q ingest --llm ollama:gpt-oss:20b "inbox/samples/*.json"` uses the model for extraction and for a short cover note at the top of a quote. A cover note that states any number not already in the quote is dropped and the template's opening line is used instead.

Prompts are versioned (`--prompt v1` or `v2`), and every saved run records the prompt's hash, so results from different prompts are never mixed. Ollama runs start with one warm-up call that is not scored, and retry a call once on a server error or a dropped connection. A reply that fails parsing or the schema is never retried; the inquiry goes to a person.

### Repeatability

- `gpt-oss:20b` runs with sampling pinned (temperature 0, seed 42) and still varies between passes: in the measured runs, s10 (original set) and k02 (held-out set 2) changed outcome from one pass to another. My reading is non-determinism in the GPU runtime; I have not verified the cause.
- `claude-haiku-5-5` takes no temperature or seed through the Messages API, so effort (`low`) is its only setting and its passes can differ.

### The guard (`--guard`, off by default)

With `--guard`, `RuleExtractor` reads each inquiry too, and the inquiry goes to a person when the two disagree on any field a quote needs. Measured with prompt v2 over three passes (`eval/REPORT.md`), scored on the same model outputs with the guard off and on:

| Row | Original set | Held-out set 1 | Held-out set 2 |
|---|---|---|---|
| `claude-haiku-5-5`, guard off / on | 25.0 / 24.0 of 25 | 15.0 / 10.0 of 15 | 15.0 / 11.0 of 15 |
| `gpt-oss:20b`, guard off / on | 24.7 / 23.7 of 25 | 14.0 / 10.0 of 15 | 14.7 / 10.0 of 15 |

- **What it cost:** every extra handoff came from `RuleExtractor` misreading an inquiry that the model had read correctly.
- **What it caught:** nothing. Neither model produced a wrong quote in any pass.

It stays an optional flag until a model is measured that sometimes quotes wrongly.

A real sender (`--sender resend`) exists behind `RESEND_API_KEY` and is never exercised by the tests.

## Roadmap

- **Phase 1:** LLM extraction side by side with `RuleExtractor` on both golden sets; cost and latency per inquiry; the cover note.
- **Phase 2:** documentation and CI to the public standard.
- **Phase 3 (later):** a web-form intake endpoint, CRM write-back, and a small approval UI.

## License

MIT. See [LICENSE](LICENSE).
