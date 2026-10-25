"""Golden-set evaluation: run every sample end to end and score it against eval/golden.yaml."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
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
FIELDS = ("is_enquiry", "contact_email", "service", "frequency", "areas", "add_ons", "out_of_scope")


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
        return [[float(a), u] for a, u in (value or [])]
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
    detail: dict = field(default_factory=dict)


@dataclass
class EvalResult:
    extractor: str
    run_date: str
    cases: list[CaseResult]

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


def run_eval(
    business: Business,
    extractor: Extractor | None = None,
    golden_path: Path = GOLDEN,
    samples_dir: Path = SAMPLES,
) -> EvalResult:
    extractor = extractor or RuleExtractor(business)
    golden = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    cases = []
    for sample_id, expected in golden.items():
        raw = RawEnquiry.model_validate(
            json.loads((samples_dir / f"{sample_id}.json").read_text(encoding="utf-8"))
        )
        enquiry = extractor.extract(raw)
        draft = build_draft(enquiry, business)
        got = observed(enquiry)
        want = expected["extraction"]
        errors = [f for f in FIELDS if normalize(f, got[f]) != normalize(f, want.get(f))]
        total = str(draft.quote.total) if draft.quote else None
        want_total = str(Decimal(expected["total"])) if expected.get("total") else None
        clar_exact = None
        if expected["outcome"] == "clarification":
            asked = [r.removeprefix("missing:") for r in draft.reasons]
            clar_exact = draft.kind == "clarification" and asked == expected.get("missing", [])
        cases.append(
            CaseResult(
                sample_id=sample_id,
                expected_outcome=expected["outcome"],
                outcome=draft.kind,
                expected_total=want_total,
                total=total,
                field_errors=errors,
                clarification_exact=clar_exact,
                detail={f: {"want": want.get(f), "got": got[f]} for f in errors},
            )
        )
    return EvalResult(
        extractor=extractor.name,
        run_date=datetime.now(UTC).strftime("%Y-%m-%d"),
        cases=cases,
    )


def pct(ok: int, n: int) -> str:
    return f"{ok}/{n} ({100 * ok / n:.0f}%)" if n else "n/a"


def render_section(title: str, source: str, result: EvalResult) -> list[str]:
    out = [
        f"## {title}",
        "",
        f"Golden file: `{source}`, {len(result.cases)} synthetic enquiries. "
        f"Extractor: `{result.extractor}`.",
        "",
        "### Summary",
        "",
        "| Measure | Result |",
        "|---|---|",
    ]
    for name, (ok, n) in result.field_accuracy().items():
        out.append(f"| Field: `{name}` | {pct(ok, n)} |")
    ok_fields = sum(ok for ok, _ in result.field_accuracy().values())
    all_fields = sum(n for _, n in result.field_accuracy().values())
    out += [
        f"| Fields, all | {pct(ok_fields, all_fields)} |",
        f"| Outcome (quote / clarification / handoff) | {pct(*result.outcome_accuracy())} |",
        f"| Price exact, on expected quotes | {pct(*result.price_exactness())} |",
        f"| Clarification asks exactly the missing fields | "
        f"{pct(*result.clarification_exactness())} |",
        "",
        "### Per enquiry",
        "",
        "| Sample | Expected | Got | Expected total | Got total | Field mismatches |",
        "|---|---|---|---|---|---|",
    ]
    for c in result.cases:
        mismatch = ", ".join(
            f"`{f}` want {c.detail[f]['want']!r} got {c.detail[f]['got']!r}" for f in c.field_errors
        )
        out.append(
            f"| {c.sample_id} | {c.expected_outcome} | {c.outcome} | {c.expected_total or '-'} "
            f"| {c.total or '-'} | {mismatch or '-'} |"
        )
    return [*out, ""]


def render_report(sections: list[tuple[str, str, EvalResult]]) -> str:
    """sections: (title, golden file shown in the report, result), one per golden set."""
    run_date = sections[0][2].run_date
    out = [
        "# Eval report",
        "",
        f"Run date: {run_date} (UTC). Generated by `uv run e2q eval`. Do not edit by hand.",
        "",
        "The original set was written in the same session as `RuleExtractor`, so its score shows",
        "that the pieces agree with each other. The held-out set was written separately, without",
        "sight of the extractor or the original samples (provenance in the `eval/holdout.yaml`",
        "header), and is the better guide to accuracy.",
        "",
    ]
    for title, source, result in sections:
        out += render_section(title, source, result)
    return "\n".join(out).rstrip("\n") + "\n"


def default_sets() -> list[tuple[str, str, Path, Path]]:
    """(title, golden file shown in the report, golden path, samples dir) for each set present."""
    sets = [("Original golden set", "eval/golden.yaml", GOLDEN, SAMPLES)]
    if HOLDOUT.exists():
        sets.append(("Held-out set", "eval/holdout.yaml", HOLDOUT, HOLDOUT_SAMPLES))
    return sets


def write_report(sections: list[tuple[str, str, EvalResult]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render_report(sections), encoding="utf-8")
