from pathlib import Path

import pytest
from conftest import load_sample

from e2q.draft import build_draft
from e2q.queue import AlreadyIngested, AlreadySent, InvalidTransition, NotFound, NotSendable
from e2q.senders import DryRunSender

FROM = "quotes@fernwick.example"


def ingest(queue, business, extractor, sample_id):
    raw = load_sample(sample_id)
    enquiry = extractor.extract(raw)
    queue.ingest(raw, enquiry, build_draft(enquiry, business), extractor.name)
    return raw.id


@pytest.fixture
def sender(tmp_path):
    return DryRunSender(tmp_path / "outbox")


def test_ingest_lands_in_drafted(queue, business, extractor):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    row = queue.get(eid)
    assert (row["state"], row["kind"], row["version"]) == ("drafted", "quote", 1)


def test_ingest_twice_is_refused(queue, business, extractor):
    ingest(queue, business, extractor, "s01-complete-email")
    with pytest.raises(AlreadyIngested):
        ingest(queue, business, extractor, "s01-complete-email")


def test_send_refuses_unapproved_draft(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    with pytest.raises(NotSendable) as exc:
        queue.send(eid, sender, FROM)
    assert exc.value.exit_code != 0
    assert queue.get(eid)["state"] == "drafted"
    assert not sender.outbox.exists()


def test_approved_draft_sends_once_and_second_send_is_refused(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    queue.approve(eid)
    ref = queue.send(eid, sender, FROM)
    assert ref.endswith("s01-complete-email-v1.eml")
    assert queue.get(eid)["state"] == "sent"
    with pytest.raises(AlreadySent) as exc:
        queue.send(eid, sender, FROM)
    assert exc.value.exit_code == 3
    assert "already sent" in str(exc.value)
    assert len(list(sender.outbox.glob("*.eml"))) == 1


def test_edit_counts_as_approval_and_bumps_version(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    version = queue.edit(eid, body="Edited body.")
    assert version == 2
    row = queue.get(eid)
    assert (row["state"], row["body"]) == ("edited", "Edited body.")
    ref = queue.send(eid, sender, FROM)
    assert ref.endswith("-v2.eml")
    assert "Edited body." in Path(ref).read_text(encoding="utf-8")


def test_rejected_draft_can_never_be_sent_or_approved(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    queue.reject(eid, note="wrong price")
    with pytest.raises(NotSendable):
        queue.send(eid, sender, FROM)
    with pytest.raises(InvalidTransition):
        queue.approve(eid)


def test_sent_is_terminal(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    queue.approve(eid)
    queue.send(eid, sender, FROM)
    for action in (queue.approve, queue.reject):
        with pytest.raises(InvalidTransition):
            action(eid)
    with pytest.raises(InvalidTransition):
        queue.edit(eid, body="too late")


def test_handoff_note_is_never_sent(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s14-prompt-injection")
    queue.approve(eid)
    with pytest.raises(NotSendable) as exc:
        queue.send(eid, sender, FROM)
    assert "handoff" in str(exc.value)


def test_failed_send_leaves_no_log_and_can_be_retried(queue, business, extractor, tmp_path):
    class Broken:
        name = "broken"

        def send(self, **kwargs):
            raise OSError("network down")

    eid = ingest(queue, business, extractor, "s01-complete-email")
    queue.approve(eid)
    with pytest.raises(OSError):
        queue.send(eid, Broken(), FROM)
    assert queue.get(eid)["state"] == "approved"
    assert queue.show(eid)["send_log"] == []
    queue.send(eid, DryRunSender(tmp_path / "out"), FROM)
    assert queue.get(eid)["state"] == "sent"


def test_every_transition_is_logged_with_actor_and_time(queue, business, extractor, sender):
    eid = ingest(queue, business, extractor, "s01-complete-email")
    queue.edit(eid, subject="New subject")
    queue.approve(eid)
    queue.send(eid, sender, FROM)
    history = queue.show(eid)["transitions"]
    assert [(t["from_state"], t["to_state"], t["actor"]) for t in history] == [
        (None, "drafted", "system"),
        ("drafted", "edited", "owner"),
        ("edited", "approved", "owner"),
        ("approved", "sent", "owner"),
    ]
    assert all(t["at"] for t in history)


def test_unknown_id(queue):
    with pytest.raises(NotFound):
        queue.approve("nope")
