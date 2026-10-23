"""LLMExtractor: structured extraction through the provider factory.

Phase 0 ships the interface only. Phase 1 wires the prompt and structured output into `Enquiry`,
measured on the same golden set as RuleExtractor. Pricing never reads anything a model wrote
except the extracted fields, and the rate card still sets every number.
"""

from __future__ import annotations

from e2q.config import Business
from e2q.providers import LLMProvider
from e2q.schema import Enquiry, RawEnquiry


class LLMExtractor:
    name = "LLMExtractor"

    def __init__(self, business: Business, provider: LLMProvider):
        self.business = business
        self.provider = provider

    def extract(self, raw: RawEnquiry) -> Enquiry:
        raise NotImplementedError("LLM extraction is Phase 1 and is not wired yet.")
