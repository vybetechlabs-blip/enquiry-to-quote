"""GuardedExtractor: an LLM extraction cross-checked against RuleExtractor (`--guard`).

When the model reads the message as a customer inquiry, RuleExtractor reads it too. If the two
disagree on any field a quote needs (service, frequency, site areas, reply address), the inquiry
goes to a person with the reason `extractors_disagree:<fields>`. Agreement changes nothing.
"""

from __future__ import annotations

from e2q.extract.llm import LLMExtractor
from e2q.extract.rules import RuleExtractor
from e2q.schema import Enquiry, RawEnquiry


def _areas(enquiry: Enquiry) -> list[tuple[float, str | None]]:
    return [(float(s.area), s.area_unit) for s in enquiry.sites if s.area is not None]


def disagreements(llm: Enquiry, rules: Enquiry) -> list[str]:
    fields = []
    if llm.service != rules.service:
        fields.append("service")
    if llm.frequency != rules.frequency:
        fields.append("frequency")
    if _areas(llm) != _areas(rules):
        fields.append("area")
    if (llm.contact_email or "").lower() != (rules.contact_email or "").lower():
        fields.append("contact_email")
    return fields


class GuardedExtractor:
    name = "GuardedExtractor"

    def __init__(self, llm: LLMExtractor, rules: RuleExtractor):
        self.llm = llm
        self.rules = rules

    @property
    def calls(self):
        return self.llm.calls

    @property
    def system_prompt(self) -> str:
        return self.llm.system_prompt

    @property
    def row_name(self) -> str:
        return f"{self.llm.row_name}+guard"

    def extract(self, raw: RawEnquiry) -> Enquiry:
        enquiry = self.llm.extract(raw)
        if not enquiry.is_enquiry or any(
            r.startswith("extraction_failed") for r in enquiry.needs_human
        ):
            return enquiry
        differ = disagreements(enquiry, self.rules.extract(raw))
        if differ:
            enquiry.needs_human.append(f"extractors_disagree:{','.join(differ)}")
        return enquiry
