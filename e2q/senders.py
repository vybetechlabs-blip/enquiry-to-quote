"""Senders. DryRunSender (default) writes the email to `outbox/`; ResendSender needs a key.

A sender is only ever called by the queue after the approval gate and the send-log check.
"""

from __future__ import annotations

import json
import os
import urllib.request
from pathlib import Path
from typing import Protocol

DEFAULT_OUTBOX = Path(__file__).resolve().parent.parent / "outbox"


class Sender(Protocol):
    name: str

    def send(self, *, key: str, to: str, sender: str, subject: str, body: str) -> str:
        """Deliver one message and return a reference to it."""
        ...


class SenderUnavailable(RuntimeError):
    pass


class DryRunSender:
    name = "dry-run"

    def __init__(self, outbox: Path | None = None):
        self.outbox = Path(outbox) if outbox else DEFAULT_OUTBOX

    def send(self, *, key: str, to: str, sender: str, subject: str, body: str) -> str:
        self.outbox.mkdir(parents=True, exist_ok=True)
        path = self.outbox / f"{key}.eml"
        path.write_text(
            f"From: {sender}\nTo: {to}\nSubject: {subject}\nX-E2Q-Key: {key}\n\n{body}\n",
            encoding="utf-8",
        )
        return str(path)


class ResendSender:
    """Resend HTTP API. Never exercised by the test suite; needs RESEND_API_KEY to construct."""

    name = "resend"
    endpoint = "https://api.resend.com/emails"

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or os.environ.get("RESEND_API_KEY")
        if not self.api_key:
            raise SenderUnavailable("RESEND_API_KEY is not set")

    def send(self, *, key: str, to: str, sender: str, subject: str, body: str) -> str:
        payload = {"from": sender, "to": [to], "subject": subject, "text": body}
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read()).get("id", "")


def make_sender(name: str, **kwargs) -> Sender:
    if name == "dry-run":
        return DryRunSender(**kwargs)
    if name == "resend":
        return ResendSender(**kwargs)
    raise ValueError(f"unknown sender: {name}")
