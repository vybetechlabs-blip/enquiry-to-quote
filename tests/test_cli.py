import pytest
from conftest import ROOT
from typer.testing import CliRunner

from e2q.cli import app


@pytest.fixture
def run(tmp_path, monkeypatch):
    """Run the CLI from the repo root with a throwaway queue database and outbox."""
    monkeypatch.chdir(ROOT)
    monkeypatch.setattr("e2q.senders.DEFAULT_OUTBOX", tmp_path / "outbox")
    db = str(tmp_path / "cli.db")
    runner = CliRunner()

    def _run(*args):
        return runner.invoke(app, ["--db", db, *args])

    return _run


def test_ingest_expands_globs_itself_and_lists_every_sample(run):
    result = run("ingest", "inbox/samples/*.json")
    assert result.exit_code == 0, result.output
    count = len(list((ROOT / "inbox" / "samples").glob("*.json")))
    assert result.output.count("ingested") == count
    listing = run("list")
    assert listing.exit_code == 0
    assert f"{count} draft(s)" in listing.output
    assert "s10-two-sites" in listing.output and "$1,214.10" in listing.output


def test_reingest_skips(run):
    run("ingest", "inbox/samples/s01-complete-email.json")
    again = run("ingest", "inbox/samples/s01-complete-email.json")
    assert again.exit_code == 0 and "skipped" in again.output


def test_send_unapproved_exits_non_zero(run):
    run("ingest", "inbox/samples/s01-complete-email.json")
    result = run("send", "s01-complete-email")
    assert result.exit_code == 2
    assert "only approved or edited drafts are sent" in result.output


def test_second_send_exits_non_zero_with_idempotency_message(run, tmp_path):
    run("ingest", "inbox/samples/s01-complete-email.json")
    assert run("approve", "s01-complete-email").exit_code == 0
    first = run("send", "s01-complete-email")
    assert first.exit_code == 0, first.output
    assert (tmp_path / "outbox" / "s01-complete-email-v1.eml").exists()
    second = run("send", "s01-complete-email")
    assert second.exit_code == 3
    assert "already sent" in second.output and "never sent twice" in second.output


def test_edit_reject_and_show(run, tmp_path):
    run("ingest", "inbox/samples/s02-complete-webform.json", "inbox/samples/s05-carpet.json")
    body = tmp_path / "body.txt"
    body.write_text("Hand-written reply.", encoding="utf-8")
    assert run("edit", "s02-complete-webform", "--body-file", str(body)).exit_code == 0
    assert run("reject", "s05-carpet", "--note", "duplicate").exit_code == 0
    shown = run("show", "s02-complete-webform")
    assert "state=edited" in shown.output and "version=2" in shown.output
    assert "drafted -> edited  by owner" in shown.output
    assert run("send", "s05-carpet").exit_code == 2


def test_resend_without_key_is_refused(run, monkeypatch):
    monkeypatch.delenv("RESEND_API_KEY", raising=False)
    run("ingest", "inbox/samples/s01-complete-email.json")
    run("approve", "s01-complete-email")
    result = run("send", "s01-complete-email", "--sender", "resend")
    assert result.exit_code == 2 and "RESEND_API_KEY" in result.output


def test_llm_flag_is_not_wired_yet(run):
    result = run("ingest", "--llm", "inbox/samples/s01-complete-email.json")
    assert result.exit_code == 2


def test_eval_writes_report(run, tmp_path):
    out = tmp_path / "REPORT.md"
    result = run("eval", "--out", str(out))
    assert result.exit_code == 0, result.output
    text = out.read_text(encoding="utf-8")
    assert "Extractor: `RuleExtractor`" in text
    assert "Price exact, on expected quotes" in text
