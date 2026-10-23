import json
from pathlib import Path

import pytest

from e2q.config import load_business
from e2q.extract import RuleExtractor
from e2q.queue import ApprovalQueue
from e2q.schema import Enquiry, RawEnquiry, Site

ROOT = Path(__file__).resolve().parent.parent
SAMPLES = ROOT / "inbox" / "samples"


@pytest.fixture(scope="session")
def business():
    return load_business()


@pytest.fixture(scope="session")
def card(business):
    return business.rate_card


@pytest.fixture
def extractor(business):
    return RuleExtractor(business)


@pytest.fixture
def queue(tmp_path):
    q = ApprovalQueue(tmp_path / "queue.db")
    yield q
    q.close()


def load_sample(sample_id: str) -> RawEnquiry:
    return RawEnquiry.model_validate(json.loads((SAMPLES / f"{sample_id}.json").read_text("utf-8")))


def make_enquiry(**overrides) -> Enquiry:
    """A complete, quotable enquiry: regular weekly cleaning of one 4,500 sq ft site."""
    data = {
        "enquiry_id": "t1",
        "source": "email",
        "contact_email": "someone@example.com",
        "contact_name": "Pat Example",
        "service": "regular_office",
        "frequency": "weekly",
        "sites": [Site(label="Site 1", area=4500, area_unit="sqft")],
    }
    data.update(overrides)
    return Enquiry(**data)
