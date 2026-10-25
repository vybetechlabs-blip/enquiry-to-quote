# enquiry-to-quote

[![CI](https://github.com/vybetechlabs-blip/enquiry-to-quote/actions/workflows/ci.yml/badge.svg)](https://github.com/vybetechlabs-blip/enquiry-to-quote/actions/workflows/ci.yml)

**Status: Active, Phase 1 complete, public release pending.**

## Problem and result
A service business that answers inquiries by hand reads each message, works out a price, and writes the reply hours later. This repo is a proof of concept for the first half of that job. An inquiry arrives as an email or a web-form submission. It comes out as a priced draft reply that waits for a person to approve it. A language model may read the inquiry, but it never sets a price: prices come from a rate card through a pure function, and every quote lists the rules that produced each line.

The business is fictional: Fernwick Commercial Cleaning, with an invented rate card. All the inquiries are synthetic. Results from `uv run e2q eval` (full tables in [`eval/REPORT.md`](eval/REPORT.md), per-call records in [`eval/runs/`](eval/runs/)):

| Extractor | Original set (25) | Held-out set 1 (15) | Held-out set 2 (15) |
| --- | --- | --- | --- |
| `RuleExtractor` (keyless baseline) | 24/25 | 7/15 | 11/15 |
| `claude-haiku-5-5`, prompt v2, mean of 3 passes | 25.0/25 | 15.0/15 | 15.0/15 |
| `gpt-oss:20b` (local), prompt v2, mean of 3 passes | 24.7/25 | 14.0/15 | 14.7/15 |

The figures count correct outcomes: quote, clarification or handoff. Across every pass on every set, neither model produced a quote with a wrong total, or a quote where a person should have taken over. The keyless baseline produced 7 such quotes on the held-out sets. The approval step is what stands between those and a customer.

**How blind the held-out sets are.** Both were written in a separate Claude chat session that had not seen the extractor code or the original samples (provenance in each file's header).
- **Held-out set 1 is not blind** for the model rows: the prompt was written after it had been seen.
- **Held-out set 2 is blind as written:** it was produced after the prompt was frozen, and nobody looked at it before the first scored run.
  - On set 2, Haiku with prompt v2 chose the right outcome for all 15 inquiries, both before and after one owner correction to the answer key (k09, recorded in [`eval/holdout2.yaml`](eval/holdout2.yaml)). It priced all 9 expected quotes to the cent.
  - Counting a case as fully correct only when the outcome, the total and the fields a clarification asks for all match, it got 13/15 under the original key and 14/15 after the correction.
  - The remaining miss is k08: Haiku also asks which service the customer means, and under the owner's answer key, which reads "clean an office" as regular cleaning, that counts as a miss.

Haiku costs $0.000331 per inquiry at the published price, with a mean latency of 1.8 s. `gpt-oss:20b` runs locally at no per-token charge, with a mean latency of 4.2 s.

### How it works
```
email / web form ──▶ extractor ──▶ Enquiry (typed fields, confidence, missing fields)
                     RuleExtractor            │
                     or LLMExtractor          ▼
                     (--llm)        pricing: pure function over business/pricing.yaml
                                              │
                         ┌────────────────────┼─────────────────────┐
                         ▼                    ▼                     ▼
                       quote            clarification            handoff
                (lines, total,        (asks exactly the     (internal note: out of
                 assumptions,          missing fields)       scope, outside the rate
                 rule ids)                                   card's band, injection,
                         │                    │              not an inquiry)
                         └──────────┬─────────┘
                                    ▼
                approval queue (SQLite): drafted → approved | edited | rejected → sent
                                    │
                                    ▼
                sender: DryRunSender writes outbox/ (a Resend sender exists behind a key)
```

The package follows the pipeline: `e2q/extract` (`rules.py`, `llm.py`, `guard.py`), `pricing.py`, `draft.py`, `queue.py`, `senders.py` and `providers.py`, with `cli.py` on top and `evaluate.py` plus `rescore.py` for measurement. Tests live in `tests/`, grouped by stage.

### The approval boundary
- `send` refuses any draft that is not `approved` or `edited`; an edit by the owner counts as approval. Handoff notes are never sent.
- The send log is keyed by inquiry id and draft version. A second send of the same key is refused with an error (exit code 3); it is never skipped silently.
- Every transition is logged with a timestamp and an actor.

## Decision log
**1. Pricing is a pure function over a rate card.**
Chosen: `business/pricing.yaml` sets every number: service rates, frequency multipliers, a per-visit minimum, add-ons, a multi-site discount and a sanity band. A quote carries the rule id behind each line and states its assumptions.
Rejected: letting a model estimate or adjust prices. Then a quote would be only as reliable as the model on its best day, and no price could be traced to a rule. A model-written cover note is dropped if it states any number that is not already in the quote.

**2. A person approves every reply.**
Chosen: drafts wait in a queue, and nothing is sent unless it is approved or edited. A second send of the same draft version is an error.
Rejected: sending quotes automatically. The baseline extractor produced seven wrong quotes on the held-out sets; the approval step is where they would be caught.

**3. A keyless baseline, with model extraction behind a flag.**
Chosen: `RuleExtractor` (regexes and keyword maps) runs with no key and makes the tests deterministic. `--llm provider:model` swaps in `LLMExtractor`. Its prompt carries the extraction schema and the rate card's categories with their labels, and none of the baseline's keyword maps.
Rejected: model-only extraction. Without the baseline there is nothing to measure against, and the tests would need a key.

**4. Held-out sets, frozen prompts, and failures as test cases.**
Chosen: two held-out sets written in a separate Claude session. Prompts are versioned (v1 `c721c7a1570d`, v2 `00398ad6cd42`), and every saved run records the prompt and golden-file hashes. When a model row fails a case, the failure pattern becomes a new golden case in new wording; the prompt is not quietly edited.
Rejected: tuning the prompt against the cases it is scored on, which makes the score say little about new inquiries.

**5. The guard stays off by default.**
Chosen: `--guard` is an option. It also runs `RuleExtractor` and hands the inquiry to a person when the two disagree on a field a quote needs. Scored on the same model outputs, it turned correct results into handoffs (for Haiku: 15.0 to 10.0 of 15 on held-out set 1, and 15.0 to 11.0 on set 2) and caught no wrong quote, because neither model produced one.
Rejected: turning it on by default. On this data it costs automation and buys no safety; it may earn its place with a model that sometimes quotes wrongly.

## How AI was used
> **PLACEHOLDER: the owner writes this section.** It is deliberately not drafted. Leave this note in place until the owner's text replaces it.

## Run it locally
You need Python 3.11 or newer and [uv](https://docs.astral.sh/uv/). These commands are for PowerShell; they also work in bash.

```powershell
git clone https://github.com/vybetechlabs-blip/enquiry-to-quote.git
cd enquiry-to-quote
uv sync
uv run pytest                              # 119 tests, no key or network needed
uv run ruff check . ; uv run ruff format --check .
```

Walk the pipeline with the sample inbox. It needs no API key or account:

```powershell
uv run e2q ingest "inbox/samples/*.json"   # extract, price, draft, queue
uv run e2q list                            # every draft with its kind, state and total
uv run e2q show s10-two-sites              # one draft, what was extracted, its history
uv run e2q send s10-two-sites              # refused: not approved (exit code 2)
uv run e2q approve s10-two-sites
uv run e2q send s10-two-sites              # writes outbox/s10-two-sites-v1.eml
uv run e2q send s10-two-sites              # refused: already sent (exit code 3)
uv run e2q eval                            # all golden sets -> eval/REPORT.md
```

- `e2q` expands the glob itself, because PowerShell passes `*.json` through unexpanded.
- The queue lives in `e2q.db` in the current folder; set `E2Q_DB` or pass `--db` to use another file.
- `e2q edit <id> --body-file reply.txt` saves a new version in state `edited`, and `e2q reject <id> --note "..."` closes a draft for good.

### Model-backed extraction (optional)
```powershell
uv run e2q ingest --llm ollama:gpt-oss:20b --prompt v2 "inbox/samples/*.json"   # a local model, already pulled
uv sync --extra llm                                                             # for Anthropic models
$env:ANTHROPIC_API_KEY = "<your key>"
uv run e2q eval --llm anthropic:claude-haiku-5-5 --prompt v2 --passes 3 --guard
```

- **Saved runs:** LLM rows are saved to `eval/runs/`, one file per pass, with tokens, latency and retries per call. `e2q eval` rebuilds the report from them without calling a model again.
- **Re-scoring:** `e2q rescore` re-scores saved runs after a pricing or answer-key change. It calls a model only for cases a run never saw.
- **Ollama reliability:** Ollama runs start with one warm-up call, which is not scored. A call is retried once on a server error or a dropped connection. A reply that fails the schema is never retried; the inquiry goes to a person.

### Repeatability
- `gpt-oss:20b` runs with sampling pinned (temperature 0, seed 42) and still varies between passes. In the measured runs, s10 (original set) and k02 (held-out set 2) changed outcome between passes. My reading is non-determinism in the GPU runtime; the cause is not verified.
- `claude-haiku-5-5` takes no temperature or seed through the Messages API, so effort (`low`) is its only setting and its passes can differ.

### The guard (`--guard`, off by default)
With `--guard`, `RuleExtractor` reads each inquiry too, and the inquiry goes to a person when the two disagree on any field a quote needs. Measured with prompt v2 over three passes, scored on the same model outputs with the guard off and on:

| Row | Original set | Held-out set 1 | Held-out set 2 |
|---|---|---|---|
| `claude-haiku-5-5`, guard off / on | 25.0 / 24.0 of 25 | 15.0 / 10.0 of 15 | 15.0 / 11.0 of 15 |
| `gpt-oss:20b`, guard off / on | 24.7 / 23.7 of 25 | 14.0 / 10.0 of 15 | 14.7 / 10.0 of 15 |

- **What it cost:** every extra handoff came from `RuleExtractor` misreading an inquiry that the model had read correctly.
- **What it caught:** nothing. Neither model produced a wrong quote in any pass.

### Configuration
- **`business/pricing.yaml`:** services and rates, frequency multipliers and visits a month, the minimum charge per visit, add-ons, the multi-site discount, the sanity band and out-of-scope services.
  - `area_unit` is `sqft` or `sqm`. Inquiries in the other unit are converted, and the quote says so.
  - A site outside the sanity band goes to a person even when other fields are missing.
- **`business/business.yaml`:** business name, reply address, sign-off, and the baseline extractor's keyword maps.
- **`business/templates/`:** the quote, clarification and handoff templates.

## Roadmap
- **Phase 3 (not started):** a web-form intake endpoint, CRM write-back, and a small approval UI.

License: MIT, see [LICENSE](LICENSE). Fernwick Commercial Cleaning and every inquiry in this repo are fictional; any resemblance to real companies or people is coincidental.

## Status
**Status: Active, Phase 1 complete, public release pending.** The test and lint commands are listed under Run it locally.
