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


# v2 (owner instruction 2026-10-25): the greeting already carries the first name, so the note
# must not repeat it. The name is no longer sent to the model at all.
SYSTEM_V2 = (
    SYSTEM
    + """ Do not use the customer's name; the greeting above your sentences \
already has it."""
)


def make_cover_writer(
    provider: LLMProvider, business: Business, version: str = "v1"
) -> CoverWriter:
    system = (SYSTEM_V2 if version == "v2" else SYSTEM).format(name=business.profile.name)

    def write(enquiry: Enquiry, quote: Quote) -> str | None:
        card = business.rate_card
        service = card.services[enquiry.service].label if enquiry.service else "cleaning"
        freq = card.frequencies[enquiry.frequency].label if enquiry.frequency else ""
        sites = len(enquiry.sites)
        job = f"Job: {service}, {freq}, {sites} site(s)."
        if version == "v2":
            prompt = job
        else:
            prompt = f"Customer first name: {enquiry.contact_name or 'unknown'}\n{job}"
        return provider.complete(system, prompt).text

    return write
