import json

import pytest
import yaml
from conftest import ROOT, SAMPLES

from e2q.evaluate import GOLDEN, HOLDOUT
from e2q.providers import ProviderUnavailable, ScriptedLLM, make_provider
from e2q.senders import DryRunSender, ResendSender, SenderUnavailable


def test_every_sample_is_labelled_synthetic_and_has_a_golden_entry():
    golden = yaml.safe_load(GOLDEN.read_text("utf-8"))
    files = sorted(SAMPLES.glob("*.json"))
    assert len(files) >= 15  # the brief's floor; hardening cases are added on top
    for path in files:
        data = json.loads(path.read_text("utf-8"))
        assert data["_synthetic"].startswith("SYNTHETIC"), path.name
        assert data["id"] == path.stem
        assert path.stem in golden
    assert set(golden) == {p.stem for p in files}


def test_holdout_set_pairs_every_file_with_an_entry():
    # The held-out files are owner-supplied and never edited here; this only checks they pair up.
    from e2q.evaluate import HOLDOUT, HOLDOUT_SAMPLES

    if not HOLDOUT.exists():
        pytest.skip("no held-out set present")
    holdout = yaml.safe_load(HOLDOUT.read_text("utf-8"))
    files = {p.stem for p in HOLDOUT_SAMPLES.glob("*.json")}
    assert set(holdout) == files
    for path in HOLDOUT_SAMPLES.glob("*.json"):
        assert json.loads(path.read_text("utf-8"))["_synthetic"].startswith("SYNTHETIC")


def test_golden_set_covers_the_required_cases():
    golden = yaml.safe_load(GOLDEN.read_text("utf-8"))
    outcomes = {g["outcome"] for g in golden.values()}
    assert outcomes == {"quote", "clarification", "handoff"}
    for g in golden.values():
        assert ("total" in g) == (g["outcome"] == "quote")


def test_business_config_is_marked_fictional():
    for name in ("business.yaml", "pricing.yaml"):
        assert "FICTIONAL" in (ROOT / "business" / name).read_text("utf-8").splitlines()[0]


def test_golden_totals_match_pricing_of_the_expected_extraction(business):
    # Totals in golden.yaml were worked out by hand from the rate card. Pricing the expected
    # extraction (not any extractor's output) must give exactly those totals.
    from e2q.pricing import price
    from e2q.schema import Enquiry, Quote, Site

    for path in (GOLDEN, HOLDOUT):
        if not path.exists():
            continue
        for sample_id, g in yaml.safe_load(path.read_text("utf-8")).items():
            if g["outcome"] != "quote":
                continue
            x = g["extraction"]
            enquiry = Enquiry(
                enquiry_id=sample_id,
                source="email",
                contact_email=x["contact_email"],
                service=x["service"],
                frequency=x["frequency"],
                add_ons=x["add_ons"],
                sites=[
                    Site(label=f"Site {i}", area=a, area_unit=u)
                    for i, (a, u) in enumerate(x["areas"], 1)
                ],
            )
            result = price(enquiry, business.rate_card)
            assert isinstance(result, Quote), sample_id
            assert str(result.total) == g["total"], sample_id


def test_scripted_provider_and_factory():
    llm = ScriptedLLM(["one"])
    assert llm.complete("sys", "hi").text == "one"
    with pytest.raises(ProviderUnavailable):
        llm.complete("sys", "again")
    with pytest.raises(ProviderUnavailable):
        make_provider("ollama")  # no model id: never guessed
    with pytest.raises(ValueError):
        make_provider("other", model="m")


def test_anthropic_needs_a_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ProviderUnavailable):
        make_provider("anthropic", model="owner-supplied-model-id")


def test_resend_needs_a_key(monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    with pytest.raises(SenderUnavailable):
        ResendSender()


def test_dry_run_sender_writes_outbox(tmp_path):
    ref = DryRunSender(tmp_path).send(
        key="k-v1", to="a@example.com", sender="b@example.com", subject="S", body="B"
    )
    text = (tmp_path / "k-v1.eml").read_text("utf-8")
    assert ref.endswith("k-v1.eml") and "To: a@example.com" in text and "X-E2Q-Key: k-v1" in text
