import pytest
from conftest import load_sample

from e2q.extract.rules import normalize_unit, strip_quoted
from e2q.schema import RawEnquiry


def email(body, sender="Pat <pat@example.com>", subject="Enquiry"):
    return RawEnquiry(id="x", source="email", sender=sender, subject=subject, body=body)


def test_strip_quoted_keeps_only_newest_message():
    body = "New text, 5,200 sq ft.\n\nOn Mon, someone wrote:\n> old text 2,600 sq ft"
    assert strip_quoted(body) == "New text, 5,200 sq ft.\n"


def test_strip_quoted_drops_inline_quote_lines():
    assert strip_quoted("keep\n> drop\n>> drop too\nkeep 2") == "keep\nkeep 2"


@pytest.mark.parametrize(
    ("text", "unit"),
    [
        ("sq ft", "sqft"),
        ("sqft", "sqft"),
        ("square feet", "sqft"),
        ("sqm", "sqm"),
        ("m2", "sqm"),
        ("square metres", "sqm"),
        ("", None),
        ("acres", None),
    ],
)
def test_normalize_unit(text, unit):
    assert normalize_unit(text) == unit


def test_reply_chain_uses_new_area_not_quoted_one(extractor):
    e = extractor.extract(load_sample("s13-reply-chain"))
    assert [(s.area, s.area_unit) for s in e.sites] == [(5200, "sqft")]


def test_two_services_named_is_ambiguous(extractor):
    e = extractor.extract(load_sample("s09-ambiguous-service"))
    assert e.service is None
    assert "service" in e.missing_fields
    assert e.confidence["service"] < 0.5
    assert any("ambiguous service" in n for n in e.notes)


def test_injection_is_flagged_but_fields_still_read(extractor):
    e = extractor.extract(load_sample("s14-prompt-injection"))
    assert {r.split(":")[0] for r in e.needs_human} == {"injection"}
    assert e.service == "regular_office" and e.frequency == "weekly"


def test_vendor_pitch_is_not_an_enquiry(extractor):
    e = extractor.extract(load_sample("s15-vendor-spam"))
    assert e.is_enquiry is False
    assert e.service is None and e.sites == []


def test_webform_fields_map_directly(extractor):
    e = extractor.extract(load_sample("s02-complete-webform"))
    assert e.service == "regular_office"
    assert e.frequency == "fortnightly"
    assert [(s.area, s.area_unit) for s in e.sites] == [(2000, "sqft")]
    assert e.add_ons == ["kitchen_appliances"]
    assert e.confidence["service"] >= 0.9


def test_empty_webform_fields_are_missing(extractor):
    e = extractor.extract(load_sample("s16-webform-incomplete"))
    assert e.missing_fields == ["frequency", "area"]


def test_single_frequency_service_defaults_with_lower_confidence(extractor):
    e = extractor.extract(load_sample("s03-deep-clean"))
    assert e.frequency == "one_off"
    assert e.confidence["frequency"] < 0.85


def test_recurring_schedule_without_service_reads_as_regular(extractor):
    e = extractor.extract(load_sample("s17-daily-supplies"))
    assert e.service == "regular_office"
    assert e.confidence["service"] == 0.6


def test_two_areas_without_multi_site_cue_keeps_first(extractor):
    e = extractor.extract(
        email("Regular office cleaning, weekly. It is 2,000 sq ft, maybe 2,100 sq ft.")
    )
    assert [s.area for s in e.sites] == [2000]
    assert e.confidence["area"] == 0.5


def test_conflicting_frequencies_are_not_guessed(extractor):
    e = extractor.extract(email("Regular office cleaning for 2,000 sq ft, weekly or monthly."))
    assert e.frequency is None
    assert "frequency" in e.missing_fields


def test_missing_sender_address_is_missing(extractor):
    e = extractor.extract(email("Regular office cleaning, weekly, 2,000 sq ft.", sender="Pat"))
    assert e.contact_email is None
    assert "contact_email" in e.missing_fields
