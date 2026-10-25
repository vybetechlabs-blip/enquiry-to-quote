"""LLM cover note for a quote draft (LLM mode only).

The note replaces the template's opening line. It is checked before use: a note that states
any number not already in the Quote, or any price, is dropped and the template line is kept
(see `draft.cover_note_is_safe`).
"""

from __future__ import annotations

from e2q.config import Business
from e2q.draft import CoverWriter
from e2q.providers import LLMProvider
from e2q.schema import Enquiry, Quote

SYSTEM = """You write the opening of a reply from {name}, a commercial cleaning company, to a \
customer who asked for a quote. Write one or two plain, friendly sentences that thank them and \
show you understood the job in everyday words. Do not state any price, number, date, \
discount or promise; the quote below your sentences carries the figures. No greeting, no \
sign-off, no lists. Reply with the sentences only."""


def make_cover_writer(provider: LLMProvider, business: Business) -> CoverWriter:
    system = SYSTEM.format(name=business.profile.name)

    def write(enquiry: Enquiry, quote: Quote) -> str | None:
        card = business.rate_card
        service = card.services[enquiry.service].label if enquiry.service else "cleaning"
        freq = card.frequencies[enquiry.frequency].label if enquiry.frequency else ""
        sites = len(enquiry.sites)
        prompt = (
            f"Customer first name: {enquiry.contact_name or 'unknown'}\n"
            f"Job: {service}, {freq}, {sites} site(s)."
        )
        return provider.complete(system, prompt).text

    return write
