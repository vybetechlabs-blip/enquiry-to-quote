"""The interface every extractor implements."""

from __future__ import annotations

from typing import Protocol

from e2q.schema import Enquiry, RawEnquiry


class Extractor(Protocol):
    name: str

    def extract(self, raw: RawEnquiry) -> Enquiry: ...
