"""Re-score saved LLM runs after a pricing or answer-key change, without calling a model again.

Each saved case is turned back into the `Enquiry` the model produced, then priced and drafted
with the current code and scored against the current golden file. Runs saved before cases
carried their full extraction (`CaseResult.observed`) are rebuilt from the golden file they were
scored against, recovered from git by its hash, plus the mismatches the run recorded.

`fill` makes new model calls only where a run has no usable output: cases added to the golden
file after the run, and calls that failed for infrastructure reasons (provider errors). Guard
rows are always rebuilt from their unguarded row's outputs, so they never need their own calls.
"""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path

import yaml
from smb_agent_kit import evals

from e2q.config import Business
from e2q.evaluate import ROOT, CaseResult, EvalResult, score_case, sha
from e2q.extract import LLMExtractor, RuleExtractor
from e2q.extract.guard import disagreements
from e2q.providers import LLMProvider
from e2q.schema import Enquiry, RawEnquiry, Site

NEEDS_HUMAN_KINDS = ("injection", "unsupported_frequency", "extraction_failed")
INFRA_FAILURE = "extraction_failed:"
PARSE_FAILURE = "extraction_failed:invalid_reply"


def golden_at(golden_path: Path, golden_sha: str) -> dict:
    """The golden file as it was when a run was scored (kit lookup by hash, this repo's git)."""
    return evals.golden_at(golden_path, golden_sha, ROOT)


def rebuild(case: CaseResult, old_expected: dict | None) -> Enquiry:
    """The Enquiry the extractor produced for this case."""
    if case.observed is not None:
        got, needs_human = dict(case.observed), list(case.needs_human)
    else:
        if old_expected is None:
            raise LookupError(f"{case.sample_id}: no saved extraction and no golden entry")
        got = dict(old_expected["extraction"])
        for name, pair in case.detail.items():
            got[name] = pair["got"]
        needs_human = [r for r in case.reasons if r.split(":", 1)[0] in NEEDS_HUMAN_KINDS]
    return Enquiry(
        enquiry_id=case.sample_id,
        source="email",
        is_enquiry=bool(got.get("is_enquiry", True)),
        contact_email=got.get("contact_email"),
        service=got.get("service"),
        frequency=got.get("frequency"),
        sites=[
            Site(label=f"Site {i}", area=a, area_unit=u)
            for i, (a, u) in enumerate(got.get("areas") or [], 1)
        ],
        add_ons=list(got.get("add_ons") or []),
        out_of_scope=list(got.get("out_of_scope") or []),
        needs_human=needs_human,
    )


def with_guard(enquiry: Enquiry, raw: RawEnquiry, rules: RuleExtractor) -> Enquiry:
    """Apply the --guard rule to a model extraction (same logic as GuardedExtractor)."""
    guarded = enquiry.model_copy(deep=True)
    if not guarded.is_enquiry or any(r.startswith(INFRA_FAILURE) for r in guarded.needs_human):
        return guarded
    differ = disagreements(guarded, rules.extract(raw))
    if differ:
        guarded.needs_human.append(f"extractors_disagree:{','.join(differ)}")
    return guarded


def load_raw(samples_dir: Path, sample_id: str) -> RawEnquiry:
    return RawEnquiry.model_validate(
        json.loads((samples_dir / f"{sample_id}.json").read_text(encoding="utf-8"))
    )


def rescore_run(
    business: Business,
    plain: EvalResult,
    guard: EvalResult | None,
    golden_path: Path,
    samples_dir: Path,
    provider: LLMProvider | None = None,
    prompt_version: str = "v1",
) -> tuple[EvalResult, EvalResult | None, list[str]]:
    """Re-score one saved run (and its guard twin). Returns the new runs and the new calls made."""
    current = yaml.safe_load(golden_path.read_text(encoding="utf-8"))
    old = golden_at(golden_path, plain.golden_sha)
    saved = {c.sample_id: c for c in plain.cases}
    rules = RuleExtractor(business)
    extractor = LLMExtractor(business, provider, prompt_version) if provider else None
    plain_cases, guard_cases, new_calls = [], [], []
    for sample_id, expected in current.items():
        raw = load_raw(samples_dir, sample_id)
        case = saved.get(sample_id)
        infra = case is not None and any(
            r.startswith(INFRA_FAILURE) and r != PARSE_FAILURE
            for r in (case.needs_human or case.reasons)
        )
        if case is None or infra:
            if extractor is None:
                if case is None:
                    continue  # no output and no provider: leave the case out
                enquiry, call = rebuild(case, old.get(sample_id)), None
            else:
                before = len(extractor.calls)
                enquiry = extractor.extract(raw)
                call = extractor.calls[-1] if len(extractor.calls) > before else None
                new_calls.append(
                    sample_id + (" (re-called: infrastructure failure)" if infra else " (new case)")
                )
        else:
            enquiry, call = rebuild(case, old.get(sample_id)), None
        scored = score_case(business, enquiry, call, sample_id, expected)
        if call is None and case is not None:
            scored = replace(
                scored,
                tokens_in=case.tokens_in,
                tokens_out=case.tokens_out,
                latency_s=case.latency_s,
                retries=case.retries,
            )
        plain_cases.append(scored)
        if guard is not None:
            g = score_case(business, with_guard(enquiry, raw, rules), None, sample_id, expected)
            guard_cases.append(
                replace(g, tokens_in=scored.tokens_in, tokens_out=scored.tokens_out,
                        latency_s=scored.latency_s, retries=scored.retries)
            )  # fmt: skip
    today = datetime.now(UTC).strftime("%Y-%m-%d")
    note = (
        f"{today}: re-scored from saved outputs against {plain.golden_file} {sha(golden_path)} "
        f"(run was scored against {plain.golden_sha}) with the current pricing code"
        + (f"; new calls: {', '.join(new_calls)}" if new_calls else "; no new calls")
    )
    new_plain = replace(
        plain, cases=plain_cases, golden_sha=sha(golden_path), notes=[*plain.notes, note]
    )
    new_guard = (
        replace(guard, cases=guard_cases, golden_sha=sha(golden_path), notes=[*guard.notes, note])
        if guard is not None
        else None
    )
    return new_plain, new_guard, new_calls
