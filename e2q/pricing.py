"""Deterministic pricing: Enquiry + rate card -> Quote or NeedsHuman.

A pure function over the YAML rate card. No model is involved anywhere in this path, and every
number in a Quote can be traced to the rule ids it carries.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

from e2q.config import RateCard
from e2q.schema import Enquiry, LineItem, NeedsHuman, Quote

CENT = Decimal("0.01")
SQFT_PER_SQM = Decimal("10.7639")
UNIT_LABEL = {"sqft": "sq ft", "sqm": "sq m"}


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def fmt_money(value: Decimal, symbol: str) -> str:
    sign = "-" if value < 0 else ""
    return f"{sign}{symbol}{abs(value):,.2f}"


def fmt_area(area: Decimal, unit: str) -> str:
    return f"{area:,.0f} {UNIT_LABEL[unit]}"


def convert_area(area: float, from_unit: str, to_unit: str) -> Decimal:
    value = Decimal(str(area))
    if from_unit == to_unit:
        return value
    value = value * SQFT_PER_SQM if to_unit == "sqft" else value / SQFT_PER_SQM
    return value.quantize(Decimal("1"), rounding=ROUND_HALF_UP)


def missing_reasons(enquiry: Enquiry) -> list[str]:
    reasons = []
    if not enquiry.service:
        reasons.append("missing:service")
    if not enquiry.frequency:
        reasons.append("missing:frequency")
    if not enquiry.sites or any(s.area is None for s in enquiry.sites):
        reasons.append("missing:area")
    if not enquiry.contact_email:
        reasons.append("missing:contact_email")
    return reasons


def price(enquiry: Enquiry, card: RateCard) -> Quote | NeedsHuman:
    eid = enquiry.enquiry_id
    if not enquiry.is_enquiry:
        return NeedsHuman(enquiry_id=eid, reasons=["not_an_enquiry"])

    reasons = list(enquiry.needs_human)
    reasons += [f"out_of_scope:{s}" for s in enquiry.out_of_scope]
    if enquiry.service and enquiry.service not in card.services:
        reasons.append(f"unknown_service:{enquiry.service}")
    if reasons:
        return NeedsHuman(enquiry_id=eid, reasons=reasons)

    missing = missing_reasons(enquiry)
    if missing:
        return NeedsHuman(enquiry_id=eid, reasons=missing)

    service = card.services[enquiry.service]
    if enquiry.frequency not in service.frequencies:
        return NeedsHuman(
            enquiry_id=eid,
            reasons=[f"frequency_not_offered:{enquiry.service}:{enquiry.frequency}"],
        )
    freq = card.frequencies[enquiry.frequency]
    unit = card.area_unit
    sym = card.currency_symbol
    band = card.sanity_band

    rule_ids = [service.rule_id, freq.rule_id]
    assumptions: list[str] = []
    lines: list[LineItem] = []
    visits = freq.visits_per_month

    for site in enquiry.sites:
        area = convert_area(site.area, site.area_unit or unit, unit)
        if site.area_unit is None:
            assumptions.append(f"{site.label}: area read as {UNIT_LABEL[unit]}.")
        elif site.area_unit != unit:
            assumptions.append(
                f"{site.label}: {site.area:,.0f} {UNIT_LABEL[site.area_unit]} converted to "
                f"{fmt_area(area, unit)}."
            )
        if not band.min_area_per_site <= float(area) <= band.max_area_per_site:
            reasons.append(f"sanity:area:{site.label}:{area}")
            continue

        base = money(area * service.rate_per_area * freq.multiplier)
        visit_total = base
        site_lines = [
            LineItem(
                description=f"{service.label}, {site.label} ({fmt_area(area, unit)}), {freq.label}",
                rule_ids=[service.rule_id, freq.rule_id],
                amount=base,
            )
        ]
        for add_id in enquiry.add_ons:
            add = card.add_ons[add_id]
            amount = money(add.amount * area if add.kind == "per_area" else add.amount)
            visit_total += amount
            site_lines.append(
                LineItem(
                    description=f"{add.label}, {site.label}",
                    rule_ids=[add.rule_id],
                    amount=amount,
                )
            )
            if add.rule_id not in rule_ids:
                rule_ids.append(add.rule_id)
        minimum = card.minimum_charge
        if visit_total < minimum.amount:
            site_lines.append(
                LineItem(
                    description=f"Minimum visit charge top-up, {site.label}",
                    rule_ids=[minimum.rule_id],
                    amount=minimum.amount - visit_total,
                )
            )
            assumptions.append(
                f"{site.label}: the minimum charge of {fmt_money(minimum.amount, sym)} "
                "per visit applies."
            )
            if minimum.rule_id not in rule_ids:
                rule_ids.append(minimum.rule_id)
        for line in site_lines:
            line.amount = money(line.amount * visits)
        lines += site_lines

    if reasons:
        return NeedsHuman(enquiry_id=eid, reasons=reasons)

    total = sum((line.amount for line in lines), Decimal("0"))
    multi = card.multi_site
    if len(enquiry.sites) >= multi.min_sites:
        discount = money(total * multi.discount)
        lines.append(
            LineItem(
                description=f"Multi-site discount ({multi.discount * 100:.0f}%)",
                rule_ids=[multi.rule_id],
                amount=-discount,
            )
        )
        total -= discount
        rule_ids.append(multi.rule_id)

    if total > band.max_monthly_total:
        return NeedsHuman(enquiry_id=eid, reasons=[f"sanity:total:{total}"])

    one_off = enquiry.frequency == "one_off"
    if not one_off:
        assumptions.append(f"Monthly figures assume {visits} visits a month ({freq.label}).")
    assumptions.append("Areas are as stated in the enquiry; a site visit may adjust the price.")
    assumptions.append("Cleaning products and equipment are included.")
    return Quote(
        enquiry_id=eid,
        line_items=lines,
        total=total,
        period="one-off" if one_off else "per month",
        assumptions=assumptions,
        rule_ids=rule_ids,
        valid_days=card.quote_valid_days,
    )
