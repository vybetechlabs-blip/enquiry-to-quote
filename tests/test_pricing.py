from decimal import Decimal

import pytest
from conftest import make_enquiry

from e2q.pricing import convert_area, price
from e2q.schema import NeedsHuman, Quote, Site


def quote_of(enquiry, card) -> Quote:
    result = price(enquiry, card)
    assert isinstance(result, Quote), result
    return result


def test_base_rate_times_frequency_times_visits(card):
    q = quote_of(make_enquiry(), card)
    # 4500 x 0.07 x 0.95 = 299.25 a visit, 4 visits a month
    assert q.total == Decimal("1197.00")
    assert q.period == "per month"
    assert q.rule_ids == ["SVC-REGULAR", "FREQ-WEEKLY"]


@pytest.mark.parametrize(
    ("freq", "expected"),
    [
        ("daily", "5355.00"),  # 4500 x 0.07 x 0.85 = 267.75 x 20
        ("weekly", "1197.00"),  # x 0.95 = 299.25 x 4
        ("fortnightly", "630.00"),  # x 1.00 = 315.00 x 2
        ("monthly", "346.50"),  # x 1.10 = 346.50 x 1
    ],
)
def test_frequency_multipliers(card, freq, expected):
    q = quote_of(make_enquiry(frequency=freq), card)
    assert q.total == Decimal(expected)
    assert card.frequencies[freq].rule_id in q.rule_ids


@pytest.mark.parametrize(("service", "rate"), [("deep_clean", "0.22"), ("carpet_cleaning", "0.30")])
def test_one_off_services(card, service, rate):
    q = quote_of(make_enquiry(service=service, frequency="one_off"), card)
    assert q.total == Decimal("4500") * Decimal(rate)
    assert q.period == "one-off"
    assert card.services[service].rule_id in q.rule_ids


def test_minimum_charge_tops_up_each_visit(card):
    q = quote_of(make_enquiry(sites=[Site(label="Site 1", area=600, area_unit="sqft")]), card)
    # 600 x 0.07 x 0.95 = 39.90, topped up to 120.00, x 4
    assert q.total == Decimal("480.00")
    top_up = [li for li in q.line_items if li.rule_ids == ["MIN-VISIT"]]
    assert top_up and top_up[0].amount == Decimal("320.40")
    assert "MIN-VISIT" in q.rule_ids


def test_minimum_counts_add_ons_before_topping_up(card):
    # 1200 x 0.07 x 1.00 = 84.00 + 35.00 kitchen = 119.00 -> top-up 1.00 a visit, 2 visits
    e = make_enquiry(
        frequency="fortnightly",
        sites=[Site(label="Site 1", area=1200, area_unit="sqft")],
        add_ons=["kitchen_appliances"],
    )
    q = quote_of(e, card)
    assert q.total == Decimal("240.00")


def test_flat_and_per_area_add_ons(card):
    e = make_enquiry(add_ons=["washroom_supplies", "interior_windows"])
    q = quote_of(e, card)
    # base 299.25 + supplies 20.00 + windows 4500 x 0.04 = 180.00 -> 499.25 x 4
    assert q.total == Decimal("1997.00")
    assert {"ADD-SUPPLIES", "ADD-WINDOWS"} <= set(q.rule_ids)


def test_multi_site_prices_each_site_then_discounts(card):
    e = make_enquiry(
        sites=[
            Site(label="Site 1", area=3000, area_unit="sqft"),
            Site(label="Site 2", area=1500, area_unit="sqft"),
        ]
    )
    q = quote_of(e, card)
    assert q.total == Decimal("1214.10")
    discount = q.line_items[-1]
    assert discount.rule_ids == ["MULTI-SITE"] and discount.amount == Decimal("-63.90")


def test_single_site_gets_no_multi_site_discount(card):
    assert "MULTI-SITE" not in quote_of(make_enquiry(), card).rule_ids


def test_square_metres_are_converted_and_stated(card):
    e = make_enquiry(sites=[Site(label="Site 1", area=400, area_unit="sqm")])
    q = quote_of(e, card)
    assert q.total == Decimal("1145.40")
    assert any("converted to 4,306 sq ft" in a for a in q.assumptions)


def test_area_without_unit_is_read_in_rate_card_unit(card):
    q = quote_of(make_enquiry(sites=[Site(label="Site 1", area=4500)]), card)
    assert q.total == Decimal("1197.00")
    assert any("area read as sq ft" in a for a in q.assumptions)


def test_convert_area_round_trip_units():
    assert convert_area(100, "sqm", "sqft") == Decimal("1076")
    assert convert_area(1076, "sqft", "sqm") == Decimal("100")
    assert convert_area(500, "sqft", "sqft") == Decimal("500")


@pytest.mark.parametrize("area", [100, 900_000])
def test_sanity_band_on_site_area(card, area):
    result = price(make_enquiry(sites=[Site(label="Site 1", area=area, area_unit="sqft")]), card)
    assert isinstance(result, NeedsHuman)
    assert result.reasons[0].startswith("sanity:area:Site 1")


def test_sanity_band_edges_are_inclusive(card):
    for area in (150, 60_000):
        e = make_enquiry(
            frequency="monthly", sites=[Site(label="Site 1", area=area, area_unit="sqft")]
        )
        assert isinstance(price(e, card), Quote)


def test_sanity_band_on_monthly_total(card):
    # 50,000 sq ft daily: 50000 x 0.07 x 0.85 = 2975.00 x 20 = 59,500 > 30,000
    e = make_enquiry(frequency="daily", sites=[Site(label="Site 1", area=50_000, area_unit="sqft")])
    result = price(e, card)
    assert isinstance(result, NeedsHuman)
    assert result.reasons == ["sanity:total:59500.00"]


def test_out_of_scope_goes_to_a_person(card):
    result = price(make_enquiry(out_of_scope=["pressure_washing"]), card)
    assert isinstance(result, NeedsHuman)
    assert result.reasons == ["out_of_scope:pressure_washing"]


def test_missing_fields_are_listed(card):
    e = make_enquiry(service=None, frequency=None, sites=[], contact_email=None)
    result = price(e, card)
    assert result.reasons == [
        "missing:service",
        "missing:frequency",
        "missing:area",
        "missing:contact_email",
    ]
    assert result.only_missing


def test_site_without_area_counts_as_missing(card):
    e = make_enquiry(sites=[Site(label="Site 1", area=None)])
    assert price(e, card).reasons == ["missing:area"]


def test_not_an_enquiry(card):
    assert price(make_enquiry(is_enquiry=False), card).reasons == ["not_an_enquiry"]


def test_injection_flag_blocks_pricing(card):
    result = price(make_enquiry(needs_human=["injection:dictated_price"]), card)
    assert isinstance(result, NeedsHuman)
    assert result.reasons == ["injection:dictated_price"]


def test_frequency_not_offered_for_service(card):
    result = price(make_enquiry(service="deep_clean", frequency="weekly"), card)
    assert result.reasons == ["frequency_not_offered:deep_clean:weekly"]


def test_unknown_service(card):
    assert price(make_enquiry(service="gutter_cleaning"), card).reasons == [
        "unknown_service:gutter_cleaning"
    ]


def test_every_line_item_traces_to_a_rule_on_the_quote(card):
    e = make_enquiry(
        add_ons=["kitchen_appliances"],
        sites=[
            Site(label="Site 1", area=600, area_unit="sqft"),
            Site(label="Site 2", area=2000, area_unit="sqft"),
        ],
    )
    q = quote_of(e, card)
    for item in q.line_items:
        assert set(item.rule_ids) <= set(q.rule_ids)
    assert sum(li.amount for li in q.line_items) == q.total


def test_pricing_is_pure(card):
    e = make_enquiry(add_ons=["interior_windows"])
    before = e.model_dump()
    first, second = price(e, card), price(e, card)
    assert first == second
    assert e.model_dump() == before
