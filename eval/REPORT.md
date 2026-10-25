# Eval report

Rendered 2026-10-25 (UTC) by `uv run e2q eval`. Do not edit by hand.

The original set was written in the same session as `RuleExtractor`, so its score shows
that the pieces agree with each other. The held-out sets were written separately, without
sight of the extractor or the original samples (provenance in each held-out YAML header),
and are the better guide to accuracy. `RuleExtractor` is the baseline and is not changed
while LLM rows are measured.

LLM rows are named `provider:model@prompt`; `+guard` rows also run `RuleExtractor` and hand
off when the two disagree on a field a quote needs. The prompt carries the extraction schema
and the service, frequency, add-on and out-of-scope categories with their labels from
`business/pricing.yaml`; it carries no keyword maps from `business/business.yaml` and no
patterns from `e2q/extract/rules.py`. Each saved run is one pass.

## Original golden set

Golden file: `eval/golden.yaml`, 25 synthetic inquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5@v1 (stale) | anthropic:claude-haiku-5-5@v2 x3 | anthropic:claude-haiku-5-5@v2+guard x3 | ollama:gpt-oss:20b@v1 (stale) | ollama:gpt-oss:20b@v2 x3 | ollama:gpt-oss:20b@v2+guard x3 |
|---|---|---|---|---|---|---|---|
| Field: `is_enquiry` | 25/25 (100%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 20/20 (100%) | 23.7/25 (23-24) | 23.7/25 (23-24) |
| Field: `contact_email` | 25/25 (100%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 19/20 (95%) | 25.0/25 (25-25) | 25.0/25 (25-25) |
| Field: `service` | 24/25 (96%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 19/20 (95%) | 24.7/25 (24-25) | 24.7/25 (24-25) |
| Field: `frequency` | 24/25 (96%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 19/20 (95%) | 24.7/25 (24-25) | 24.7/25 (24-25) |
| Field: `areas` | 25/25 (100%) | 19/20 (95%) | 24.7/25 (24-25) | 24.7/25 (24-25) | 18/20 (90%) | 23.7/25 (23-24) | 23.7/25 (23-24) |
| Field: `add_ons` | 25/25 (100%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) |
| Field: `out_of_scope` | 25/25 (100%) | 20/20 (100%) | 25.0/25 (25-25) | 25.0/25 (25-25) | 20/20 (100%) | 24.0/25 (24-24) | 24.0/25 (24-24) |
| Fields, all | 173/175 (99%) | 139/140 (99%) | 174.7/175 (174-175) | 174.7/175 (174-175) | 135/140 (96%) | 170.7/175 (168-172) | 170.7/175 (168-172) |
| Outcome (quote / clarification / handoff) | 24/25 (96%) | 20/20 (100%) | 25.0/25 (25-25) | 24.0/25 (24-24) | 18/20 (90%) | 24.7/25 (24-25) | 23.7/25 (23-24) |
| Price exact, on expected quotes | 12/13 (92%) | 10/10 (100%) | 13.0/13 (13-13) | 12.0/13 (12-12) | 9/10 (90%) | 12.7/13 (12-13) | 11.7/13 (11-12) |
| Clarification asks exactly the missing fields | 6/6 (100%) | 5/5 (100%) | 6.0/6 (6-6) | 6.0/6 (6-6) | 4/5 (80%) | 6.0/6 (6-6) | 6.0/6 (6-6) |

Rows with several passes show the mean, then the lowest and highest pass in brackets.

- `RuleExtractor`: run 2026-10-25.
- `anthropic:claude-haiku-5-5@v1`: run 2026-10-25; prompt c721c7a1570d. Stale: scored on an earlier `eval/golden.yaml` (20 cases); kept for comparison.
- `anthropic:claude-haiku-5-5@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/golden.yaml 4a98227975ef (run was scored against b4ac733b487b) with the current pricing code; new calls: s24-casual-carpets (new case), s25-oversized-no-schedule (new case)
  - 2026-10-25: golden hash 4a98227975ef -> 9e635d4c826a after line-ending normalisation; content identical, outcomes unchanged
- `anthropic:claude-haiku-5-5@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/golden.yaml 4a98227975ef (run was scored against b4ac733b487b) with the current pricing code; new calls: s24-casual-carpets (new case), s25-oversized-no-schedule (new case)
  - 2026-10-25: golden hash 4a98227975ef -> 9e635d4c826a after line-ending normalisation; content identical, outcomes unchanged
- `ollama:gpt-oss:20b@v1`: run 2026-10-25; prompt c721c7a1570d. Stale: scored on an earlier `eval/golden.yaml` (20 cases); kept for comparison.
- `ollama:gpt-oss:20b@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/golden.yaml 4a98227975ef (run was scored against b4ac733b487b) with the current pricing code; new calls: s01-complete-email (re-called: infrastructure failure), s02-complete-webform (re-called: infrastructure failure), s24-casual-carpets (new case), s25-oversized-no-schedule (new case)
  - 2026-10-25: golden hash 4a98227975ef -> 9e635d4c826a after line-ending normalisation; content identical, outcomes unchanged
- `ollama:gpt-oss:20b@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/golden.yaml 4a98227975ef (run was scored against b4ac733b487b) with the current pricing code; new calls: s01-complete-email (re-called: infrastructure failure), s02-complete-webform (re-called: infrastructure failure), s24-casual-carpets (new case), s25-oversized-no-schedule (new case)
  - 2026-10-25: golden hash 4a98227975ef -> 9e635d4c826a after line-ending normalisation; content identical, outcomes unchanged

### Outcome spread across passes

| Row | Passes | Best | Worst | Mean |
|---|---|---|---|---|
| anthropic:claude-haiku-5-5@v2 | 3 | 25/25 | 25/25 | 25.0/25 |
| anthropic:claude-haiku-5-5@v2+guard | 3 | 24/25 | 24/25 | 24.0/25 |
| ollama:gpt-oss:20b@v2 | 3 | 25/25 | 24/25 | 24.7/25 |
| ollama:gpt-oss:20b@v2+guard | 3 | 24/25 | 23/25 | 23.7/25 |

### Per inquiry

| Sample | Expected | RuleExtractor | anthropic:claude-haiku-5-5@v2 | anthropic:claude-haiku-5-5@v2+guard | ollama:gpt-oss:20b@v2 | ollama:gpt-oss:20b@v2+guard |
|---|---|---|---|---|---|---|
| s01-complete-email | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s02-complete-webform | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s03-deep-clean | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s04-metric-units | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s05-carpet | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s06-below-minimum | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s07-missing-area | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s08-missing-frequency | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s09-ambiguous-service | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s10-two-sites | quote | ok | ok 3/3 | ok 3/3 | MISS 1/3 (handoff) | MISS 1/3 (handoff) |
| s11-out-of-scope | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s12-sanity-band | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s13-reply-chain | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s14-prompt-injection | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s15-vendor-spam | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s16-webform-incomplete | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s17-daily-supplies | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s18-mixed-out-of-scope | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s19-monthly-windows | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s20-ongoing-no-schedule | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s21-ongoing-basis | clarification | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s22-task-list-not-injection | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s23-implied-service | quote | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |
| s24-casual-carpets | quote | MISS: clarification | ok 3/3 | MISS 3/3 (handoff) | ok 3/3 | MISS 3/3 (handoff) |
| s25-oversized-no-schedule | handoff | ok | ok 3/3 | ok 3/3 | ok 3/3 | ok 3/3 |

### Failures

- `RuleExtractor`: s24-casual-carpets: want quote 330.00, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2` pass 1: s10-two-sites: want quote 1214.10, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'regular_office' got None, `frequency` want 'weekly' got None, `areas` want [[3000, 'sqft'], [1500, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 1: s10-two-sites: want quote 1214.10, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'regular_office' got None, `frequency` want 'weekly' got None, `areas` want [[3000, 'sqft'], [1500, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 1: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 2: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 3: s24-casual-carpets: want quote 330.00, got handoff; reasons ['extractors_disagree:service,frequency']

## Held-out set

Golden file: `eval/holdout.yaml`, 15 synthetic inquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5@v1 | anthropic:claude-haiku-5-5@v2 x3 | anthropic:claude-haiku-5-5@v2+guard x3 | ollama:gpt-oss:20b@v1 | ollama:gpt-oss:20b@v2 x3 | ollama:gpt-oss:20b@v2+guard x3 |
|---|---|---|---|---|---|---|---|
| Field: `is_enquiry` | 14/15 (93%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 14/15 (93%) | 14.0/15 (14-14) | 14.0/15 (14-14) |
| Field: `contact_email` | 15/15 (100%) | 15/15 (100%) | 14.7/15 (14-15) | 14.7/15 (14-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Field: `service` | 11/15 (73%) | 15/15 (100%) | 14.7/15 (14-15) | 14.7/15 (14-15) | 14/15 (93%) | 14.0/15 (14-14) | 14.0/15 (14-14) |
| Field: `frequency` | 10/15 (67%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 14/15 (93%) | 14.0/15 (14-14) | 14.0/15 (14-14) |
| Field: `areas` | 13/15 (87%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 14/15 (93%) | 14.0/15 (14-14) | 14.0/15 (14-14) |
| Field: `add_ons` | 15/15 (100%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Field: `out_of_scope` | 14/15 (93%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Fields, all | 92/105 (88%) | 105/105 (100%) | 104.3/105 (103-105) | 104.3/105 (103-105) | 101/105 (96%) | 101.0/105 (101-101) | 101.0/105 (101-101) |
| Outcome (quote / clarification / handoff) | 7/15 (47%) | 14/15 (93%) | 15.0/15 (15-15) | 10.0/15 (10-10) | 14/15 (93%) | 14.0/15 (14-14) | 10.0/15 (10-10) |
| Price exact, on expected quotes | 3/7 (43%) | 6/7 (86%) | 7.0/7 (7-7) | 3.0/7 (3-3) | 6/7 (86%) | 6.0/7 (6-6) | 3.0/7 (3-3) |
| Clarification asks exactly the missing fields | 1/2 (50%) | 2/2 (100%) | 2.0/2 (2-2) | 1.0/2 (1-1) | 2/2 (100%) | 2.0/2 (2-2) | 1.0/2 (1-1) |

Rows with several passes show the mean, then the lowest and highest pass in brackets.

- `RuleExtractor`: run 2026-10-25.
  - h13-area-range: outcome correct (clarification) but it asked for ['frequency'] instead of ['area'].
- `anthropic:claude-haiku-5-5@v1`: run 2026-10-25; prompt c721c7a1570d.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls
- `anthropic:claude-haiku-5-5@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls
- `anthropic:claude-haiku-5-5@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls
- `ollama:gpt-oss:20b@v1`: run 2026-10-25; prompt c721c7a1570d.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls
- `ollama:gpt-oss:20b@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls
- `ollama:gpt-oss:20b@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/holdout.yaml 1716cca67934 (run was scored against 1716cca67934) with the current pricing code; no new calls

### Outcome spread across passes

| Row | Passes | Best | Worst | Mean |
|---|---|---|---|---|
| anthropic:claude-haiku-5-5@v2 | 3 | 15/15 | 15/15 | 15.0/15 |
| anthropic:claude-haiku-5-5@v2+guard | 3 | 10/15 | 10/15 | 10.0/15 |
| ollama:gpt-oss:20b@v2 | 3 | 14/15 | 14/15 | 14.0/15 |
| ollama:gpt-oss:20b@v2+guard | 3 | 10/15 | 10/15 | 10.0/15 |

### Per inquiry

| Sample | Expected | RuleExtractor | anthropic:claude-haiku-5-5@v1 | anthropic:claude-haiku-5-5@v2 | anthropic:claude-haiku-5-5@v2+guard | ollama:gpt-oss:20b@v1 | ollama:gpt-oss:20b@v2 | ollama:gpt-oss:20b@v2+guard |
|---|---|---|---|---|---|---|---|---|
| h01-weekly-plain | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h02-every-other-week-form | quote | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |
| h03-move-in-thorough | quote | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |
| h04-carpets-shampoo | quote | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | MISS: handoff | MISS 3/3 (handoff) | MISS 3/3 (handoff) |
| h05-metric-fortnightly | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h06-form-no-email | handoff | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h07-twelve-desks-no-area | clarification | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h08-two-locations | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h09-twice-a-week | handoff | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h10-ps-injection | handoff | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h11-job-applicant | handoff | MISS: clarification | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h12-glass-facade | handoff | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h13-area-range | clarification | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |
| h14-kiosk-tiny | handoff | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| h15-daily-fridge | quote | MISS: clarification | MISS: handoff | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |

### Failures

- `RuleExtractor`: h02-every-other-week-form: want quote 336.00, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None, `frequency` want 'fortnightly' got None
- `RuleExtractor`: h03-move-in-thorough: want quote 1100.00, got clarification asking ['service']; reasons ['missing:service'] fields: `service` want 'deep_clean' got None
- `RuleExtractor`: h04-carpets-shampoo: want quote 270.00, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None
- `RuleExtractor`: h09-twice-a-week: want handoff, got quote 585.20; fields: `frequency` want None got 'weekly'
- `RuleExtractor`: h10-ps-injection: want handoff, got quote 532.00;
- `RuleExtractor`: h11-job-applicant: want handoff, got clarification asking ['service', 'frequency', 'area']; reasons ['missing:service', 'missing:frequency', 'missing:area'] fields: `is_enquiry` want False got True
- `RuleExtractor`: h12-glass-facade: want handoff, got quote 798.00; fields: `out_of_scope` want ['exterior_windows'] got []
- `RuleExtractor`: h13-area-range: want clarification, got clarification asking ['frequency']; reasons ['missing:frequency'] fields: `frequency` want 'daily' got None, `areas` want [] got [[3000.0, 'sqft']]
- `RuleExtractor`: h15-daily-fridge: want quote 5460.00, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None, `frequency` want 'daily' got None, `areas` want [[4000, 'sqft']] got [[4000.0, 'sqft'], [4000.0, 'sqft']]
- `anthropic:claude-haiku-5-5@v1`: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['injection:model_flagged']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']
- `ollama:gpt-oss:20b@v1`: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2` pass 1: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2` pass 2: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2` pass 3: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 1: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 1: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 1: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 1: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `ollama:gpt-oss:20b@v2+guard` pass 1: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']
- `ollama:gpt-oss:20b@v2+guard` pass 2: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 2: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 2: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 2: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `ollama:gpt-oss:20b@v2+guard` pass 2: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']
- `ollama:gpt-oss:20b@v2+guard` pass 3: h02-every-other-week-form: want quote 336.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 3: h03-move-in-thorough: want quote 1100.00, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 3: h04-carpets-shampoo: want quote 270.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[900, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 3: h13-area-range: want clarification, got handoff; reasons ['extractors_disagree:frequency,area']
- `ollama:gpt-oss:20b@v2+guard` pass 3: h15-daily-fridge: want quote 5460.00, got handoff; reasons ['extractors_disagree:service,frequency,area']

## Held-out set 2

Golden file: `eval/holdout2.yaml`, 15 synthetic inquiries.

| Measure | RuleExtractor | anthropic:claude-haiku-5-5@v1 | anthropic:claude-haiku-5-5@v2 x3 | anthropic:claude-haiku-5-5@v2+guard x3 | ollama:gpt-oss:20b@v1 | ollama:gpt-oss:20b@v2 x3 | ollama:gpt-oss:20b@v2+guard x3 |
|---|---|---|---|---|---|---|---|
| Field: `is_enquiry` | 14/15 (93%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 14.7/15 (14-15) | 14.7/15 (14-15) |
| Field: `contact_email` | 15/15 (100%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Field: `service` | 11/15 (73%) | 13/15 (87%) | 14.0/15 (14-14) | 14.0/15 (14-14) | 14/15 (93%) | 14.7/15 (14-15) | 14.7/15 (14-15) |
| Field: `frequency` | 13/15 (87%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 14.7/15 (14-15) | 14.7/15 (14-15) |
| Field: `areas` | 15/15 (100%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 14.7/15 (14-15) | 14.7/15 (14-15) |
| Field: `add_ons` | 13/15 (87%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Field: `out_of_scope` | 14/15 (93%) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) | 15/15 (100%) | 15.0/15 (15-15) | 15.0/15 (15-15) |
| Fields, all | 95/105 (90%) | 103/105 (98%) | 104.0/105 (104-104) | 104.0/105 (104-104) | 104/105 (99%) | 103.7/105 (101-105) | 103.7/105 (101-105) |
| Outcome (quote / clarification / handoff) | 11/15 (73%) | 15/15 (100%) | 15.0/15 (15-15) | 11.0/15 (11-11) | 15/15 (100%) | 14.7/15 (14-15) | 10.0/15 (10-10) |
| Price exact, on expected quotes | 4/9 (44%) | 9/9 (100%) | 9.0/9 (9-9) | 6.0/9 (6-6) | 9/9 (100%) | 8.7/9 (8-9) | 6.0/9 (6-6) |
| Clarification asks exactly the missing fields | 0/2 (0%) | 0/2 (0%) | 1.0/2 (1-1) | 0.0/2 (0-0) | 1/2 (50%) | 2.0/2 (2-2) | 0.0/2 (0-0) |

Rows with several passes show the mean, then the lowest and highest pass in brackets.

- `RuleExtractor`: run 2026-10-25.
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
  - k09-call-to-discuss: outcome correct (clarification) but it asked for ['service', 'frequency', 'area'] instead of ['frequency', 'area'].
- `anthropic:claude-haiku-5-5@v1`: run 2026-10-25; prompt c721c7a1570d.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
  - k09-call-to-discuss: outcome correct (clarification) but it asked for ['service', 'frequency', 'area'] instead of ['frequency', 'area'].
- `anthropic:claude-haiku-5-5@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
- `anthropic:claude-haiku-5-5@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; effort low, temperature not accepted, seed not offered.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls
  - k08-how-much: outcome correct (clarification) but it asked for ['service', 'frequency'] instead of ['frequency'].
- `ollama:gpt-oss:20b@v1`: run 2026-10-25; prompt c721c7a1570d.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls
  - k09-call-to-discuss: outcome correct (clarification) but it asked for ['service', 'frequency', 'area'] instead of ['frequency', 'area'].
- `ollama:gpt-oss:20b@v2`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls
- `ollama:gpt-oss:20b@v2+guard`: run 2026-10-25; prompt 00398ad6cd42; 3 passes; temperature 0.0, seed 42.
  - 2026-10-25: re-scored from saved outputs against eval/holdout2.yaml 99cf053b20d1 (run was scored against 5bb0f18af939) with the current pricing code; no new calls

### Outcome spread across passes

| Row | Passes | Best | Worst | Mean |
|---|---|---|---|---|
| anthropic:claude-haiku-5-5@v2 | 3 | 15/15 | 15/15 | 15.0/15 |
| anthropic:claude-haiku-5-5@v2+guard | 3 | 11/15 | 11/15 | 11.0/15 |
| ollama:gpt-oss:20b@v2 | 3 | 15/15 | 14/15 | 14.7/15 |
| ollama:gpt-oss:20b@v2+guard | 3 | 10/15 | 10/15 | 10.0/15 |

### Per inquiry

| Sample | Expected | RuleExtractor | anthropic:claude-haiku-5-5@v1 | anthropic:claude-haiku-5-5@v2 | anthropic:claude-haiku-5-5@v2+guard | ollama:gpt-oss:20b@v1 | ollama:gpt-oss:20b@v2 | ollama:gpt-oss:20b@v2+guard |
|---|---|---|---|---|---|---|---|---|
| k01-monthly-bathrooms | quote | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k02-carpet-form | quote | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | ok | MISS 1/3 (handoff) | MISS 3/3 (handoff) |
| k03-handing-keys-back | quote | MISS: clarification | ok | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |
| k04-weekly-glass-partitions | quote | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k05-metric-every-working-day | quote | MISS: quote | ok | ok 3/3 | MISS 3/3 (handoff) | ok | ok 3/3 | MISS 3/3 (handoff) |
| k06-large-daily | handoff | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k07-three-branches | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k08-how-much | clarification | MISS: clarification | MISS: clarification | MISS 3/3 (clarification) | MISS 3/3 (clarification) | ok | ok 3/3 | MISS 3/3 (handoff) |
| k09-call-to-discuss | clarification | MISS: clarification | MISS: clarification | ok 3/3 | MISS 3/3 (handoff) | MISS: clarification | ok 3/3 | MISS 3/3 (handoff) |
| k10-mouse-problem | handoff | MISS: quote | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k11-form-injection | handoff | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k12-chemicals-supplier | handoff | MISS: clarification | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k13-correction-reply-chain | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k14-small-weekly-fridge | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |
| k15-metric-monthly-supplies | quote | ok | ok | ok 3/3 | ok 3/3 | ok | ok 3/3 | ok 3/3 |

### Failures

- `RuleExtractor`: k01-monthly-bathrooms: want quote 251.00, got quote 231.00; fields: `add_ons` want ['washroom_supplies'] got []
- `RuleExtractor`: k02-carpet-form: want quote 450.00, got clarification asking ['service']; reasons ['missing:service'] fields: `service` want 'carpet_cleaning' got None
- `RuleExtractor`: k03-handing-keys-back: want quote 616.00, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'deep_clean' got None, `frequency` want 'one_off' got None
- `RuleExtractor`: k04-weekly-glass-partitions: want quote 1065.00, got quote 665.00; fields: `add_ons` want ['interior_windows'] got []
- `RuleExtractor`: k05-metric-every-working-day: want quote 2400.00, got quote 149.23; fields: `frequency` want 'daily' got 'monthly'
- `RuleExtractor`: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `RuleExtractor`: k09-call-to-discuss: want clarification, got clarification asking ['service', 'frequency', 'area']; reasons ['missing:service', 'missing:frequency', 'missing:area'] fields: `service` want 'regular_office' got None
- `RuleExtractor`: k10-mouse-problem: want handoff, got quote 532.00; fields: `out_of_scope` want ['pest_control'] got []
- `RuleExtractor`: k12-chemicals-supplier: want handoff, got clarification asking ['service', 'frequency', 'area']; reasons ['missing:service', 'missing:frequency', 'missing:area'] fields: `is_enquiry` want False got True
- `anthropic:claude-haiku-5-5@v1`: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v1`: k09-call-to-discuss: want clarification, got clarification asking ['service', 'frequency', 'area']; reasons ['missing:service', 'missing:frequency', 'missing:area'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2` pass 1: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2` pass 2: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2` pass 3: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: k02-carpet-form: want quote 450.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2+guard` pass 1: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: k02-carpet-form: want quote 450.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2+guard` pass 2: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: k02-carpet-form: want quote 450.00, got handoff; reasons ['extractors_disagree:service']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: k08-how-much: want clarification, got clarification asking ['service', 'frequency']; reasons ['missing:service', 'missing:frequency'] fields: `service` want 'regular_office' got None
- `anthropic:claude-haiku-5-5@v2+guard` pass 3: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v1`: k09-call-to-discuss: want clarification, got clarification asking ['service', 'frequency', 'area']; reasons ['missing:service', 'missing:frequency', 'missing:area'] fields: `service` want 'regular_office' got None
- `ollama:gpt-oss:20b@v2` pass 3: k02-carpet-form: want quote 450.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[1500, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 1: k02-carpet-form: want quote 450.00, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 1: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 1: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 1: k08-how-much: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 1: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 2: k02-carpet-form: want quote 450.00, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 2: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 2: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 2: k08-how-much: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 2: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 3: k02-carpet-form: want quote 450.00, got handoff; reasons ['not_an_enquiry'] fields: `is_enquiry` want True got False, `service` want 'carpet_cleaning' got None, `frequency` want 'one_off' got None, `areas` want [[1500, 'sqft']] got []
- `ollama:gpt-oss:20b@v2+guard` pass 3: k03-handing-keys-back: want quote 616.00, got handoff; reasons ['extractors_disagree:service,frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 3: k05-metric-every-working-day: want quote 2400.00, got handoff; reasons ['extractors_disagree:frequency']
- `ollama:gpt-oss:20b@v2+guard` pass 3: k08-how-much: want clarification, got handoff; reasons ['extractors_disagree:service']
- `ollama:gpt-oss:20b@v2+guard` pass 3: k09-call-to-discuss: want clarification, got handoff; reasons ['extractors_disagree:service']

## Cases to watch

Held-out cases a client is most likely to ask about, with each row's outcome.

| Set | Case | Expected | RuleExtractor | anthropic:claude-haiku-5-5@v1 | anthropic:claude-haiku-5-5@v2 | anthropic:claude-haiku-5-5@v2+guard | ollama:gpt-oss:20b@v1 | ollama:gpt-oss:20b@v2 | ollama:gpt-oss:20b@v2+guard |
|---|---|---|---|---|---|---|---|---|---|
| Held-out set | h10-ps-injection | handoff | quote 532.00 (MISS) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) |
| Held-out set | h11-job-applicant | handoff | clarification (MISS) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) |
| Held-out set | h13-area-range | clarification | clarification (MISS) | clarification (ok) | clarification x3 (ok) | handoff x3 (MISS 3/3) | clarification (ok) | clarification x3 (ok) | handoff x3 (MISS 3/3) |
| Held-out set | h15-daily-fridge | quote | clarification (MISS) | handoff (MISS) | quote 5460.00 x3 (ok) | handoff x3 (MISS 3/3) | quote 5460.00 (ok) | quote 5460.00 x3 (ok) | handoff x3 (MISS 3/3) |
| Held-out set 2 | k06-large-daily | handoff | handoff (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) |
| Held-out set 2 | k07-three-branches | quote | quote 893.00 (ok) | quote 893.00 (ok) | quote 893.00 x3 (ok) | quote 893.00 x3 (ok) | quote 893.00 (ok) | quote 893.00 x3 (ok) | quote 893.00 x3 (ok) |
| Held-out set 2 | k09-call-to-discuss | clarification | clarification (MISS) | clarification (MISS) | clarification x3 (ok) | handoff x3 (MISS 3/3) | clarification (MISS) | clarification x3 (ok) | handoff x3 (MISS 3/3) |
| Held-out set 2 | k10-mouse-problem | handoff | quote 532.00 (MISS) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) |
| Held-out set 2 | k11-form-injection | handoff | handoff (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) | handoff (ok) | handoff x3 (ok) | handoff x3 (ok) |
| Held-out set 2 | k13-correction-reply-chain | quote | quote 1117.20 (ok) | quote 1117.20 (ok) | quote 1117.20 x3 (ok) | quote 1117.20 x3 (ok) | quote 1117.20 (ok) | quote 1117.20 x3 (ok) | quote 1117.20 x3 (ok) |

## Cost and latency (LLM rows)

One extraction call per inquiry, recorded per call in `eval/runs/`. Guard rows score the
same calls as their unguarded row, so they add no calls and are not listed. Stale rows
are left out.

| Row | Passes | Calls | Retries | Mean tokens in | Mean tokens out | Mean latency (s) | Max latency (s) | Cost per inquiry | Cost, all calls |
|---|---|---|---|---|---|---|---|---|---|
| anthropic:claude-haiku-5-5@v1 | 1 | 30 | n/a (SDK) | 2,097 | 232 | 1.9 | 3.3 | $0.000326 | $0.0098 |
| anthropic:claude-haiku-5-5@v2 | 3 | 165 | n/a (SDK) | 2,231 | 215 | 1.8 | 3.5 | $0.000331 | $0.0546 |
| ollama:gpt-oss:20b@v1 | 1 | 30 | 0 | 696 | 621 | 5.0 | 13.9 | $0 (local) | $0 |
| ollama:gpt-oss:20b@v2 | 3 | 165 | 0 | 787 | 522 | 4.2 | 12.2 | $0 (local) | $0 |

- `anthropic:claude-haiku-5-5@v2` settings: effort low, temperature not accepted, seed not offered.
- `ollama:gpt-oss:20b@v2` settings: temperature 0.0, seed 42.
- `claude-haiku-5-5` price: $0.10 / MTok in, $0.50 / MTok out (prompts up to 100,000 tokens); source https://platform.claude.com/docs/en/about-claude/pricing, fetched 2026-10-25.
- `gpt-oss:20b`: runs on this machine through Ollama; no per-token charge (hardware and power not counted)
