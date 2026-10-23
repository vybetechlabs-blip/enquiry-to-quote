"""Typed records that move through the pipeline: raw enquiry, extraction, quote, draft."""

from __future__ import annotations

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

Frequency = Literal["daily", "weekly", "fortnightly", "monthly", "one_off"]
AreaUnit = Literal["sqft", "sqm"]
DraftKind = Literal["quote", "clarification", "handoff"]
DraftState = Literal["drafted", "approved", "edited", "rejected", "sent"]

# Fields a quote cannot be priced without. Clarification emails ask for exactly these.
REQUIRED_FIELDS = ("service", "frequency", "area", "contact_email")


class RawEnquiry(BaseModel):
    """What arrives: an email or a web-form submission, before any interpretation."""

    id: str
    source: Literal["email", "webform"]
    received_at: str | None = None
    sender: str | None = Field(default=None, alias="from")
    subject: str | None = None
    body: str | None = None
    fields: dict[str, str] | None = None

    model_config = {"populate_by_name": True, "extra": "ignore"}


class Site(BaseModel):
    label: str
    area: float | None = None
    area_unit: AreaUnit | None = None


class Enquiry(BaseModel):
    """The job as the extractor understood it. Nothing here is a price."""

    enquiry_id: str
    source: Literal["email", "webform"]
    is_enquiry: bool = True
    contact_name: str | None = None
    contact_email: str | None = None
    company: str | None = None
    service: str | None = None
    frequency: Frequency | None = None
    sites: list[Site] = Field(default_factory=list)
    add_ons: list[str] = Field(default_factory=list)
    out_of_scope: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)
    needs_human: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


class LineItem(BaseModel):
    description: str
    rule_ids: list[str]
    amount: Decimal


class Quote(BaseModel):
    enquiry_id: str
    line_items: list[LineItem]
    total: Decimal
    period: Literal["per month", "one-off"]
    assumptions: list[str]
    rule_ids: list[str]
    valid_days: int


class NeedsHuman(BaseModel):
    """Pricing declined to produce a number. Reasons are machine-readable `kind:detail` strings."""

    enquiry_id: str
    reasons: list[str]

    @property
    def only_missing(self) -> bool:
        return bool(self.reasons) and all(r.startswith("missing:") for r in self.reasons)


class Draft(BaseModel):
    enquiry_id: str
    kind: DraftKind
    to: str | None
    subject: str
    body: str
    quote: Quote | None = None
    reasons: list[str] = Field(default_factory=list)
