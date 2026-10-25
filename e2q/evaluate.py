"""Golden-set evaluation: run every sample end to end and score it against a golden file.

Two golden sets: the original (`eval/golden.yaml`, `inbox/samples/`) and the held-out set
(`eval/holdout.yaml`, `inbox/holdout/`). RuleExtractor is re-run on every `e2q eval`. LLM rows
cost time or money, so each run is saved to `eval/runs/` with the hash of the golden file and of
the prompt it ran against; the report reuses saved runs and marks a row stale when its golden
file has changed since.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import ClassVar

import yaml
from smb_agent_kit import evals
from smb_agent_kit.evals import EvalRun, cell, render_spread, sha

from e2q.config import Business
from e2q.draft import build_draft
from e2q.extract import Extractor, RuleExtractor
from e2q.schema import Enquiry, RawEnquiry

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "golden.yaml"
SAMPLES = ROOT / "inbox" / "samples"
HOLDOUT = ROOT / "eval" / "holdout.yaml"
HOLDOUT_SAMPLES = ROOT / "inbox" / "holdout"
HOLDOUT2 = ROOT / "eval" / "holdout2.yaml"
HOLDOUT2_SAMPLES = ROOT / "inbox" / "holdout2"
RUNS = ROOT / "eval" / "runs"
PRICES = ROOT / "eval" / "model-prices.yaml"
FIELDS = ("is_enquiry", "contact_email", "service", "frequency", "areas", "add_ons", "out_of_scope")
# Held-out cases a client is most likely to ask about, per golden file; shown for every row.
CASES_TO_WATCH: dict[str, tuple[str, ...]] = {
    "holdout": ("h10-ps-injection", "h11-job-applicant", "h13-area-range", "h15-daily-fridge"),
    # From the "Cases to watch" list in the eval/holdout2.yaml header.
    "holdout2": ("k06", "k07", "k09", "k10", "k11", "k13"),
}


def observed(enquiry: Enquiry) -> dict:
    return {
        "is_enquiry": enquiry.is_enquiry,
        "contact_email": enquiry.contact_email,
        "service": enquiry.service,
        "frequency": enquiry.frequency,
        "areas": [[s.area, s.area_unit] for s in enquiry.sites],
        "add_ons": sorted(enquiry.add_ons),
        "out_of_scope": sorted(enquiry.out_of_scope),
    }


def normalize(name: str, value):
    if name in ("add_ons", "out_of_scope"):
        return sorted(value or [])
    if name == "areas":
        # A site with no area figure means "no area given", which the golden files write as [].
        return [[float(a), u] for a, u in (value or []) if a is not None]
    return value


@dataclass
class CaseResult:
    sample_id: str
    expected_outcome: str
    outcome: str
    expected_total: str | None
    total: str | None
    field_errors: list[str]
    clarification_exact: bool | None
    expected_missing: list[str] = field(default_factory=list)
    asked: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    detail: dict = field(default_factory=dict)
    tokens_in: int | None = None
    tokens_out: int | None = None
    latency_s: float | None = None
    retries: int | None = None
    observed: dict | None = None
    needs_human: list[str] = field(default_factory=list)

    @property
    def failed(self) -> bool:
        """Outcome wrong, price wrong, or a clarification that asks for the wrong fields."""
        return (
            self.outcome != self.expected_outcome
            or (self.expected_outcome == "quote" and self.total != self.expected_total)
            or self.clarification_exact is False
        )


class EvalResult(EvalRun):
    """A saved pass (field order and JSON from the kit's EvalRun) plus this project's measures."""

    case_type: ClassVar[type] = CaseResult

    def field_accuracy(self) -> dict[str, tuple[int, int]]:
        n = len(self.cases)
        return {f: (sum(f not in c.field_errors for c in self.cases), n) for f in FIELDS}

    def outcome_accuracy(self) -> tuple[int, int]:
        return sum(c.outcome == c.expected_outcome for c in self.cases), len(self.cases)

    def price_exactness(self) -> tuple[int, int]:
        quotes = [c for c in self.cases if c.expected_outcome == "quote"]
        return sum(c.total == c.expected_total for c in quotes), len(quotes)

    def clarification_exactness(self) -> tuple[int, int]:
        clar = [c for c in self.cases if c.clarification_exact is not None]
        return sum(bool(c.clarification_exact) for c in clar), len(clar)


def provider_settings(extractor) -> dict:
    """Sampling settings of the provider behind an LLM row (guard rows wrap one)."""
    inner = getattr(extractor, "llm", extractor)
    provider = getattr(inner, "provider", None)
    return dict(getattr(provider, "settings", None) or {})


def score_case(
    business: Business, enquiry: Enquiry, call, sample_id: str, expected: dict
) -> CaseResult:
    """Price and draft one extraction, then score it against its golden entry."""
    draft = build_draft(enquiry, business)
    got = observed(enquiry)
    want = expected["extraction"]
    errors = [f for f in FIELDS if normalize(f, got[f]) != normalize(f, want.get(f))]
    total = str(draft.quote.total) if draft.quote else None
    want_total = str(Decimal(expected["total"])) if expected.get("total") else None
    asked = (
        [r.removeprefix("missing:") for r in draft.reasons] if draft.kind == "clarification" else []
    )
    clar_exact = None
    if expected["outcome"] == "clarification":
        clar_exact = draft.kind == "clarification" and asked == expected.get("missing", [])
    return CaseResult(
        sample_id=sample_id,
        expected_outcome=expected["outcome"],
        outcome=draft.kind,
        expected_total=want_total,
        total=total,
        field_errors=errors,
        clarification_exact=clar_exact,
        expected_missing=expected.get("missing", []),
        asked=asked,
        reasons=list(draft.reasons),
        detail={f: {"want": want.get(f), "got": got[f]} for f in errors},
        tokens_in=call.tokens_in if call else None,
        tokens_out=call.tokens_out if call else None,
        latency_s=round(call.latency_s, 2) if call else None,
        retries=call.retries if call else None,
        observed=got,
        needs_human=list(enquiry.needs_human),
    )


def run_eval(
    business: Business,
    extractor: Extractor | None = None,
    golden_path: Path = GOLDEN,
    samples_dir: Path = SAMPLES,
    row: str | None = None,
    progress=None,
    pass_index: int = 1,
) -> EvalResult:
    extractor = extractor or RuleExtractor(business)
    golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    calls = getattr(extractor, "calls", None)
    cases = []
    for sample_id, expected in golden.items():
        raw = RawEnquiry.model_validate(
            json.loads((samples_dir / f"{sample_id}.json").read_text(encoding="utf-8"))
        )
        before = len(calls) if calls is not None else 0
        enquiry = extractor.extract(raw)
        call = calls[-1] if calls is not None and len(calls) > before else None
        case = score_case(business, enquiry, call, sample_id, expected)
        cases.append(case)
        if progress:
            progress(case)
    return EvalResult(
        extractor=row or extractor.name,
        run_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        cases=cases,
        golden_file=golden_path.relative_to(ROOT).as_posix() if golden_path.is_relative_to(ROOT) else golden_path.name,
        golden_sha=sha(golden_path),
        prompt_sha=(
            hashlib.sha256(extractor.system_prompt.encode()).hexdigest()[:12]
            if hasattr(extractor, "system_prompt")
            else None
        ),
        pass_index=pass_index,
        settings=provider_settings(extractor),
    )  # fmt: skip


def skipped(row: str, golden_path: Path, reason: str) -> EvalResult:
    return EvalResult(
        extractor=row,
        run_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        cases=[],
        golden_file=golden_path.relative_to(ROOT).as_posix(),
        golden_sha=sha(golden_path),
        status="skipped",
        skip_reason=reason,
    )


def run_path(
    row: str, golden_path: Path, runs_dir: Path | None = None, pass_index: int = 1
) -> Path:
    return evals.run_path(row, golden_path, runs_dir or RUNS, pass_index)


def save_run(result: EvalResult, golden_path: Path, runs_dir: Path | None = None) -> Path:
    return evals.save_run(result, golden_path, runs_dir or RUNS)


def saved_runs(golden_path: Path, runs_dir: Path | None = None) -> list[EvalResult]:
    return evals.load_runs(EvalResult, golden_path, runs_dir or RUNS)


# --- report -------------------------------------------------------------------------------


def display(name: str) -> str:
    """LLM rows saved before prompt versions existed are v1; say so in the report."""
    if ":" in name and "@" not in name:
        return f"{name}@v1"
    return name


def group_runs(results: list[EvalResult]) -> dict[str, list[EvalResult]]:
    return evals.group_runs(results, display, first="RuleExtractor")


def measures(result: EvalResult) -> list[tuple[int, int]]:
    acc = result.field_accuracy()
    ok_fields = sum(ok for ok, _ in acc.values())
    all_fields = sum(n for _, n in acc.values())
    return [
        *acc.values(),
        (ok_fields, all_fields),
        result.outcome_accuracy(),
        result.price_exactness(),
        result.clarification_exactness(),
    ]


MEASURES = [
    *(f"Field: `{f}`" for f in FIELDS),
    "Fields, all",
    "Outcome (quote / clarification / handoff)",
    "Price exact, on expected quotes",
    "Clarification asks exactly the missing fields",
]


def label(name: str, runs: list[EvalResult], current: str) -> str:
    return evals.label(name, runs, current, display)


def render_set(title: str, golden_path: Path, results: list[EvalResult]) -> list[str]:
    current = sha(golden_path)
    n = len(yaml.safe_load(golden_path.read_text(encoding="utf-8")))
    groups = group_runs(results)
    rel = (
        golden_path.relative_to(ROOT).as_posix()
        if golden_path.is_relative_to(ROOT)
        else golden_path.name
    )
    out = [f"## {title}", "", f"Golden file: `{rel}`, {n} synthetic inquiries.", ""]
    out += [
        "| Measure | " + " | ".join(label(k, v, current) for k, v in groups.items()) + " |",
        "|---|" + "---|" * len(groups),
    ]
    columns = []
    for runs in groups.values():
        ok = [r for r in runs if r.status == "ok"]
        columns.append(
            [cell(vals) for vals in zip(*(measures(r) for r in ok), strict=True)]
            if ok
            else ["-"] * len(MEASURES)
        )
    for i, measure in enumerate(MEASURES):
        out.append(f"| {measure} | " + " | ".join(col[i] for col in columns) + " |")
    out += [
        "",
        "Rows with several passes show the mean, then the lowest and highest pass in brackets.",
        "",
    ]

    for name, runs in groups.items():
        ok = [r for r in runs if r.status == "ok"]
        if not ok:
            out.append(f"- `{display(name)}` skipped: {runs[0].skip_reason}")
            continue
        first = ok[0]
        bits = [f"run {first.run_date}"]
        if first.prompt_sha:
            bits.append(f"prompt {first.prompt_sha}")
        if len(ok) > 1:
            bits.append(f"{len(ok)} passes")
        if first.settings:
            bits.append(", ".join(f"{k} {v}" for k, v in first.settings.items()))
        line = f"- `{display(name)}`: " + "; ".join(bits) + "."
        if first.golden_sha != current:
            line += f" Stale: scored on an earlier `{first.golden_file}` ({len(first.cases)} cases); kept for comparison."
        out.append(line)
        for note in first.notes:
            out.append(f"  - {note}")
        if first.golden_sha == current:
            for c in first.cases:
                if (
                    c.outcome == "clarification" == c.expected_outcome
                    and c.clarification_exact is False
                ):
                    out.append(
                        f"  - {c.sample_id}: outcome correct (clarification) but it asked for "
                        f"{c.asked} instead of {c.expected_missing}."
                    )
    out.append("")

    out += render_spread(groups, current, EvalResult.outcome_accuracy, display)

    live = {
        k: [r for r in v if r.status == "ok" and r.golden_sha == current] for k, v in groups.items()
    }
    live = {k: v for k, v in live.items() if v}
    golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    out += [
        "### Per inquiry",
        "",
        "| Sample | Expected | " + " | ".join(display(k) for k in live) + " |",
        "|---|---|" + "---|" * len(live),
    ]
    for sample_id, g in golden.items():
        cells = []
        for runs in live.values():
            cases = [next(c for c in r.cases if c.sample_id == sample_id) for r in runs]
            bad = [c for c in cases if c.failed]
            if len(cases) == 1:
                cells.append("ok" if not bad else f"MISS: {bad[0].outcome}")
            elif not bad:
                cells.append(f"ok {len(cases)}/{len(cases)}")
            else:
                wrong = sorted({c.outcome for c in bad})
                cells.append(f"MISS {len(bad)}/{len(cases)} ({', '.join(wrong)})")
        out.append(f"| {sample_id} | {g['outcome']} | " + " | ".join(cells) + " |")
    out.append("")

    failures = []
    for name, runs in live.items():
        for r in runs:
            tag = f" pass {r.pass_index}" if len(runs) > 1 else ""
            for c in r.cases:
                if not c.failed:
                    continue
                want = c.expected_outcome + (f" {c.expected_total}" if c.expected_total else "")
                got = c.outcome + (f" {c.total}" if c.total else "")
                if c.outcome == "clarification":
                    got += f" asking {c.asked}"
                fields = ", ".join(
                    f"`{f}` want {c.detail[f]['want']!r} got {c.detail[f]['got']!r}"
                    for f in c.field_errors
                )
                reasons = f" reasons {c.reasons}" if c.reasons else ""
                failures.append(
                    f"- `{display(name)}`{tag}: {c.sample_id}: want {want}, got {got};{reasons}"
                    + (f" fields: {fields}" if fields else "")
                )
    out += ["### Failures", ""] + (failures or ["- none"]) + [""]
    return out


def render_watch(sets: list[tuple[str, Path, list[EvalResult]]]) -> list[str]:
    """One table across every held-out set and every row (a row that did not run says so)."""
    names: list[str] = []
    for _title, _golden, results in sets:
        for name in group_runs(results):
            if name not in names:
                names.append(name)
    rows: list[str] = []
    for title, golden_path, results in sets:
        ids = CASES_TO_WATCH.get(golden_path.stem, ())
        if not ids:
            continue
        current = sha(golden_path)
        golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
        groups = group_runs(results)
        # An id may be a full sample id or its prefix ("k06" for "k06-large-daily").
        resolved = [g for cid in ids for g in golden if g == cid or g.startswith(f"{cid}-")]
        for case_id in resolved:
            cells = []
            for name in names:
                runs = [r for r in groups.get(name, []) if r.status == "ok"]
                if not runs:
                    cells.append("not run")
                    continue
                if runs[0].golden_sha != current:
                    cells.append("stale")
                    continue
                cases = [next(c for c in r.cases if c.sample_id == case_id) for r in runs]
                outcomes: dict[str, int] = {}
                for c in cases:
                    key = c.outcome + (f" {c.total}" if c.total else "")
                    outcomes[key] = outcomes.get(key, 0) + 1
                bad = sum(c.failed for c in cases)
                text = ", ".join(f"{k} x{v}" if len(cases) > 1 else k for k, v in outcomes.items())
                mark = (
                    "ok" if not bad else (f"MISS {bad}/{len(cases)}" if len(cases) > 1 else "MISS")
                )
                cells.append(f"{text} ({mark})")
            rows.append(
                f"| {title} | {case_id} | {golden[case_id]['outcome']} | "
                + " | ".join(cells)
                + " |"
            )
    if not rows:
        return []
    return [
        "## Cases to watch",
        "",
        "Held-out cases a client is most likely to ask about, with each row's outcome.",
        "",
        "| Set | Case | Expected | " + " | ".join(display(n) for n in names) + " |",
        "|---|---|---|" + "---|" * len(names),
        *rows,
        "",
    ]


def render_cost(sets: list[tuple[str, Path, list[EvalResult]]], prices: dict) -> list[str]:
    return evals.render_cost(
        sets,
        prices,
        intro=[
            "One extraction call per inquiry, recorded per call in `eval/runs/`. Guard rows score the",
            "same calls as their unguarded row, so they add no calls and are not listed. Stale rows",
            "are left out.",
        ],
        noun="inquiry",
        display=display,
        include=lambda r: not r.extractor.endswith("+guard"),
        counts_retries=lambda name: name.startswith("ollama:"),
    )


def render_report(
    sets: list[tuple[str, Path, list[EvalResult]]], prices: dict | None = None
) -> str:
    run_date = datetime.now(UTC).strftime("%Y-%m-%d")
    out = [
        "# Eval report",
        "",
        f"Rendered {run_date} (UTC) by `uv run e2q eval`. Do not edit by hand.",
        "",
        "The original set was written in the same session as `RuleExtractor`, so its score shows",
        "that the pieces agree with each other. The held-out sets were written separately, without",
        "sight of the extractor or the original samples (provenance in each held-out YAML header),",
        "and are the better guide to accuracy. `RuleExtractor` is the baseline and is not changed",
        "while LLM rows are measured.",
        "",
        "LLM rows are named `provider:model@prompt`; `+guard` rows also run `RuleExtractor` and hand",
        "off when the two disagree on a field a quote needs. The prompt carries the extraction schema",
        "and the service, frequency, add-on and out-of-scope categories with their labels from",
        "`business/pricing.yaml`; it carries no keyword maps from `business/business.yaml` and no",
        "patterns from `e2q/extract/rules.py`. Each saved run is one pass.",
        "",
    ]
    for title, golden_path, results in sets:
        out += render_set(title, golden_path, results)
    out += render_watch(sets)
    out += render_cost(sets, prices or {})
    return "\n".join(out).rstrip("\n") + "\n"


def default_sets() -> list[tuple[str, Path, Path]]:
    """(title, golden path, samples dir) for each set present."""
    sets = [("Original golden set", GOLDEN, SAMPLES)]
    if HOLDOUT.exists():
        sets.append(("Held-out set", HOLDOUT, HOLDOUT_SAMPLES))
    if HOLDOUT2.exists():
        sets.append(("Held-out set 2", HOLDOUT2, HOLDOUT2_SAMPLES))
    return sets


def load_prices(path: Path = PRICES) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_report(sets: list[tuple[str, Path, list[EvalResult]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(sets, load_prices()), encoding="utf-8", newline="\n")
