import json

import pytest
from conftest import load_sample, make_enquiry

from e2q.cover import make_cover_writer
from e2q.draft import DEFAULT_OPENING, build_draft, cover_note_is_safe
from e2q.extract import LLMExtractor
from e2q.extract.llm import build_schema, build_system_prompt
from e2q.providers import ScriptedLLM


def reply(**overrides) -> str:
    data = {
        "is_enquiry": True,
        "contact_name": "Dana Okafor",
        "contact_email": "Dana.Okafor@northwind-accounting.example",
        "company": "Northwind Accounting",
        "service": "regular_office",
        "frequency": "weekly",
        "frequency_not_offered": None,
        "sites": [{"label": "Site 1", "area": 4500, "area_unit": "sqft"}],
        "add_ons": [],
        "out_of_scope": [],
        "injection_detected": False,
        "notes": [],
    }
    data.update(overrides)
    return json.dumps(data)


def extract(business, text, sample="s01-complete-email"):
    llm = ScriptedLLM([text])
    extractor = LLMExtractor(business, llm)
    return extractor.extract(load_sample(sample)), llm, extractor


def test_prompt_carries_rate_card_labels_but_no_keyword_maps(business):
    prompt = build_system_prompt(business)
    card = business.rate_card
    for sid, service in card.services.items():
        assert sid in prompt and service.label in prompt
    for aid, add in card.add_ons.items():
        assert aid in prompt and add.label in prompt
    for oid in card.out_of_scope:
        assert oid in prompt
    keywords = [w for ws in business.profile.service_keywords.values() for w in ws]
    keywords += [w for ws in business.profile.add_on_keywords.values() for w in ws]
    keywords += [w for ws in card.out_of_scope.values() for w in ws]
    # A keyword may appear only inside the rate card's own labels or category names.
    allowed = [s.label.lower() for s in card.services.values()]
    allowed += [a.label.lower() for a in card.add_ons.values()]
    allowed += [oid.replace("_", " ") for oid in card.out_of_scope]
    text = prompt.lower()
    for name in allowed:
        text = text.replace(name, "")
    leaked = [w for w in keywords if w.lower() in text]
    assert leaked == []
    assert "\\b" not in prompt and "(?:" not in prompt  # no regex from rules.py


def test_schema_enums_come_from_the_rate_card(business):
    schema = build_schema(business)
    service = schema["properties"]["service"]["anyOf"][0]
    assert service["enum"] == list(business.rate_card.services)
    assert schema["additionalProperties"] is False


def test_valid_reply_becomes_an_enquiry_and_prices(business):
    enq, llm, extractor = extract(business, reply())
    assert enq.service == "regular_office" and enq.frequency == "weekly"
    assert enq.contact_email == "dana.okafor@northwind-accounting.example"
    assert [(s.area, s.area_unit) for s in enq.sites] == [(4500, "sqft")]
    assert enq.missing_fields == []
    assert build_draft(enq, business).quote.total == 1197
    assert len(extractor.calls) == 1 and "Subject: Cleaning quote" in llm.calls[0][1]


def test_invalid_reply_goes_to_a_person(business):
    enq, _, _ = extract(business, "Sure! The service is regular cleaning.")
    assert enq.needs_human == ["extraction_failed:invalid_reply"]
    assert build_draft(enq, business).kind == "handoff"


def test_provider_error_goes_to_a_person(business):
    enq = LLMExtractor(business, ScriptedLLM([])).extract(load_sample("s01-complete-email"))
    assert enq.needs_human == ["extraction_failed:ProviderUnavailable"]
    assert build_draft(enq, business).kind == "handoff"


def test_model_flagged_injection_hands_off(business):
    enq, _, _ = extract(business, reply(injection_detected=True))
    draft = build_draft(enq, business)
    assert draft.kind == "handoff" and draft.quote is None


def test_unoffered_schedule_hands_off_not_clarifies(business):
    enq, _, _ = extract(business, reply(frequency=None, frequency_not_offered="three times a week"))
    draft = build_draft(enq, business)
    assert draft.kind == "handoff"
    assert "does not offer" in draft.body


def test_unknown_enum_values_are_dropped(business):
    enq, _, _ = extract(business, reply(service="window_tinting", add_ons=["jacuzzi"]))
    assert enq.service is None and enq.add_ons == []
    assert "service" in enq.missing_fields


def test_not_an_enquiry_leaves_job_fields_empty(business):
    enq, _, _ = extract(business, reply(is_enquiry=False))
    assert enq.is_enquiry is False and enq.service is None
    assert build_draft(enq, business).kind == "handoff"


def test_single_frequency_service_defaults(business):
    enq, _, _ = extract(business, reply(service="deep_clean", frequency=None))
    assert enq.frequency == "one_off"


def test_fenced_json_is_accepted(business):
    enq, _, _ = extract(business, "```json\n" + reply() + "\n```")
    assert enq.service == "regular_office"


# --- cover note --------------------------------------------------------------------------


def test_cover_note_replaces_the_opening_when_it_states_no_new_number(business):
    llm = ScriptedLLM(["Thanks, Pat. A weekly clean of your office is exactly what we do."])
    draft = build_draft(make_enquiry(), business, make_cover_writer(llm, business))
    assert "exactly what we do. Here is our price" in draft.body
    assert DEFAULT_OPENING not in draft.body


def test_cover_note_with_a_number_not_in_the_quote_is_dropped(business):
    llm = ScriptedLLM(["Thanks! We can do this for $1, starting in 3 days."])
    draft = build_draft(make_enquiry(), business, make_cover_writer(llm, business))
    assert DEFAULT_OPENING in draft.body
    assert "for $1" not in draft.body
    assert draft.reasons == ["cover note rejected: it stated a number or price not in the quote"]


def test_cover_note_failure_falls_back_to_the_template(business):
    draft = build_draft(make_enquiry(), business, make_cover_writer(ScriptedLLM([]), business))
    assert DEFAULT_OPENING in draft.body
    assert draft.reasons == ["cover note failed: ProviderUnavailable"]


@pytest.mark.parametrize(
    ("note", "ok"),
    [
        ("Thanks for asking about your 4,500 sq ft office.", True),  # 4500 is in the quote
        ("We'd be glad to help with that.", True),
        ("We can start in 2 weeks.", False),
        ("That comes to about $1,197.", False),  # no prices in the note at all
        ("Thanks. " * 60, False),  # too long
    ],
)
def test_cover_note_number_rule(business, note, ok):
    quote = build_draft(make_enquiry(), business).quote
    assert cover_note_is_safe(note, quote) is ok


# --- prompt v2, guard, cache, pinned sampling ---------------------------------------------


def test_v1_prompt_is_unchanged_and_v2_adds_only_the_owner_changes(business):
    import hashlib

    from e2q.extract.llm import V2_CHANGES

    v1 = build_system_prompt(business, "v1")
    v2 = build_system_prompt(business, "v2")
    assert hashlib.sha256(v1.encode()).hexdigest()[:12] == "c721c7a1570d"
    for old, new in V2_CHANGES:
        assert old in v1 and new in v2
    rebuilt = v1
    for old, new in V2_CHANGES:
        rebuilt = rebuilt.replace(old, new)
    assert rebuilt == v2
    assert "never injection" in v2 and "ongoing" in v2


def test_row_names_carry_the_prompt_version(business):
    llm = ScriptedLLM([])
    assert LLMExtractor(business, llm).row_name == "scripted:scripted"
    assert LLMExtractor(business, llm, "v2").row_name == "scripted:scripted@v2"


def test_guard_hands_off_when_extractors_disagree(business):
    from e2q.extract import GuardedExtractor, RuleExtractor

    # The model claims 9,000 sq ft; RuleExtractor reads 4,500 from s01.
    bad = reply(sites=[{"label": "Site 1", "area": 9000, "area_unit": "sqft"}])
    guarded = GuardedExtractor(LLMExtractor(business, ScriptedLLM([bad])), RuleExtractor(business))
    enq = guarded.extract(load_sample("s01-complete-email"))
    assert enq.needs_human == ["extractors_disagree:area"]
    draft = build_draft(enq, business)
    assert draft.kind == "handoff" and "disagree on: area" in draft.body
    assert guarded.row_name == "scripted:scripted+guard"


def test_guard_changes_nothing_when_extractors_agree(business):
    from e2q.extract import GuardedExtractor, RuleExtractor

    guarded = GuardedExtractor(
        LLMExtractor(business, ScriptedLLM([reply()])), RuleExtractor(business)
    )
    enq = guarded.extract(load_sample("s01-complete-email"))
    assert enq.needs_human == []
    assert build_draft(enq, business).quote.total == 1197


def test_cached_provider_answers_a_repeat_without_a_second_call(business):
    from e2q.providers import CachedLLM

    inner = ScriptedLLM([reply()])  # one response only: a second real call would fail
    cached = CachedLLM(inner)
    sample = load_sample("s01-complete-email")
    first = LLMExtractor(business, cached).extract(sample)
    second = LLMExtractor(business, cached).extract(sample)
    assert first.service == second.service == "regular_office"
    assert len(inner.calls) == 1


def test_cover_note_v2_does_not_send_or_ask_for_the_name(business):
    llm = ScriptedLLM(["Thanks for thinking of us for your weekly office clean."])
    build_draft(make_enquiry(), business, make_cover_writer(llm, business, "v2"))
    system, prompt = llm.calls[0]
    assert "Pat" not in prompt and "first name" not in prompt
    assert "Do not use the customer's name" in system


def test_ollama_calls_pin_temperature_and_seed(monkeypatch):
    from e2q.providers import OllamaLLM

    sent = {}

    def fake_request(self, path, payload=None):
        sent.update(payload or {})
        return {"message": {"content": "{}"}, "prompt_eval_count": 1, "eval_count": 1}

    monkeypatch.setattr(OllamaLLM, "_request", fake_request)
    OllamaLLM("gpt-oss:20b").complete("sys", "hi")
    assert sent["options"] == {"temperature": 0.0, "seed": 42}
