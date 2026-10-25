"""e2q command line: ingest | list | show | approve | edit | reject | send | eval."""

from __future__ import annotations

import glob
import json
from decimal import Decimal
from pathlib import Path

import typer
import yaml

from e2q.config import load_business
from e2q.draft import build_draft
from e2q.extract import GuardedExtractor, LLMExtractor, RuleExtractor
from e2q.pricing import fmt_money
from e2q.providers import CachedLLM, ProviderUnavailable, make_provider
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


def _provider_args(row: str) -> tuple[str, str]:
    provider, model = split_row(row)
    return provider, model


def open_queue() -> ApprovalQueue:
    return ApprovalQueue(state.db)


def fail(err: QueueError) -> None:
    typer.echo(str(err), err=True)
    raise typer.Exit(err.exit_code)


def split_row(row: str) -> tuple[str, str]:
    """`ollama:gpt-oss:20b` -> ("ollama", "gpt-oss:20b"). The model id is never guessed."""
    provider, _, model = row.partition(":")
    if not model:
        raise typer.BadParameter(f"{row!r}: use provider:model, e.g. ollama:gpt-oss:20b")
    return provider, model


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
    llm: str = typer.Option(
        None,
        "--llm",
        help="LLM extraction and cover note, as provider:model (ollama or anthropic).",
    ),
    prompt: str = typer.Option("v1", help="LLM prompt version: v1 or v2."),
    guard: bool = typer.Option(
        False, "--guard", help="With --llm: also run RuleExtractor; hand off when they disagree."
    ),
) -> None:
    """Extract, price and draft each enquiry, then park the draft in the approval queue."""
    business = load_business(state.business_dir)
    cover_writer = None
    if llm:
        from e2q.cover import make_cover_writer

        try:
            name, model = _provider_args(llm)
            provider = make_provider(name, model=model)
        except ProviderUnavailable as exc:
            typer.echo(f"LLM mode unavailable: {exc}", err=True)
            raise typer.Exit(2) from exc
        extractor = LLMExtractor(business, provider, prompt)
        if guard:
            extractor = GuardedExtractor(extractor, RuleExtractor(business))
        cover_writer = make_cover_writer(provider, business, prompt)
    else:
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
        draft = build_draft(enquiry, business, cover_writer)
        try:
            queue.ingest(raw, enquiry, draft, getattr(extractor, "row_name", extractor.name))
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
    llm: list[str] = typer.Option(
        None, "--llm", help="Also run this LLM row (provider:model) and save it. Repeatable."
    ),
    prompt: str = typer.Option("v1", help="LLM prompt version for --llm rows: v1 or v2."),
    passes: int = typer.Option(1, min=1, help="Passes per --llm row (each saved separately)."),
    guard: bool = typer.Option(
        False, "--guard", help="Also score a +guard row from the same model outputs."
    ),
) -> None:
    """Score RuleExtractor and every saved LLM row on each golden set; write eval/REPORT.md."""
    from e2q.evaluate import default_sets, run_eval, save_run, saved_runs, skipped, write_report

    business = load_business(state.business_dir)
    sets = default_sets()
    for row in llm or []:
        name, model = split_row(row)
        try:
            provider = make_provider(name, model=model)
        except ProviderUnavailable as exc:
            typer.echo(f"row {row} skipped: {exc}", err=True)
            for _, golden, _ in sets:
                skipped_row = row if prompt == "v1" else f"{row}@{prompt}"
                save_run(skipped(skipped_row, golden, str(exc)), golden)
            continue

        def show(c):
            typer.echo(
                f"  {c.sample_id:<28} {c.outcome:<14} {'MISS' if c.failed else 'ok'}"
                f"  {c.latency_s}s",
                err=True,
            )

        for n in range(1, passes + 1):
            # One model call per inquiry per pass; the guard row re-scores the same outputs.
            cached = CachedLLM(provider)
            for title, golden, samples in sets:
                plain = LLMExtractor(business, cached, prompt)
                typer.echo(f"pass {n}: {plain.row_name} on {title} ...", err=True)
                result = run_eval(
                    business,
                    plain,
                    golden,
                    samples,
                    row=plain.row_name,
                    progress=show,
                    pass_index=n,
                )
                typer.echo(f"saved {save_run(result, golden)}", err=True)
                if guard:
                    guarded = GuardedExtractor(
                        LLMExtractor(business, cached, prompt), RuleExtractor(business)
                    )
                    result = run_eval(
                        business, guarded, golden, samples, row=guarded.row_name, pass_index=n
                    )
                    typer.echo(f"saved {save_run(result, golden)}", err=True)
    sections = [
        (
            title,
            golden,
            [run_eval(business, golden_path=golden, samples_dir=samples), *saved_runs(golden)],
        )
        for title, golden, samples in sets
    ]
    write_report(sections, out)
    typer.echo(out.read_text(encoding="utf-8"))


@app.command()
def rescore(
    fill: list[str] = typer.Option(
        None,
        "--fill",
        help="Row (provider:model@prompt) allowed new calls for new cases and infrastructure "
        "failures. Repeatable. Rows not named here get no calls.",
    ),
) -> None:
    """Re-score saved LLM runs against the current golden files and pricing code."""
    from e2q.evaluate import default_sets, save_run, saved_runs
    from e2q.rescore import rescore_run

    business = load_business(state.business_dir)
    providers = {}
    for row in fill or []:
        base, _, version = row.partition("@")
        name, model = split_row(base)
        try:
            providers[row] = (make_provider(name, model=model), version or "v1")
        except ProviderUnavailable as exc:
            typer.echo(f"--fill {row}: unavailable ({exc}); its runs get no new calls", err=True)
    for title, golden, samples in default_sets():
        runs = [r for r in saved_runs(golden) if r.status == "ok"]
        guards = {(r.extractor, r.pass_index): r for r in runs if r.extractor.endswith("+guard")}
        for plain in (r for r in runs if not r.extractor.endswith("+guard")):
            provider, version = providers.get(plain.extractor, (None, None))
            golden_ids = set(yaml.safe_load(golden.read_text(encoding="utf-8")))
            missing = golden_ids - {c.sample_id for c in plain.cases}
            if missing and provider is None:
                typer.echo(
                    f"skip  {plain.extractor} p{plain.pass_index} on {title}: "
                    f"{len(missing)} new case(s) and no --fill; left as it was"
                )
                continue
            guard = guards.get((f"{plain.extractor}+guard", plain.pass_index))
            new_plain, new_guard, calls = rescore_run(
                business,
                plain,
                guard,
                golden,
                samples,
                provider,
                version or ("v2" if "@v2" in plain.extractor else "v1"),
            )
            save_run(new_plain, golden)
            if new_guard is not None:
                save_run(new_guard, golden)
            retries = sum(
                c.retries or 0
                for c in new_plain.cases
                if c.sample_id in {x.split(" ")[0] for x in calls}
            )
            typer.echo(
                f"done  {plain.extractor} p{plain.pass_index} on {title}: "
                f"{len(calls)} new call(s), {retries} retried"
                + (f" [{'; '.join(calls)}]" if calls else "")
            )


def main() -> None:
    app()
