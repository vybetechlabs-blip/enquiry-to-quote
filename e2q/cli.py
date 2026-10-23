"""e2q command line: ingest | list | show | approve | edit | reject | send | eval."""

from __future__ import annotations

import glob
import json
from decimal import Decimal
from pathlib import Path

import typer

from e2q.config import load_business
from e2q.draft import build_draft
from e2q.extract import RuleExtractor
from e2q.pricing import fmt_money
from e2q.queue import AlreadyIngested, ApprovalQueue, QueueError
from e2q.schema import RawEnquiry
from e2q.senders import SenderUnavailable, make_sender

app = typer.Typer(add_completion=False, no_args_is_help=True, help=__doc__)
ACTOR = "owner"  # every CLI transition is logged as the owner


class State:
    db: Path
    business_dir: Path | None


state = State()


@app.callback()
def options(
    db: Path = typer.Option(Path("e2q.db"), envvar="E2Q_DB", help="Queue database file."),
    business: Path = typer.Option(None, help="Business config folder (default: business/)."),
) -> None:
    state.db = db
    state.business_dir = business


def open_queue() -> ApprovalQueue:
    return ApprovalQueue(state.db)


def fail(err: QueueError) -> None:
    typer.echo(str(err), err=True)
    raise typer.Exit(err.exit_code)


def expand(patterns: list[str]) -> list[Path]:
    """Expand globs here: PowerShell passes `*.json` through unexpanded."""
    paths: list[Path] = []
    for pattern in patterns:
        matches = sorted(glob.glob(pattern)) if any(c in pattern for c in "*?[") else [pattern]
        paths += [Path(m) for m in matches]
    return paths


@app.command()
def ingest(
    files: list[str] = typer.Argument(..., help="Enquiry JSON files or globs."),
    llm: bool = typer.Option(False, "--llm", help="LLM extraction (Phase 1, not wired yet)."),
) -> None:
    """Extract, price and draft each enquiry, then park the draft in the approval queue."""
    if llm:
        typer.echo("LLM mode is Phase 1 and is not wired yet; run without --llm.", err=True)
        raise typer.Exit(2)
    business = load_business(state.business_dir)
    extractor = RuleExtractor(business)
    queue = open_queue()
    paths = expand(files)
    if not paths:
        typer.echo("no files matched", err=True)
        raise typer.Exit(1)
    errors = 0
    for path in paths:
        try:
            raw = RawEnquiry.model_validate(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError) as exc:
            typer.echo(f"error     {path}: {exc}", err=True)
            errors += 1
            continue
        enquiry = extractor.extract(raw)
        draft = build_draft(enquiry, business)
        try:
            queue.ingest(raw, enquiry, draft, extractor.name)
        except AlreadyIngested as exc:
            typer.echo(f"skipped   {exc}")
            continue
        typer.echo(f"ingested  {raw.id:<28} {draft.kind:<14} drafted")
    queue.close()
    if errors:
        raise typer.Exit(1)


@app.command("list")
def list_cmd() -> None:
    """List every draft with its kind, state and total."""
    business = load_business(state.business_dir)
    sym = business.rate_card.currency_symbol
    queue = open_queue()
    rows = queue.list()
    typer.echo(f"{'ID':<28} {'KIND':<14} {'STATE':<9} {'VER':>3}  {'TOTAL':>12}  TO")
    for r in rows:
        total = ""
        if r["quote_json"]:
            quote = json.loads(r["quote_json"])
            total = fmt_money(Decimal(quote["total"]), sym)
        typer.echo(
            f"{r['enquiry_id']:<28} {r['kind']:<14} {r['state']:<9} {r['version']:>3}  "
            f"{total:>12}  {r['to_addr'] or '-'}"
        )
    typer.echo(f"{len(rows)} draft(s)")
    queue.close()


@app.command()
def show(enquiry_id: str) -> None:
    """Show one draft, what was extracted, and its full transition and send history."""
    queue = open_queue()
    try:
        info = queue.show(enquiry_id)
    except QueueError as err:
        fail(err)
    d = info["draft"]
    typer.echo(f"{d['enquiry_id']}  kind={d['kind']}  state={d['state']}  version={d['version']}")
    typer.echo(f"To: {d['to_addr'] or '-'}\nSubject: {d['subject']}\n")
    typer.echo(d["body"])
    if d["quote_json"]:
        quote = json.loads(d["quote_json"])
        typer.echo(f"\nrule ids: {', '.join(quote['rule_ids'])}")
    typer.echo("\nextracted:")
    typer.echo(json.dumps(info["enquiry"], indent=2))
    typer.echo("\nhistory:")
    for t in info["transitions"]:
        note = f"  ({t['note']})" if t["note"] else ""
        typer.echo(
            f"  {t['at']}  v{t['version']}  {t['from_state'] or '-'} -> {t['to_state']}"
            f"  by {t['actor']}{note}"
        )
    for s in info["send_log"]:
        typer.echo(f"  sent v{s['version']} at {s['sent_at']} via {s['sender']}: {s['ref']}")
    queue.close()


@app.command()
def approve(enquiry_id: str) -> None:
    """Approve a draft for sending."""
    queue = open_queue()
    try:
        queue.approve(enquiry_id, actor=ACTOR)
    except QueueError as err:
        fail(err)
    typer.echo(f"approved  {enquiry_id}")
    queue.close()


@app.command()
def reject(enquiry_id: str, note: str = typer.Option(None, help="Why it was rejected.")) -> None:
    """Reject a draft. Rejected drafts can never be sent."""
    queue = open_queue()
    try:
        queue.reject(enquiry_id, actor=ACTOR, note=note)
    except QueueError as err:
        fail(err)
    typer.echo(f"rejected  {enquiry_id}")
    queue.close()


@app.command()
def edit(
    enquiry_id: str,
    body_file: Path = typer.Option(None, help="File holding the new body."),
    subject: str = typer.Option(None, help="New subject line."),
) -> None:
    """Replace the subject and/or body. Saved as a new version in state `edited`."""
    if body_file is None and subject is None:
        typer.echo("nothing to edit: pass --body-file and/or --subject", err=True)
        raise typer.Exit(1)
    body = body_file.read_text(encoding="utf-8") if body_file else None
    queue = open_queue()
    try:
        version = queue.edit(enquiry_id, body=body, subject=subject, actor=ACTOR)
    except QueueError as err:
        fail(err)
    typer.echo(f"edited    {enquiry_id} -> v{version}")
    queue.close()


@app.command()
def send(
    enquiry_id: str,
    sender: str = typer.Option("dry-run", help="dry-run (writes outbox/) or resend (needs key)."),
) -> None:
    """Send an approved or edited draft. Refuses anything else, and refuses a repeat send."""
    business = load_business(state.business_dir)
    try:
        backend = make_sender(sender)
    except SenderUnavailable as exc:
        typer.echo(f"refused: {exc}", err=True)
        raise typer.Exit(2) from exc
    queue = open_queue()
    try:
        ref = queue.send(enquiry_id, backend, business.profile.reply_from, actor=ACTOR)
    except QueueError as err:
        fail(err)
    typer.echo(f"sent      {enquiry_id} via {backend.name}: {ref}")
    queue.close()


@app.command("eval")
def eval_cmd(
    out: Path = typer.Option(Path("eval/REPORT.md"), help="Where to write the report."),
) -> None:
    """Run the golden set end to end with RuleExtractor and write eval/REPORT.md."""
    from e2q.evaluate import run_eval, write_report

    business = load_business(state.business_dir)
    result = run_eval(business)
    write_report(result, out)
    typer.echo(out.read_text(encoding="utf-8"))


def main() -> None:
    app()
