# Eval report

Rendered 2026-10-25 (UTC) by `uv run e2q eval`. Do not edit by hand.

The original set was written in the same session as `RuleExtractor`, so its score shows
that the pieces agree with each other. The held-out set was written separately, without
sight of the extractor or the original samples (provenance in the `eval/holdout.yaml`
header), and is the better guide to accuracy. `RuleExtractor` is the baseline and is not
changed while LLM rows are measured.

LLM rows (`provider:model`) use `LLMExtractor`. Its prompt carries the extraction schema and
the service, frequency, add-on and out-of-scope categories with their labels from
`business/pricing.yaml`; it carries no keyword maps from `business/business.yaml` and no
patterns from `e2q/extract/rules.py`. LLM runs are not deterministic: each saved run is one
pass.

## Original golden set

Golden file: `eval/golden.yaml`, 20 synthetic enquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5 | ollama:gpt-oss:20b |
|---|---|---|---|
| Field: `is_enquiry` | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |
| Field: `contact_email` | 20/20 (100%) | 20/20 (100%) | 19/20 (95%) |
| Field: `service` | 20/20 (100%) | 20/20 (100%) | 19/20 (95%) |
| Field: `frequency` | 20/20 (100%) | 20/20 (100%) | 19/20 (95%) |
| Field: `areas` | 20/20 (100%) | 19/20 (95%) | 18/20 (90%) |
| Field: `add_ons` | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |
| Field: `out_of_scope` | 20/20 (100%) | 20/20 (100%) | 20/20 (100%) |
| Fields, all | 140/140 (100%) | 139/140 (99%) | 135/140 (96%) |
| Outcome (quote / clarification / handoff) | 20/20 (100%) | 20/20 (100%) | 18/20 (90%) |
| Price exact, on expected quotes | 10/10 (100%) | 10/10 (100%) | 9/10 (90%) |
| Clarification asks exactly the missing fields | 5/5 (100%) | 5/5 (100%) | 4/5 (80%) |

- `RuleExtractor` run 2026-10-25.
- `anthropic:claude-haiku-5-5` run 2026-10-25, prompt c721c7a1570d.
- `ollama:gpt-oss:20b` run 2026-10-25, prompt c721c7a1570d.

### Per enquiry: `RuleExtractor`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| s01-complete-email | quote | quote | 1197.00 | 1197.00 | - |
| s02-complete-webform | quote | quote | 350.00 | 350.00 | - |
| s03-deep-clean | quote | quote | 704.00 | 704.00 | - |
| s04-metric-units | quote | quote | 1145.40 | 1145.40 | - |
| s05-carpet | quote | quote | 360.00 | 360.00 | - |
| s06-below-minimum | quote | quote | 480.00 | 480.00 | - |
| s07-missing-area | clarification | clarification | - | - | - |
| s08-missing-frequency | clarification | clarification | - | - | - |
| s09-ambiguous-service | clarification | clarification | - | - | - |
| s10-two-sites | quote | quote | 1214.10 | 1214.10 | - |
| s11-out-of-scope | handoff | handoff | - | - | - |
| s12-sanity-band | handoff | handoff | - | - | - |
| s13-reply-chain | quote | quote | 1383.20 | 1383.20 | - |
| s14-prompt-injection | handoff | handoff | - | - | - |
| s15-vendor-spam | handoff | handoff | - | - | - |
| s16-webform-incomplete | clarification | clarification | - | - | - |
| s17-daily-supplies | quote | quote | 9920.00 | 9920.00 | - |
| s18-mixed-out-of-scope | handoff | handoff | - | - | - |
| s19-monthly-windows | quote | quote | 210.60 | 210.60 | - |
| s20-ongoing-no-schedule | clarification | clarification | - | - | - |

### Per enquiry: `anthropic:claude-haiku-5-5`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| s01-complete-email | quote | quote | 1197.00 | 1197.00 | - |
| s02-complete-webform | quote | quote | 350.00 | 350.00 | - |
| s03-deep-clean | quote | quote | 704.00 | 704.00 | - |
| s04-metric-units | quote | quote | 1145.40 | 1145.40 | - |
| s05-carpet | quote | quote | 360.00 | 360.00 | - |
| s06-below-minimum | quote | quote | 480.00 | 480.00 | - |
| s07-missing-area | clarification | clarification | - | - | - |
| s08-missing-frequency | clarification | clarification | - | - | - |
| s09-ambiguous-service | clarification | clarification | - | - | - |
| s10-two-sites | quote | quote | 1214.10 | 1214.10 | - |
| s11-out-of-scope | handoff | handoff | - | - | `areas` want [[1000, 'sqft']] got [] |
| s12-sanity-band | handoff | handoff | - | - | - |
| s13-reply-chain | quote | quote | 1383.20 | 1383.20 | - |
| s14-prompt-injection | handoff | handoff | - | - | - |
| s15-vendor-spam | handoff | handoff | - | - | - |
| s16-webform-incomplete | clarification | clarification | - | - | - |
| s17-daily-supplies | quote | quote | 9920.00 | 9920.00 | - |
| s18-mixed-out-of-scope | handoff | handoff | - | - | - |
| s19-monthly-windows | quote | quote | 210.60 | 210.60 | - |
| s20-ongoing-no-schedule | clarification | clarification | - | - | - |

### Per enquiry: `ollama:gpt-oss:20b`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| s01-complete-email | quote | handoff | 1197.00 | - | `contact_email` want 'dana.okafor@northwind-accounting.example' got None, `service` want 'regular_office' got None, `frequency` want 'weekly' got None, `areas` want [[4500, 'sqft']] got [] |
| s02-complete-webform | quote | quote | 350.00 | 350.00 | - |
| s03-deep-clean | quote | quote | 704.00 | 704.00 | - |
| s04-metric-units | quote | quote | 1145.40 | 1145.40 | - |
| s05-carpet | quote | quote | 360.00 | 360.00 | - |
| s06-below-minimum | quote | quote | 480.00 | 480.00 | - |
| s07-missing-area | clarification | clarification | - | - | - |
| s08-missing-frequency | clarification | handoff | - | - | - |
| s09-ambiguous-service | clarification | clarification | - | - | - |
| s10-two-sites | quote | quote | 1214.10 | 1214.10 | - |
| s11-out-of-scope | handoff | handoff | - | - | `areas` want [[1000, 'sqft']] got [[None, None], [None, None]] |
| s12-sanity-band | handoff | handoff | - | - | - |
| s13-reply-chain | quote | quote | 1383.20 | 1383.20 | - |
| s14-prompt-injection | handoff | handoff | - | - | - |
| s15-vendor-spam | handoff | handoff | - | - | - |
| s16-webform-incomplete | clarification | clarification | - | - | - |
| s17-daily-supplies | quote | quote | 9920.00 | 9920.00 | - |
| s18-mixed-out-of-scope | handoff | handoff | - | - | - |
| s19-monthly-windows | quote | quote | 210.60 | 210.60 | - |
| s20-ongoing-no-schedule | clarification | clarification | - | - | - |

## Held-out set

Golden file: `eval/holdout.yaml`, 15 synthetic enquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5 | ollama:gpt-oss:20b |
|---|---|---|---|
| Field: `is_enquiry` | 14/15 (93%) | 15/15 (100%) | 14/15 (93%) |
| Field: `contact_email` | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) |
| Field: `service` | 11/15 (73%) | 15/15 (100%) | 14/15 (93%) |
| Field: `frequency` | 10/15 (67%) | 15/15 (100%) | 14/15 (93%) |
| Field: `areas` | 13/15 (87%) | 15/15 (100%) | 14/15 (93%) |
| Field: `add_ons` | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) |
| Field: `out_of_scope` | 14/15 (93%) | 15/15 (100%) | 15/15 (100%) |
| Fields, all | 92/105 (88%) | 105/105 (100%) | 101/105 (96%) |
| Outcome (quote / clarification / handoff) | 7/15 (47%) | 14/15 (93%) | 14/15 (93%) |
| Price exact, on expected quotes | 3/7 (43%) | 6/7 (86%) | 6/7 (86%) |
| Clarification asks exactly the missing fields | 1/2 (50%) | 2/2 (100%) | 2/2 (100%) |

- `RuleExtractor` run 2026-10-25.
  - h13-area-range: outcome correct (clarification) but it asked for ['frequency'] instead of ['area'].
- `anthropic:claude-haiku-5-5` run 2026-10-25, prompt c721c7a1570d.
- `ollama:gpt-oss:20b` run 2026-10-25, prompt c721c7a1570d.

### Per enquiry: `RuleExtractor`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| h01-weekly-plain | quote | quote | 1010.80 | 1010.80 | - |
| h02-every-other-week-form | quote | clarification | 336.00 | - | `service` want 'regular_office' got None, `frequency` want 'fortnightly' got None |
| h03-move-in-thorough | quote | clarification | 1100.00 | - | `service` want 'deep_clean' got None |
| h04-carpets-shampoo | quote | clarification | 270.00 | - | `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None |
| h05-metric-fortnightly | quote | quote | 376.74 | 376.74 | - |
| h06-form-no-email | handoff | handoff | - | - | - |
| h07-twelve-desks-no-area | clarification | clarification | - | - | - |
| h08-two-locations | quote | quote | 1972.20 | 1972.20 | - |
| h09-twice-a-week | handoff | quote | - | 585.20 | `frequency` want None got 'weekly' |
| h10-ps-injection | handoff | quote | - | 532.00 | - |
| h11-job-applicant | handoff | clarification | - | - | `is_enquiry` want False got True |
| h12-glass-facade | handoff | quote | - | 798.00 | `out_of_scope` want ['exterior_windows'] got [] |
| h13-area-range | clarification | clarification | - | - | `frequency` want 'daily' got None, `areas` want [] got [[3000.0, 'sqft']] |
| h14-kiosk-tiny | handoff | handoff | - | - | - |
| h15-daily-fridge | quote | clarification | 5460.00 | - | `service` want 'regular_office' got None, `frequency` want 'daily' got None, `areas` want [[4000, 'sqft']] got [[4000.0, 'sqft'], [4000.0, 'sqft']] |

### Per enquiry: `anthropic:claude-haiku-5-5`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| h01-weekly-plain | quote | quote | 1010.80 | 1010.80 | - |
| h02-every-other-week-form | quote | quote | 336.00 | 336.00 | - |
| h03-move-in-thorough | quote | quote | 1100.00 | 1100.00 | - |
| h04-carpets-shampoo | quote | quote | 270.00 | 270.00 | - |
| h05-metric-fortnightly | quote | quote | 376.74 | 376.74 | - |
| h06-form-no-email | handoff | handoff | - | - | - |
| h07-twelve-desks-no-area | clarification | clarification | - | - | - |
| h08-two-locations | quote | quote | 1972.20 | 1972.20 | - |
| h09-twice-a-week | handoff | handoff | - | - | - |
| h10-ps-injection | handoff | handoff | - | - | - |
| h11-job-applicant | handoff | handoff | - | - | - |
| h12-glass-facade | handoff | handoff | - | - | - |
| h13-area-range | clarification | clarification | - | - | - |
| h14-kiosk-tiny | handoff | handoff | - | - | - |
| h15-daily-fridge | quote | handoff | 5460.00 | - | - |

### Per enquiry: `ollama:gpt-oss:20b`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| h01-weekly-plain | quote | quote | 1010.80 | 1010.80 | - |
| h02-every-other-week-form | quote | quote | 336.00 | 336.00 | - |
| h03-move-in-thorough | quote | quote | 1100.00 | 1100.00 | - |
| h04-carpets-shampoo | quote | handoff | 270.00 | - | `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got [] |
| h05-metric-fortnightly | quote | quote | 376.74 | 376.74 | - |
| h06-form-no-email | handoff | handoff | - | - | - |
| h07-twelve-desks-no-area | clarification | clarification | - | - | - |
| h08-two-locations | quote | quote | 1972.20 | 1972.20 | - |
| h09-twice-a-week | handoff | handoff | - | - | - |
| h10-ps-injection | handoff | handoff | - | - | - |
| h11-job-applicant | handoff | handoff | - | - | - |
| h12-glass-facade | handoff | handoff | - | - | - |
| h13-area-range | clarification | clarification | - | - | - |
| h14-kiosk-tiny | handoff | handoff | - | - | - |
| h15-daily-fridge | quote | quote | 5460.00 | 5460.00 | - |

## Held-out set 2

Golden file: `eval/holdout2.yaml`, 15 synthetic enquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5 | ollama:gpt-oss:20b |
|---|---|---|---|
| Field: `is_enquiry` | 14/15 (93%) | 15/15 (100%) | 15/15 (100%) |
| Field: `contact_email` | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) |
| Field: `service` | 12/15 (80%) | 14/15 (93%) | 15/15 (100%) |
| Field: `frequency` | 13/15 (87%) | 15/15 (100%) | 15/15 (100%) |
| Field: `areas` | 15/15 (100%) | 15/15 (100%) | 15/15 (100%) |
| Field: `add_ons` | 13/15 (87%) | 15/15 (100%) | 15/15 (100%) |
| Field: `out_of_scope` | 14/15 (93%) | 15/15 (100%) | 15/15 (100%) |
| Fields, all | 96/105 (91%) | 104/105 (99%) | 105/105 (100%) |
| Outcome (quote / clarification / handoff) | 11/15 (73%) | 15/15 (100%) | 15/15 (100%) |
| Price exact, on expected quotes | 4/9 (44%) | 9/9 (100%) | 9/9 (100%) |
| Clarification asks exactly the missing fields | 1/2 (50%) | 1/2 (50%) | 2/2 (100%) |

- `RuleExtractor` run 2026-10-25.
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
- `anthropic:claude-haiku-5-5` run 2026-10-25, prompt c721c7a1570d.
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
- `ollama:gpt-oss:20b` run 2026-10-25, prompt c721c7a1570d.

### Per enquiry: `RuleExtractor`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| k01-monthly-bathrooms | quote | quote | 251.00 | 231.00 | `add_ons` want ['washroom_supplies'] got [] |
| k02-carpet-form | quote | clarification | 450.00 | - | `service` want 'carpet_cleaning' got None |
| k03-handing-keys-back | quote | clarification | 616.00 | - | `service` want 'deep_clean' got None, `frequency` want 'one_off' got None |
| k04-weekly-glass-partitions | quote | quote | 1065.00 | 665.00 | `add_ons` want ['interior_windows'] got [] |
| k05-metric-every-working-day | quote | quote | 2400.00 | 149.23 | `frequency` want 'daily' got 'monthly' |
| k06-large-daily | handoff | handoff | - | - | - |
| k07-three-branches | quote | quote | 893.00 | 893.00 | - |
| k08-how-much | clarification | clarification | - | - | `service` want 'regular_office' got None |
| k09-call-to-discuss | clarification | clarification | - | - | - |
| k10-mouse-problem | handoff | quote | - | 532.00 | `out_of_scope` want ['pest_control'] got [] |
| k11-form-injection | handoff | handoff | - | - | - |
| k12-chemicals-supplier | handoff | clarification | - | - | `is_enquiry` want False got True |
| k13-correction-reply-chain | quote | quote | 1117.20 | 1117.20 | - |
| k14-small-weekly-fridge | quote | quote | 480.00 | 480.00 | - |
| k15-metric-monthly-supplies | quote | quote | 434.41 | 434.41 | - |

### Per enquiry: `anthropic:claude-haiku-5-5`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| k01-monthly-bathrooms | quote | quote | 251.00 | 251.00 | - |
| k02-carpet-form | quote | quote | 450.00 | 450.00 | - |
| k03-handing-keys-back | quote | quote | 616.00 | 616.00 | - |
| k04-weekly-glass-partitions | quote | quote | 1065.00 | 1065.00 | - |
| k05-metric-every-working-day | quote | quote | 2400.00 | 2400.00 | - |
| k06-large-daily | handoff | handoff | - | - | - |
| k07-three-branches | quote | quote | 893.00 | 893.00 | - |
| k08-how-much | clarification | clarification | - | - | `service` want 'regular_office' got None |
| k09-call-to-discuss | clarification | clarification | - | - | - |
| k10-mouse-problem | handoff | handoff | - | - | - |
| k11-form-injection | handoff | handoff | - | - | - |
| k12-chemicals-supplier | handoff | handoff | - | - | - |
| k13-correction-reply-chain | quote | quote | 1117.20 | 1117.20 | - |
| k14-small-weekly-fridge | quote | quote | 480.00 | 480.00 | - |
| k15-metric-monthly-supplies | quote | quote | 434.41 | 434.41 | - |

### Per enquiry: `ollama:gpt-oss:20b`

| Sample | Expected | Got | Expected total | Got total | Field mismatches |
|---|---|---|---|---|---|
| k01-monthly-bathrooms | quote | quote | 251.00 | 251.00 | - |
| k02-carpet-form | quote | quote | 450.00 | 450.00 | - |
| k03-handing-keys-back | quote | quote | 616.00 | 616.00 | - |
| k04-weekly-glass-partitions | quote | quote | 1065.00 | 1065.00 | - |
| k05-metric-every-working-day | quote | quote | 2400.00 | 2400.00 | - |
| k06-large-daily | handoff | handoff | - | - | - |
| k07-three-branches | quote | quote | 893.00 | 893.00 | - |
| k08-how-much | clarification | clarification | - | - | - |
| k09-call-to-discuss | clarification | clarification | - | - | - |
| k10-mouse-problem | handoff | handoff | - | - | - |
| k11-form-injection | handoff | handoff | - | - | - |
| k12-chemicals-supplier | handoff | handoff | - | - | - |
| k13-correction-reply-chain | quote | quote | 1117.20 | 1117.20 | - |
| k14-small-weekly-fridge | quote | quote | 480.00 | 480.00 | - |
| k15-metric-monthly-supplies | quote | quote | 434.41 | 434.41 | - |

## Cases to watch

Held-out cases a client is most likely to ask about, with each row's outcome.

| Set | Case | Expected | RuleExtractor | anthropic:claude-haiku-5-5 | ollama:gpt-oss:20b |
|---|---|---|---|---|---|
| Held-out set | h10-ps-injection | handoff | quote, total 532.00 (MISS) | handoff (ok) | handoff (ok) |
| Held-out set | h11-job-applicant | handoff | clarification, asked ['service', 'frequency', 'area'] (MISS) | handoff (ok) | handoff (ok) |
| Held-out set | h13-area-range | clarification | clarification, asked ['frequency'] (MISS) | clarification, asked ['area'] (ok) | clarification, asked ['area'] (ok) |
| Held-out set | h15-daily-fridge | quote | clarification, asked ['service', 'frequency'] (MISS) | handoff (MISS) | quote, total 5460.00 (ok) |
| Held-out set 2 | k06-large-daily | handoff | handoff (ok) | handoff (ok) | handoff (ok) |
| Held-out set 2 | k07-three-branches | quote | quote, total 893.00 (ok) | quote, total 893.00 (ok) | quote, total 893.00 (ok) |
| Held-out set 2 | k09-call-to-discuss | clarification | clarification, asked ['service', 'frequency', 'area'] (ok) | clarification, asked ['service', 'frequency', 'area'] (ok) | clarification, asked ['service', 'frequency', 'area'] (ok) |
| Held-out set 2 | k10-mouse-problem | handoff | quote, total 532.00 (MISS) | handoff (ok) | handoff (ok) |
| Held-out set 2 | k11-form-injection | handoff | handoff (ok) | handoff (ok) | handoff (ok) |
| Held-out set 2 | k13-correction-reply-chain | quote | quote, total 1117.20 (ok) | quote, total 1117.20 (ok) | quote, total 1117.20 (ok) |

## Cost and latency (LLM rows)

One extraction call per enquiry; tokens and latency are recorded per call in `eval/runs/`.

| Row | Calls | Mean tokens in | Mean tokens out | Mean latency (s) | Max latency (s) | Cost per enquiry |
|---|---|---|---|---|---|---|
| anthropic:claude-haiku-5-5 | 50 | 2,092 | 216 | 1.9 | 3.3 | $0.000317 |
| ollama:gpt-oss:20b | 49 | 691 | 625 | 5.2 | 13.9 | $0 (local) |

- `claude-haiku-5-5`: $0.10 / MTok in, $0.50 / MTok out (prompts up to 100,000 tokens); source https://platform.claude.com/docs/en/about-claude/pricing, fetched 2026-10-25.
- `gpt-oss:20b`: runs on this machine through Ollama; no per-token charge (hardware and power not counted)
