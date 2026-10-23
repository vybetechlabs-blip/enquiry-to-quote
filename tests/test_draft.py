import re

from conftest import load_sample, make_enquiry

from e2q.draft import build_draft
from e2q.pricing import fmt_money
from e2q.schema import Site


def test_quote_draft_states_every_line_total_and_assumption(business):
    draft = build_draft(make_enquiry(add_ons=["washroom_supplies"]), business)
    assert draft.kind == "quote" and draft.to == "someone@example.com"
    sym = business.rate_card.currency_symbol
    for item in draft.quote.line_items:
        assert fmt_money(item.amount, sym) in draft.body
    assert f"Total: {fmt_money(draft.quote.total, sym)} per month" in draft.body
    for assumption in draft.quote.assumptions:
        assert assumption in draft.body
    assert "valid for 30 days" in draft.body
    assert "Hi Pat," in draft.body


def test_quote_body_has_no_number_that_is_not_in_the_quote(business):
    draft = build_draft(
        make_enquiry(sites=[Site(label="Site 1", area=600, area_unit="sqft")]), business
    )
    allowed = {f"{li.amount:,.2f}" for li in draft.quote.line_items}
    allowed.add(f"{draft.quote.total:,.2f}")
    allowed.add(f"{business.rate_card.minimum_charge.amount:,.2f}")
    money = set(re.findall(r"\$([\d,]+\.\d{2})", draft.body))
    assert money <= allowed


def test_clarification_asks_exactly_the_missing_fields(business, extractor):
    draft = build_draft(extractor.extract(load_sample("s07-missing-area")), business)
    assert draft.kind == "clarification"
    assert draft.reasons == ["missing:area"]
    questions = [line for line in draft.body.splitlines() if line.startswith("- ")]
    assert questions == ["- The approximate floor area of each site, in sq ft."]


def test_clarification_for_two_missing_fields(business, extractor):
    draft = build_draft(extractor.extract(load_sample("s16-webform-incomplete")), business)
    questions = [line for line in draft.body.splitlines() if line.startswith("- ")]
    assert len(questions) == 2
    assert questions[0].startswith("- How often")
    assert "floor area" in questions[1]


def test_handoff_is_internal_and_has_no_recipient(business, extractor):
    draft = build_draft(extractor.extract(load_sample("s11-out-of-scope")), business)
    assert draft.kind == "handoff"
    assert draft.to is None
    assert draft.body.startswith("INTERNAL NOTE")
    assert "pressure washing" in draft.body


def test_injection_handoff_names_no_price(business, extractor):
    draft = build_draft(extractor.extract(load_sample("s14-prompt-injection")), business)
    assert draft.kind == "handoff" and draft.quote is None
    assert "$1" not in draft.body


def test_no_reply_address_goes_to_a_person_not_a_clarification(business):
    draft = build_draft(make_enquiry(contact_email=None), business)
    assert draft.kind == "handoff"
    assert "no reply address" in draft.body


def test_templates_leave_no_unfilled_slots(business, extractor):
    import json

    from conftest import SAMPLES

    from e2q.schema import RawEnquiry

    for path in SAMPLES.glob("*.json"):
        raw = RawEnquiry.model_validate(json.loads(path.read_text("utf-8")))
        draft = build_draft(extractor.extract(raw), business)
        assert "$" not in re.sub(r"\$[\d,]+\.\d{2}", "", draft.body), path.name
