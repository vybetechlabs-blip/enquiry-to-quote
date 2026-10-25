"""Approval queue, from smb-agent-kit, set up for inquiries.

States: drafted -> (approved | edited | rejected) -> sent. A handoff draft is an internal note
and is never sent. The send log is keyed by inquiry id + draft version, and a second send of a
logged key is refused with an error, never skipped silently.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from smb_agent_kit import approval
from smb_agent_kit.approval import (
    ALLOWED,
    SENDABLE_STATES,
    AlreadyIngested,
    AlreadySent,
    InvalidTransition,
    NotFound,
    NotSendable,
    QueueError,
)

from e2q.schema import Draft, Enquiry, RawEnquiry

__all__ = [
    "ALLOWED",
    "SENDABLE_STATES",
    "AlreadyIngested",
    "AlreadySent",
    "ApprovalQueue",
    "InvalidTransition",
    "NotFound",
    "NotSendable",
    "QueueError",
]


@dataclass
class _QueuedDraft:
    """A project draft as the kit queue stores it; the quote travels as the payload."""

    kind: str
    to: str | None
    subject: str
    body: str
    reasons: list[str]
    payload_json: str | None


class ApprovalQueue(approval.ApprovalQueue):
    noun: ClassVar[str] = "enquiry"
    not_sendable: ClassVar[dict[str, str]] = {
        "handoff": "a handoff note for a person, not an email"
    }

    def ingest(self, raw: RawEnquiry, enquiry: Enquiry, draft: Draft, extractor: str) -> None:
        self.ingest_item(
            raw.id,
            raw.model_dump_json(by_alias=True),
            enquiry.model_dump_json(),
            _QueuedDraft(
                kind=draft.kind,
                to=draft.to,
                subject=draft.subject,
                body=draft.body,
                reasons=draft.reasons,
                payload_json=draft.quote.model_dump_json() if draft.quote else None,
            ),
            extractor,
        )
