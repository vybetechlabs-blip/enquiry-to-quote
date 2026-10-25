# enquiry-to-quote

**Status: Active, Phase 0 complete, LLM mode pending.**

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

`uv run e2q eval` runs every sample in the golden set (`eval/golden.yaml`) end to end and writes `eval/REPORT.md`: field-level extraction accuracy, outcome accuracy (quote, clarification or handoff) and whether each expected quote total matches to the cent. The expected values were written by hand from the sample text and the rate card.

The current extractor is `RuleExtractor`, a deterministic regex and keyword reader. It exists so the tests and the demo run without any key. Its golden-set score shows that the pieces agree with each other. It does not predict how it would do on real inquiries, because the samples and the extractor were written together.

## Model providers

LLM mode (`--llm`) is not wired yet. `e2q/providers.py` already holds the factory it will use: a scripted provider for tests, Ollama at `127.0.0.1` if it is running, and Anthropic when `ANTHROPIC_API_KEY` is set and a model id is given. A model may extract fields and write a cover note. The rate card still sets every number.

A real sender (`--sender resend`) exists behind `RESEND_API_KEY` and is never exercised by the tests.

## Roadmap

- **Phase 1:** LLM extraction on the same golden set, side by side with `RuleExtractor`; cost per inquiry; an optional cover note that may not state any number absent from the quote.
- **Phase 2:** documentation and CI to the public standard.
- **Phase 3 (later):** a web-form intake endpoint, CRM write-back, and a small approval UI.

## License

MIT. See [LICENSE](LICENSE).
