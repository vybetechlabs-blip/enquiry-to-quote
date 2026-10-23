"""Approval queue: one SQLite file, a state machine, and an idempotent send log.

States: drafted -> (approved | edited | rejected) -> sent.
Nothing reaches a sender unless the draft is `approved` or `edited`. The send log is keyed by
enquiry id + draft version, and a second send of a key that is already logged is refused with an
error, never skipped silently. Every transition is logged with a timestamp and an actor.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from e2q.schema import Draft, Enquiry, RawEnquiry
from e2q.senders import Sender

ALLOWED = {
    "drafted": {"approved", "edited", "rejected"},
    "approved": {"edited", "rejected", "sent"},
    "edited": {"approved", "edited", "rejected", "sent"},
    "rejected": set(),
    "sent": set(),
}
SENDABLE_STATES = {"approved", "edited"}

SCHEMA = """
CREATE TABLE IF NOT EXISTS enquiries (
    enquiry_id TEXT PRIMARY KEY,
    raw_json TEXT NOT NULL,
    extracted_json TEXT NOT NULL,
    extractor TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS drafts (
    enquiry_id TEXT PRIMARY KEY REFERENCES enquiries(enquiry_id),
    version INTEGER NOT NULL,
    kind TEXT NOT NULL,
    state TEXT NOT NULL,
    to_addr TEXT,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    quote_json TEXT,
    reasons_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS draft_versions (
    enquiry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    subject TEXT NOT NULL,
    body TEXT NOT NULL,
    actor TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (enquiry_id, version)
);
CREATE TABLE IF NOT EXISTS transitions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    enquiry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    from_state TEXT,
    to_state TEXT NOT NULL,
    actor TEXT NOT NULL,
    at TEXT NOT NULL,
    note TEXT
);
CREATE TABLE IF NOT EXISTS send_log (
    enquiry_id TEXT NOT NULL,
    version INTEGER NOT NULL,
    sent_at TEXT NOT NULL,
    sender TEXT NOT NULL,
    ref TEXT,
    PRIMARY KEY (enquiry_id, version)
);
"""


class QueueError(Exception):
    exit_code = 1


class NotFound(QueueError):
    exit_code = 1


class AlreadyIngested(QueueError):
    exit_code = 1


class InvalidTransition(QueueError):
    exit_code = 2


class NotSendable(QueueError):
    exit_code = 2


class AlreadySent(QueueError):
    exit_code = 3


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def send_key(enquiry_id: str, version: int) -> str:
    return f"{enquiry_id}-v{version}"


class ApprovalQueue:
    def __init__(self, path: Path | str):
        self.path = Path(path)
        self.db = sqlite3.connect(self.path, isolation_level=None)
        self.db.row_factory = sqlite3.Row
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    # --- reads ----------------------------------------------------------------------------

    def get(self, enquiry_id: str) -> sqlite3.Row:
        row = self.db.execute("SELECT * FROM drafts WHERE enquiry_id = ?", (enquiry_id,)).fetchone()
        if row is None:
            raise NotFound(f"no draft for enquiry {enquiry_id!r}")
        return row

    def list(self) -> list[sqlite3.Row]:
        return self.db.execute(
            "SELECT d.*, e.ingested_at FROM drafts d JOIN enquiries e USING (enquiry_id) "
            "ORDER BY e.ingested_at, d.enquiry_id"
        ).fetchall()

    def show(self, enquiry_id: str) -> dict:
        draft = self.get(enquiry_id)
        enquiry = self.db.execute(
            "SELECT * FROM enquiries WHERE enquiry_id = ?", (enquiry_id,)
        ).fetchone()
        transitions = self.db.execute(
            "SELECT * FROM transitions WHERE enquiry_id = ? ORDER BY id", (enquiry_id,)
        ).fetchall()
        sends = self.db.execute(
            "SELECT * FROM send_log WHERE enquiry_id = ? ORDER BY version", (enquiry_id,)
        ).fetchall()
        return {
            "draft": dict(draft),
            "enquiry": json.loads(enquiry["extracted_json"]),
            "transitions": [dict(t) for t in transitions],
            "send_log": [dict(s) for s in sends],
        }

    # --- writes ---------------------------------------------------------------------------

    def _log(self, enquiry_id, version, from_state, to_state, actor, note=None) -> None:
        self.db.execute(
            "INSERT INTO transitions (enquiry_id, version, from_state, to_state, actor, at, note) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (enquiry_id, version, from_state, to_state, actor, now(), note),
        )

    def _check(self, row: sqlite3.Row, to_state: str) -> None:
        if to_state not in ALLOWED[row["state"]]:
            raise InvalidTransition(
                f"{row['enquiry_id']}: cannot go from {row['state']} to {to_state}"
            )

    def ingest(self, raw: RawEnquiry, enquiry: Enquiry, draft: Draft, extractor: str) -> None:
        exists = self.db.execute(
            "SELECT 1 FROM enquiries WHERE enquiry_id = ?", (raw.id,)
        ).fetchone()
        if exists:
            raise AlreadyIngested(f"{raw.id} is already in the queue")
        ts = now()
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO enquiries VALUES (?, ?, ?, ?, ?)",
                (
                    raw.id,
                    raw.model_dump_json(by_alias=True),
                    enquiry.model_dump_json(),
                    extractor,
                    ts,
                ),
            )
            self.db.execute(
                "INSERT INTO drafts VALUES (?, 1, ?, 'drafted', ?, ?, ?, ?, ?, ?)",
                (
                    raw.id,
                    draft.kind,
                    draft.to,
                    draft.subject,
                    draft.body,
                    draft.quote.model_dump_json() if draft.quote else None,
                    json.dumps(draft.reasons),
                    ts,
                ),
            )
            self.db.execute(
                "INSERT INTO draft_versions VALUES (?, 1, ?, ?, 'system', ?)",
                (raw.id, draft.subject, draft.body, ts),
            )
            self._log(raw.id, 1, None, "drafted", "system", note=draft.kind)
            self.db.execute("COMMIT")
        except Exception:
            self.db.execute("ROLLBACK")
            raise

    def _transition(self, enquiry_id: str, to_state: str, actor: str, note: str | None) -> None:
        row = self.get(enquiry_id)
        self._check(row, to_state)
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute(
            "UPDATE drafts SET state = ?, updated_at = ? WHERE enquiry_id = ?",
            (to_state, now(), enquiry_id),
        )
        self._log(enquiry_id, row["version"], row["state"], to_state, actor, note)
        self.db.execute("COMMIT")

    def approve(self, enquiry_id: str, actor: str = "owner") -> None:
        self._transition(enquiry_id, "approved", actor, None)

    def reject(self, enquiry_id: str, actor: str = "owner", note: str | None = None) -> None:
        self._transition(enquiry_id, "rejected", actor, note)

    def edit(
        self,
        enquiry_id: str,
        *,
        body: str | None = None,
        subject: str | None = None,
        actor: str = "owner",
    ) -> int:
        """Save an edited draft as a new version. An edit by the owner counts as approval."""
        row = self.get(enquiry_id)
        self._check(row, "edited")
        version = row["version"] + 1
        new_subject = subject if subject is not None else row["subject"]
        new_body = body if body is not None else row["body"]
        ts = now()
        self.db.execute("BEGIN IMMEDIATE")
        self.db.execute(
            "UPDATE drafts SET version = ?, state = 'edited', subject = ?, body = ?, "
            "updated_at = ? WHERE enquiry_id = ?",
            (version, new_subject, new_body, ts, enquiry_id),
        )
        self.db.execute(
            "INSERT INTO draft_versions VALUES (?, ?, ?, ?, ?, ?)",
            (enquiry_id, version, new_subject, new_body, actor, ts),
        )
        self._log(enquiry_id, version, row["state"], "edited", actor)
        self.db.execute("COMMIT")
        return version

    def send(self, enquiry_id: str, sender: Sender, from_addr: str, actor: str = "owner") -> str:
        row = self.get(enquiry_id)
        version = row["version"]
        key = send_key(enquiry_id, version)
        logged = self.db.execute(
            "SELECT * FROM send_log WHERE enquiry_id = ? AND version = ?", (enquiry_id, version)
        ).fetchone()
        if logged:
            raise AlreadySent(
                f"refused: {key} was already sent at {logged['sent_at']} via {logged['sender']} "
                f"(ref {logged['ref']}). The same key is never sent twice."
            )
        if row["kind"] == "handoff":
            raise NotSendable(f"refused: {enquiry_id} is a handoff note for a person, not an email")
        if row["state"] not in SENDABLE_STATES:
            raise NotSendable(
                f"refused: {enquiry_id} is {row['state']}; only approved or edited drafts are sent"
            )
        if not row["to_addr"]:
            raise NotSendable(f"refused: {enquiry_id} has no recipient address")

        # The send-log row is written in the same write transaction as the send, so two
        # concurrent sends of one key cannot both get through (primary key + write lock).
        self.db.execute("BEGIN IMMEDIATE")
        try:
            self.db.execute(
                "INSERT INTO send_log (enquiry_id, version, sent_at, sender) VALUES (?, ?, ?, ?)",
                (enquiry_id, version, now(), sender.name),
            )
            ref = sender.send(
                key=key,
                to=row["to_addr"],
                sender=from_addr,
                subject=row["subject"],
                body=row["body"],
            )
            self.db.execute(
                "UPDATE send_log SET ref = ? WHERE enquiry_id = ? AND version = ?",
                (ref, enquiry_id, version),
            )
            self.db.execute(
                "UPDATE drafts SET state = 'sent', updated_at = ? WHERE enquiry_id = ?",
                (now(), enquiry_id),
            )
            self._log(
                enquiry_id, version, row["state"], "sent", actor, note=f"{sender.name}: {ref}"
            )
            self.db.execute("COMMIT")
        except sqlite3.IntegrityError as exc:
            self.db.execute("ROLLBACK")
            raise AlreadySent(f"refused: {key} is already in the send log") from exc
        except Exception:
            self.db.execute("ROLLBACK")
            raise
        return ref
