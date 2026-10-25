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
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

import yaml

from e2q.config import Business
from e2q.draft import build_draft
from e2q.extract import Extractor, RuleExtractor
from e2q.schema import Enquiry, RawEnquiry

ROOT = Path(__file__).resolve().parent.parent
GOLDEN = ROOT / "eval" / "golden.yaml"
SAMPLES = ROOT / "inbox" / "samples"
HOLDOUT = ROOT / "eval" / "holdout.yaml"
HOLDOUT_SAMPLES = ROOT / "inbox" / "holdout"
RUNS = ROOT / "eval" / "runs"
PRICES = ROOT / "eval" / "model-prices.yaml"
FIELDS = ("is_enquiry", "contact_email", "service", "frequency", "areas", "add_ons", "out_of_scope")
# Held-out cases a client is most likely to ask about; shown side by side for every row.
CASES_TO_WATCH = ("h10-ps-injection", "h11-job-applicant", "h13-area-range", "h15-daily-fridge")


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


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


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

    @property
    def failed(self) -> bool:
        """Outcome wrong, price wrong, or a clarification that asks for the wrong fields."""
        return (
            self.outcome != self.expected_outcome
            or (self.expected_outcome == "quote" and self.total != self.expected_total)
            or self.clarification_exact is False
        )


@dataclass
class EvalResult:
    extractor: str
    run_date: str
    cases: list[CaseResult]
    golden_file: str = "eval/golden.yaml"
    golden_sha: str = ""
    prompt_sha: str | None = None
    status: str = "ok"  # ok | skipped
    skip_reason: str | None = None

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

    def to_json(self) -> str:
        return json.dumps(asdict(self), indent=2) + "\n"

    @classmethod
    def from_json(cls, text: str) -> EvalResult:
        data = json.loads(text)
        data["cases"] = [CaseResult(**c) for c in data["cases"]]
        return cls(**data)


def run_eval(
    business: Business,
    extractor: Extractor | None = None,
    golden_path: Path = GOLDEN,
    samples_dir: Path = SAMPLES,
    row: str | None = None,
    progress=None,
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
        draft = build_draft(enquiry, business)
        got = observed(enquiry)
        want = expected["extraction"]
        errors = [f for f in FIELDS if normalize(f, got[f]) != normalize(f, want.get(f))]
        total = str(draft.quote.total) if draft.quote else None
        want_total = str(Decimal(expected["total"])) if expected.get("total") else None
        asked = (
            [r.removeprefix("missing:") for r in draft.reasons]
            if draft.kind == "clarification"
            else []
        )
        clar_exact = None
        if expected["outcome"] == "clarification":
            clar_exact = draft.kind == "clarification" and asked == expected.get("missing", [])
        case = CaseResult(
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
        )
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


def run_path(row: str, golden_path: Path, runs_dir: Path | None = None) -> Path:
    slug = row.replace(":", "_").replace("/", "_")
    return (runs_dir or RUNS) / f"{slug}__{golden_path.stem}.json"


def save_run(result: EvalResult, golden_path: Path, runs_dir: Path | None = None) -> Path:
    path = run_path(result.extractor, golden_path, runs_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(result.to_json(), encoding="utf-8")
    return path


def saved_runs(golden_path: Path, runs_dir: Path | None = None) -> list[EvalResult]:
    runs_dir = runs_dir or RUNS
    if not runs_dir.exists():
        return []
    return [
        EvalResult.from_json(p.read_text(encoding="utf-8"))
        for p in sorted(runs_dir.glob(f"*__{golden_path.stem}.json"))
    ]


# --- report -------------------------------------------------------------------------------


def pct(ok: int, n: int) -> str:
    return f"{ok}/{n} ({100 * ok / n:.0f}%)" if n else "n/a"


def row_label(result: EvalResult, current_sha: str) -> str:
    if result.status == "skipped":
        return f"{result.extractor} (skipped)"
    if result.golden_sha != current_sha:
        return f"{result.extractor} (stale)"
    return result.extractor


def summary_rows(result: EvalResult) -> list[str]:
    acc = result.field_accuracy()
    ok_fields = sum(ok for ok, _ in acc.values())
    all_fields = sum(n for _, n in acc.values())
    return [
        *(pct(ok, n) for ok, n in acc.values()),
        pct(ok_fields, all_fields),
        pct(*result.outcome_accuracy()),
        pct(*result.price_exactness()),
        pct(*result.clarification_exactness()),
    ]


MEASURES = [
    *(f"Field: `{f}`" for f in FIELDS),
    "Fields, all",
    "Outcome (quote / clarification / handoff)",
    "Price exact, on expected quotes",
    "Clarification asks exactly the missing fields",
]


def render_set(title: str, golden_path: Path, results: list[EvalResult]) -> list[str]:
    current = sha(golden_path)
    n = len(yaml.safe_load(golden_path.read_text(encoding="utf-8")))
    out = [
        f"## {title}",
        "",
        f"Golden file: `{results[0].golden_file}`, {n} synthetic enquiries.",
        "",
    ]
    head = "| Measure | " + " | ".join(row_label(r, current) for r in results) + " |"
    out += [head, "|---|" + "---|" * len(results)]
    columns = [
        summary_rows(r) if r.status == "ok" and r.golden_sha == current else ["-"] * len(MEASURES)
        for r in results
    ]
    for i, measure in enumerate(MEASURES):
        out.append(f"| {measure} | " + " | ".join(col[i] for col in columns) + " |")
    out.append("")
    for r in results:
        if r.status == "skipped":
            out.append(f"- `{r.extractor}` skipped: {r.skip_reason}")
        elif r.golden_sha != current:
            out.append(
                f"- `{r.extractor}` is stale: its run ({r.run_date}) used an older `{r.golden_file}`; re-run it."
            )
        else:
            out.append(
                f"- `{r.extractor}` run {r.run_date}"
                + (f", prompt {r.prompt_sha}" if r.prompt_sha else "")
                + "."
            )
            for c in r.cases:
                if (
                    c.outcome == "clarification" == c.expected_outcome
                    and c.clarification_exact is False
                ):
                    out.append(
                        f"  - {c.sample_id}: outcome correct (clarification) but it asked for "
                        f"{c.asked} instead of {c.expected_missing}."
                    )
    out.append("")
    for r in results:
        if r.status != "ok" or r.golden_sha != current:
            continue
        out += [
            f"### Per enquiry: `{r.extractor}`",
            "",
            "| Sample | Expected | Got | Expected total | Got total | Field mismatches |",
            "|---|---|---|---|---|---|",
        ]
        for c in r.cases:
            mismatch = ", ".join(
                f"`{f}` want {c.detail[f]['want']!r} got {c.detail[f]['got']!r}"
                for f in c.field_errors
            )
            out.append(
                f"| {c.sample_id} | {c.expected_outcome} | {c.outcome} | {c.expected_total or '-'} "
                f"| {c.total or '-'} | {mismatch or '-'} |"
            )
        out.append("")
    return out  # fmt: skip


def render_watch(golden_path: Path, results: list[EvalResult]) -> list[str]:
    current = sha(golden_path)
    live = [r for r in results if r.status == "ok" and r.golden_sha == current]
    if not live:
        return []
    golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    out = [
        "## Cases to watch",
        "",
        "Held-out cases a client is most likely to ask about, with each row's outcome.",
        "",
        "| Case | Expected | " + " | ".join(r.extractor for r in live) + " |",
        "|---|---|" + "---|" * len(live),
    ]
    for case_id in CASES_TO_WATCH:
        if case_id not in golden:
            continue
        cells = []
        for r in live:
            c = next(c for c in r.cases if c.sample_id == case_id)
            mark = "ok" if not c.failed else "MISS"
            extra = f", asked {c.asked}" if c.outcome == "clarification" else ""
            extra += f", total {c.total}" if c.total else ""
            cells.append(f"{c.outcome}{extra} ({mark})")
        out.append(f"| {case_id} | {golden[case_id]['outcome']} | " + " | ".join(cells) + " |")
    return [*out, ""]


def render_cost(all_results: list[EvalResult], prices: dict) -> list[str]:
    rows = {}
    for r in all_results:
        if r.status == "ok" and r.prompt_sha:
            rows.setdefault(r.extractor, []).extend(c for c in r.cases if c.tokens_in is not None)
        elif r.status == "skipped":
            rows.setdefault(r.extractor, [])
    if not rows:
        return []
    out = [
        "## Cost and latency (LLM rows)",
        "",
        "One extraction call per enquiry; tokens and latency are recorded per call in `eval/runs/`.",
        "",
        "| Row | Calls | Mean tokens in | Mean tokens out | Mean latency (s) | Max latency (s) | Cost per enquiry |",
        "|---|---|---|---|---|---|---|",
    ]
    notes = []
    for name, cases in rows.items():
        model = name.split(":", 1)[1] if ":" in name else name
        price = prices.get(model, {})
        if not cases:
            out.append(f"| {name} | 0 | - | - | - | - | not run |")
        else:
            k = len(cases)
            tin = sum(c.tokens_in for c in cases) / k
            tout = sum(c.tokens_out for c in cases) / k
            lat = [c.latency_s for c in cases]
            if price.get("local"):
                cost = "$0 (local)"
            elif "input_per_mtok" in price:
                usd = (
                    tin * float(price["input_per_mtok"]) / 1e6
                    + tout * float(price["output_per_mtok"]) / 1e6
                )
                cost = f"${usd:.6f}"
            else:
                cost = "unverified"
            out.append(
                f"| {name} | {k} | {tin:,.0f} | {tout:,.0f} | {sum(lat) / k:.1f} | {max(lat):.1f} | {cost} |"
            )
        if price.get("source"):
            notes.append(
                f"- `{model}`: ${price['input_per_mtok']} / MTok in, ${price['output_per_mtok']} / MTok out "
                f"({price.get('condition', '')}); source {price['source']}, fetched {price['fetched']}."
            )
        elif price.get("local"):
            notes.append(f"- `{model}`: {price.get('note', 'runs locally')}")
    return [*out, "", *notes, ""]  # fmt: skip


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
        "that the pieces agree with each other. The held-out set was written separately, without",
        "sight of the extractor or the original samples (provenance in the `eval/holdout.yaml`",
        "header), and is the better guide to accuracy. `RuleExtractor` is the baseline and is not",
        "changed while LLM rows are measured.",
        "",
        "LLM rows (`provider:model`) use `LLMExtractor`. Its prompt carries the extraction schema and",
        "the service, frequency, add-on and out-of-scope categories with their labels from",
        "`business/pricing.yaml`; it carries no keyword maps from `business/business.yaml` and no",
        "patterns from `e2q/extract/rules.py`. LLM runs are not deterministic: each saved run is one",
        "pass.",
        "",
    ]
    all_results = []
    for title, golden_path, results in sets:
        out += render_set(title, golden_path, results)
        all_results += results
    for _title, golden_path, results in sets:
        if golden_path == HOLDOUT or golden_path.stem == "holdout":
            out += render_watch(golden_path, results)
    out += render_cost(all_results, prices or {})
    return "\n".join(out).rstrip("\n") + "\n"


def default_sets() -> list[tuple[str, Path, Path]]:
    """(title, golden path, samples dir) for each set present."""
    sets = [("Original golden set", GOLDEN, SAMPLES)]
    if HOLDOUT.exists():
        sets.append(("Held-out set", HOLDOUT, HOLDOUT_SAMPLES))
    return sets


def load_prices(path: Path = PRICES) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}


def write_report(sets: list[tuple[str, Path, list[EvalResult]]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(sets, load_prices()), encoding="utf-8")
