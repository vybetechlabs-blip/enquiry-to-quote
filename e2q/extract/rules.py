"""RuleExtractor: deterministic extraction with regexes and keyword maps.

It exists so the test suite and the keyless demo are deterministic. On clean enquiries it should
read the job correctly; on messy ones it should say what it could not read (missing_fields, low
confidence) rather than guess.
"""

from __future__ import annotations

import re

from e2q.config import Business
from e2q.schema import Enquiry, RawEnquiry, Site

NUMBER = r"(\d{1,3}(?:,\d{3})+|\d+(?:\.\d+)?)"
UNIT_PATTERNS = {
    "sqft": r"sq\.?\s*ft\.?|sqft|square\s+f(?:ee|oo)t|ft2|ft²|sf\b",
    "sqm": r"sq\.?\s*m\b|sqm|square\s+met(?:re|er)s?|m2\b|m²",
}
AREA_RE = re.compile(
    NUMBER + r"\s*(" + "|".join(f"(?:{p})" for p in UNIT_PATTERNS.values()) + ")",
    re.IGNORECASE,
)
FREQUENCY_PATTERNS = {
    "daily": r"\bdaily\b|every\s+(?:week)?day|each\s+weekday|five\s+days\s+a\s+week",
    "weekly": r"\bweekly\b|every\s+week\b|once\s+a\s+week|each\s+week|per\s+week",
    "fortnightly": r"fortnight|every\s+(?:two|2|other)\s+weeks",
    "monthly": r"\bmonthly\b|every\s+month|once\s+a\s+month",
    "one_off": r"\bone[\s-]?off\b|\bone[\s-]time\b|just\s+once",
}
MULTI_SITE_CUE = re.compile(
    r"\b(two|three|four|both|each|sites|offices|locations|branch(?:es)?)\b", re.IGNORECASE
)
INJECTION_PATTERNS = {
    "ignore_instructions": (
        r"\bignore\b[^.\n]{0,40}\b(instructions|rate\s*card|rules|prompt|pricing)\b"
    ),
    "system_note": r"\bsystem\s+(note|prompt|message|override)\b",
    "role_reset": r"\byou\s+are\s+now\b|\bact\s+as\b",
    "dictated_price": r"\bquote\s+(?:us\s+)?\$\s*\d+(?:\.\d+)?\s+(?:for|on)\b",
}
VENDOR_MARKERS = (
    "seo",
    "unsubscribe",
    "rate sheet",
    "leads",
    "we help",
    "our agency",
    "marketing",
    "partnership opportunity",
    "reply yes",
    "reply stop",
    "search results",
)
QUOTED_HEADER = re.compile(
    r"^(on .+wrote:|-{2,}\s*original message\s*-{2,}|from:\s.+)$", re.IGNORECASE
)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")


def strip_quoted(body: str) -> str:
    """Keep only the newest message in a reply chain."""
    kept = []
    for line in body.splitlines():
        if QUOTED_HEADER.match(line.strip()):
            break
        if line.lstrip().startswith(">"):
            continue
        kept.append(line)
    return "\n".join(kept)


def normalize_unit(text: str | None) -> str | None:
    if not text:
        return None
    for unit, pattern in UNIT_PATTERNS.items():
        if re.fullmatch(pattern, text.strip(), re.IGNORECASE):
            return unit
    return None


def parse_number(text: str) -> float:
    return float(text.replace(",", ""))


class RuleExtractor:
    name = "RuleExtractor"

    def __init__(self, business: Business):
        self.business = business
        self.card = business.rate_card

    # --- field readers -------------------------------------------------------------------

    def _match_services(self, text: str) -> list[str]:
        low = text.lower()
        found = []
        for sid, words in self.business.profile.service_keywords.items():
            label = self.card.services[sid].label.lower()
            if any(w in low for w in [*words, label]):
                found.append(sid)
        return found

    def _match_frequencies(self, text: str) -> list[str]:
        return [f for f, p in FREQUENCY_PATTERNS.items() if re.search(p, text, re.IGNORECASE)]

    def _match_add_ons(self, text: str) -> list[str]:
        low = text.lower()
        found = []
        for aid, words in self.business.profile.add_on_keywords.items():
            label = self.card.add_ons[aid].label.lower()
            if any(w in low for w in [*words, label]):
                found.append(aid)
        return found

    def _match_out_of_scope(self, text: str) -> list[str]:
        low = text.lower()
        return [
            sid for sid, words in self.card.out_of_scope.items() if any(w in low for w in words)
        ]

    def _match_injection(self, text: str) -> list[str]:
        return [
            f"injection:{name}"
            for name, p in INJECTION_PATTERNS.items()
            if re.search(p, text, re.IGNORECASE)
        ]

    def _match_areas(self, text: str) -> list[Site]:
        sites = []
        for m in AREA_RE.finditer(text):
            sites.append(
                Site(
                    label=f"Site {len(sites) + 1}",
                    area=parse_number(m.group(1)),
                    area_unit=normalize_unit(m.group(2)),
                )
            )
        return sites

    @staticmethod
    def _is_vendor_pitch(text: str) -> bool:
        low = text.lower()
        return sum(marker in low for marker in VENDOR_MARKERS) >= 2

    # --- assembly -------------------------------------------------------------------------

    def extract(self, raw: RawEnquiry) -> Enquiry:
        enq = Enquiry(enquiry_id=raw.id, source=raw.source)
        conf = enq.confidence

        if raw.source == "webform":
            f = {k: (v or "").strip() for k, v in (raw.fields or {}).items()}
            free_text = f.get("message", "")
            enq.contact_name = f.get("name") or None
            enq.contact_email = f.get("email") or None
            enq.company = f.get("company") or None
            services = self._match_services(f.get("service", ""))
            freqs = self._match_frequencies(f.get("frequency", "")) or [
                k
                for k, v in self.card.frequencies.items()
                if f.get("frequency", "").lower() in (k, v.label.lower())
            ]
            sites = []
            if f.get("area"):
                try:
                    sites = [
                        Site(
                            label="Site 1",
                            area=parse_number(f["area"]),
                            area_unit=normalize_unit(f.get("area_unit")),
                        )
                    ]
                except ValueError:
                    enq.notes.append(f"area field not a number: {f['area']!r}")
            add_ons = self._match_add_ons(f.get("extras", "") + "\n" + free_text)
            scan_text = " ".join(f.values())
            base_conf = 0.95
        else:
            body = strip_quoted(raw.body or "")
            free_text = f"{raw.subject or ''}\n{body}"
            sender = raw.sender or ""
            addr = EMAIL_RE.search(sender)
            enq.contact_email = addr.group(0).lower() if addr else None
            name = sender.split("<")[0].strip().strip('"')
            enq.contact_name = name or None
            services = self._match_services(free_text)
            freqs = self._match_frequencies(free_text)
            sites = self._match_areas(free_text)
            add_ons = self._match_add_ons(free_text)
            scan_text = free_text
            base_conf = 0.85

        conf["contact_email"] = 0.95 if enq.contact_email else 0.0

        # Not an enquiry at all (vendor pitch, newsletter): stop reading fields.
        if self._is_vendor_pitch(scan_text) and not services:
            enq.is_enquiry = False
            enq.notes.append("reads as a vendor pitch, not a customer enquiry")
            conf["is_enquiry"] = 0.8
            enq.missing_fields = []
            return enq
        conf["is_enquiry"] = 0.9

        enq.needs_human = self._match_injection(scan_text)
        enq.out_of_scope = self._match_out_of_scope(scan_text)

        # Frequency.
        if len(freqs) == 1:
            enq.frequency = freqs[0]
            conf["frequency"] = base_conf
        elif len(freqs) > 1:
            enq.notes.append(f"conflicting frequencies: {', '.join(freqs)}")
            conf["frequency"] = 0.2
        else:
            conf["frequency"] = 0.0

        # Service.
        if len(services) == 1:
            enq.service = services[0]
            conf["service"] = base_conf
        elif len(services) > 1:
            enq.notes.append(f"ambiguous service: {' or '.join(services)}")
            conf["service"] = 0.2
        elif enq.frequency and enq.frequency != "one_off" and not enq.out_of_scope:
            # A recurring schedule with no named service reads as regular cleaning.
            enq.service = "regular_office"
            conf["service"] = 0.6
            enq.notes.append("service inferred as regular cleaning from a recurring frequency")
        else:
            conf["service"] = 0.0

        # A service sold at one frequency only needs no frequency from the customer.
        if enq.service and not enq.frequency:
            allowed = self.card.services[enq.service].frequencies
            if len(allowed) == 1 and not any("conflicting" in n for n in enq.notes):
                enq.frequency = allowed[0]
                conf["frequency"] = 0.7
                enq.notes.append(f"frequency defaulted to {allowed[0]} (only option for service)")

        # Sites and area.
        if len(sites) > 1 and not MULTI_SITE_CUE.search(free_text):
            enq.notes.append("several areas mentioned but no sign of several sites; kept the first")
            sites = sites[:1]
            conf["area"] = 0.5
        else:
            conf["area"] = base_conf if sites else 0.0
        enq.sites = sites
        enq.add_ons = add_ons
        if add_ons:
            conf["add_ons"] = base_conf

        missing = []
        if not enq.service:
            missing.append("service")
        if not enq.frequency:
            missing.append("frequency")
        if not enq.sites or any(s.area is None for s in enq.sites):
            missing.append("area")
        if not enq.contact_email:
            missing.append("contact_email")
        enq.missing_fields = missing
        return enq
