"""Senders, from smb-agent-kit, with this project's defaults.

DryRunSender (default) writes the email to `outbox/` with an `X-E2Q-Key` header; ResendSender
needs a key. A sender is only ever called by the queue after the approval gate and the send-log
check.
"""

from __future__ import annotations

from pathlib import Path

from smb_agent_kit import delivery
from smb_agent_kit.delivery import ResendSender, Sender, SenderUnavailable

DEFAULT_OUTBOX = Path(__file__).resolve().parent.parent / "outbox"
KEY_HEADER = "X-E2Q-Key"

__all__ = ["DryRunSender", "ResendSender", "Sender", "SenderUnavailable", "make_sender"]


class DryRunSender(delivery.DryRunSender):
    def __init__(self, outbox: Path | None = None):
        super().__init__(Path(outbox) if outbox else DEFAULT_OUTBOX, key_header=KEY_HEADER)


def make_sender(name: str, **kwargs) -> Sender:
    if name == "dry-run":
        return DryRunSender(**kwargs)
    if name == "resend":
        return ResendSender(**kwargs)
    raise ValueError(f"unknown sender: {name}")
