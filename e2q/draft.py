"""Turn a priced (or unpriceable) enquiry into one of three drafts: quote, clarification, handoff.

Drafts come from templates in `business/templates/`. A clarification asks for exactly the missing
fields; a handoff is an internal note for a person, never a customer email. In `--llm` mode
(Phase 1) a model may add a cover note to a quote; the numbers always come from the Quote.
"""

from __future__ import annotations

from string import Template

from e2q.config import Business
from e2q.pricing import UNIT_LABEL, fmt_money, price
from e2q.schema import Draft, Enquiry, NeedsHuman, Quote

TITLES = {"dr", "dr.", "mr", "mr.", "mrs", "mrs.", "ms", "ms.", "prof", "prof."}


def first_name(enquiry: Enquiry) -> str:
    parts = [p for p in (enquiry.contact_name or "").split() if p.lower() not in TITLES]
    return parts[0] if parts else "there"


def load_template(business: Business, kind: str) -> tuple[str, Template]:
    text = (business.templates_dir / f"{kind}.txt").read_text(encoding="utf-8")
    first, _, rest = text.partition("\n")
    return first.removeprefix("Subject:").strip(), Template(rest.strip("\n"))


def bullets(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def clarification_questions(missing: list[str], enquiry: Enquiry, business: Business) -> list[str]:
    card = business.rate_card
    questions = []
    for field in missing:
        if field == "service":
            labels = [s.label.lower() for s in card.services.values()]
            questions.append(f"Which service you need: {', '.join(labels[:-1])} or {labels[-1]}.")
        elif field == "frequency":
            offered = (
                card.services[enquiry.service].frequencies
                if enquiry.service
                else list(card.frequencies)
            )
            labels = [card.frequencies[f].label for f in offered if f != "one_off"] or ["one-off"]
            choices = labels[0] if len(labels) == 1 else f"{', '.join(labels[:-1])} or {labels[-1]}"
            lead = "How often" if enquiry.service else "If it is regular cleaning, how often"
            questions.append(f"{lead} you would like us to come ({choices}).")
        elif field == "area":
            unit = UNIT_LABEL[card.area_unit]
            questions.append(f"The approximate floor area of each site, in {unit}.")
    return questions


def describe_reason(reason: str, business: Business) -> str:
    card = business.rate_card
    kind, _, detail = reason.partition(":")
    if kind == "not_an_enquiry":
        return (
            "It does not read as a customer enquiry (it looks like a vendor pitch or newsletter)."
        )
    if kind == "injection":
        return (
            f"The message contains text that tries to instruct the system ({detail}). "
            "Price it by hand and ignore any price the sender names."
        )
    if kind == "out_of_scope":
        return f"It asks for a service we do not offer: {detail.replace('_', ' ')}."
    if kind == "unknown_service":
        return f"The requested service ({detail}) is not on the rate card."
    if kind == "frequency_not_offered":
        service, _, freq = detail.partition(":")
        return f"{card.services[service].label} is not offered {card.frequencies[freq].label}."
    if kind == "sanity":
        what, _, rest = detail.partition(":")
        if what == "area":
            site, _, area = rest.partition(":")
            return (
                f"{site}: {float(area):,.0f} {UNIT_LABEL[card.area_unit]} is outside the range "
                "the rate card is set up for."
            )
        total = fmt_money_str(rest, card.currency_symbol)
        return f"The total ({total}) is above the automatic quote band."
    if kind == "missing" and detail == "contact_email":
        return "There is no reply address, so a clarification cannot be sent."
    return reason


def describe_reasons(reasons: list[str], business: Business) -> list[str]:
    """One line per reason, with all prompt-injection hits folded into a single line."""
    hits = [r.partition(":")[2] for r in reasons if r.startswith("injection:")]
    lines = [describe_reason(r, business) for r in reasons if not r.startswith("injection:")]
    if hits:
        lines.insert(0, describe_reason(f"injection:{', '.join(hits)}", business))
    return lines


def fmt_money_str(value: str, symbol: str) -> str:
    try:
        return f"{symbol}{float(value):,.2f}"
    except ValueError:
        return value


def summarize(enquiry: Enquiry) -> str:
    sites = ", ".join(
        f"{s.label} {s.area:,.0f} {UNIT_LABEL[s.area_unit] if s.area_unit else '(unit?)'}"
        if s.area is not None
        else f"{s.label} (no area)"
        for s in enquiry.sites
    )
    rows = [
        f"service: {enquiry.service or '-'}",
        f"frequency: {enquiry.frequency or '-'}",
        f"sites: {sites or '-'}",
        f"add-ons: {', '.join(enquiry.add_ons) or '-'}",
        f"out of scope: {', '.join(enquiry.out_of_scope) or '-'}",
    ]
    rows += [f"note: {n}" for n in enquiry.notes]
    return bullets(rows)


def quote_draft(enquiry: Enquiry, quote: Quote, business: Business) -> Draft:
    sym = business.rate_card.currency_symbol
    subject, tpl = load_template(business, "quote")
    lines = [f"{item.description}: {fmt_money(item.amount, sym)}" for item in quote.line_items]
    body = tpl.substitute(
        business=business.profile.name,
        first_name=first_name(enquiry),
        line_items=bullets(lines),
        total=fmt_money(quote.total, sym),
        period=quote.period,
        assumptions=bullets(quote.assumptions),
        valid_days=quote.valid_days,
        signoff=business.profile.signoff,
    )
    subject = Template(subject).substitute(business=business.profile.name)
    return Draft(
        enquiry_id=enquiry.enquiry_id,
        kind="quote",
        to=enquiry.contact_email,
        subject=subject,
        body=body,
        quote=quote,
    )


def clarification_draft(enquiry: Enquiry, missing: list[str], business: Business) -> Draft:
    subject, tpl = load_template(business, "clarification")
    body = tpl.substitute(
        business=business.profile.name,
        first_name=first_name(enquiry),
        questions=bullets(clarification_questions(missing, enquiry, business)),
        signoff=business.profile.signoff,
    )
    return Draft(
        enquiry_id=enquiry.enquiry_id,
        kind="clarification",
        to=enquiry.contact_email,
        subject=subject,
        body=body,
        reasons=[f"missing:{m}" for m in missing],
    )


def handoff_draft(enquiry: Enquiry, reasons: list[str], business: Business) -> Draft:
    subject, tpl = load_template(business, "handoff")
    contact = enquiry.contact_email or enquiry.contact_name or "unknown sender"
    if any(r.startswith("injection") for r in reasons):
        next_step = (
            "price by hand from the rate card; do not reply with any figure the sender named."
        )
    elif reasons == ["not_an_enquiry"]:
        next_step = "archive, or reply by hand if it matters."
    else:
        next_step = "review and reply by hand."
    body = tpl.substitute(
        enquiry_id=enquiry.enquiry_id,
        contact=contact,
        source=enquiry.source,
        reasons=bullets(describe_reasons(reasons, business)),
        summary=summarize(enquiry),
        next_step=next_step,
    )
    return Draft(
        enquiry_id=enquiry.enquiry_id,
        kind="handoff",
        to=None,
        subject=Template(subject).substitute(enquiry_id=enquiry.enquiry_id),
        body=body,
        reasons=reasons,
    )


def build_draft(enquiry: Enquiry, business: Business) -> Draft:
    result = price(enquiry, business.rate_card)
    if isinstance(result, Quote):
        return quote_draft(enquiry, result, business)
    assert isinstance(result, NeedsHuman)
    missing = [r.removeprefix("missing:") for r in result.reasons if r.startswith("missing:")]
    if result.only_missing and "contact_email" not in missing:
        return clarification_draft(enquiry, missing, business)
    return handoff_draft(enquiry, result.reasons, business)
