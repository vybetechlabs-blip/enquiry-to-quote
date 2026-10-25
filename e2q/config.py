"""Load the business profile and rate card from `business/`."""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Literal

from pydantic import BaseModel
from smb_agent_kit.config import load_yaml, require_fictional

from e2q.schema import AreaUnit

DEFAULT_BUSINESS_DIR = Path(__file__).resolve().parent.parent / "business"


class ServiceRule(BaseModel):
    label: str
    rule_id: str
    rate_per_area: Decimal
    frequencies: list[str]


class FrequencyRule(BaseModel):
    rule_id: str
    multiplier: Decimal
    visits_per_month: int
    label: str


class MinimumCharge(BaseModel):
    rule_id: str
    amount: Decimal


class AddOnRule(BaseModel):
    label: str
    rule_id: str
    kind: Literal["flat", "per_area"]
    amount: Decimal


class MultiSiteRule(BaseModel):
    rule_id: str
    min_sites: int
    discount: Decimal


class SanityBand(BaseModel):
    rule_id: str
    min_area_per_site: float
    max_area_per_site: float
    max_monthly_total: Decimal


class RateCard(BaseModel):
    area_unit: AreaUnit
    currency_symbol: str
    quote_valid_days: int
    services: dict[str, ServiceRule]
    frequencies: dict[str, FrequencyRule]
    minimum_charge: MinimumCharge
    add_ons: dict[str, AddOnRule]
    multi_site: MultiSiteRule
    sanity_band: SanityBand
    out_of_scope: dict[str, list[str]]


class FaqItem(BaseModel):
    q: str
    a: str


class BusinessProfile(BaseModel):
    name: str
    fictional: bool
    reply_from: str
    signoff: str
    service_keywords: dict[str, list[str]]
    add_on_keywords: dict[str, list[str]]
    faq: list[FaqItem] = []


class Business(BaseModel):
    profile: BusinessProfile
    rate_card: RateCard
    templates_dir: Path


def load_business(business_dir: Path | None = None) -> Business:
    root = Path(business_dir) if business_dir else DEFAULT_BUSINESS_DIR
    profile = require_fictional(load_yaml(root / "business.yaml"), root / "business.yaml")
    card = load_yaml(root / "pricing.yaml")
    return Business(
        profile=BusinessProfile.model_validate(profile),
        rate_card=RateCard.model_validate(card),
        templates_dir=root / "templates",
    )
