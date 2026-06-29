"""PR helpers, terminal state, and postmerge phase for ship-pr."""
# pyright: reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

import json
from contextlib import suppress
from pathlib import Path
from typing import cast

from larch.core import config
from larch.core.proc import Runner
from larch.core.run_context import RunContext
from larch.errors import ShipError
from larch.git import git
from larch.git import push
from larch.outcomes import Outcome
from larch.report import run_logs
from larch.state import finalize
from larch.implement.ship_state import _tmpdir_under_allowed_root, _write_ship_state, _breadcrumb
from larch.implement.ship_result import ShipResult, _write_terminal_finalize_if_terminal


def _summary_from_manifest(ctx: RunContext) -> str:
    if ctx.summary:
        return ctx.summary
    manifest_path = Path(ctx.manifest_path)
    if manifest_path.is_file():
        try:
            loaded = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            data = cast("dict[str, object]", loaded)
            bullets_obj = data.get("summary_bullets")
            if isinstance(bullets_obj, list) and bullets_obj:
                bullets = [item for item in cast("list[object]", bullets_obj) if isinstance(item, str)]
                return "\n".join(f"- {item}" for item in bullets) + "\n"
    return "- Implement requested changes.\n"


def _write_ci_fix_detail_log(*, ctx: RunContext, detail: str) -> str:
    """Write the ci-fix exhaustion detail text to a tmpdir file; return path or empty."""
    if not detail or not ctx.tmpdir or not _tmpdir_under_allowed_root(ctx.tmpdir):
        return ""
    try:
        path = Path(ctx.tmpdir) / "ci-fix-exhausted-detail.log"
        _ = path.write_text(detail, encoding="utf-8")
        return str(path)
    except OSError:
        return ""


def _pr_title(*, ctx: RunContext, runner: Runner, cwd: str | None) -> str:
    issue = ctx.issue_number or ctx.issue
    prefix = f"Fixes #{issue}: " if issue and str(issue).isdigit() else ""
    if ctx.pr_title:
        title = ctx.pr_title
        return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"
    subject = git.log_subject(runner, "HEAD", cwd=cwd)
    if subject.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX):
        subject = ""
    title = subject or f"Implement issue #{issue or ctx.issue}"
    return title if not prefix or title.startswith(prefix) else f"{prefix}{title}"


def _postmerge_should_flush(ctx: RunContext) -> bool:
    return bool(
        run_logs.effective_run_id(ctx)
        and ctx.pr_number is not None
        and not ctx.repo_unavailable
        and ctx.pr_closed
    )


def _write_terminal_state(
    *,
    ctx: RunContext,
    result: Outcome,
    step: str,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
    failed_run_id: str = "",
    bail_failure_detail_log: str = "",
    last_monitored_head: str | None = None,
) -> None:
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return
    terminal_ctx = ctx.with_(stall_tracking=result is Outcome.STALLED, stall_step=step)
    _write_terminal_finalize_if_terminal(
        ctx=terminal_ctx,
        result=result,
        step=step,
        failed_run_id=failed_run_id,
        bail_failure_detail_log=bail_failure_detail_log,
    )
    phase = "done" if result is Outcome.OK else "stalled"
    _write_ship_state(
        terminal_ctx,
        phase=phase,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        transient_retries=transient_retries,
        terminal_outcome=result,
        failed_run_id=failed_run_id,
        bail_failure_detail_log=bail_failure_detail_log,
        last_monitored_head=last_monitored_head,
    )


def _publish_post_pr_terminal_snapshot(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str,
) -> None:
    if ctx.pr_number is None:
        return
    with suppress(Exception):
        refresh = run_logs.flush_logs_pre(
            runner=runner,
            ctx=ctx.with_(state_file=None),
            cwd=cwd,
            strict_final_report=True,
        )
        if not refresh.skipped:
            with suppress(ShipError):
                _ = push.push_branch(runner=runner, ctx=ctx, cwd=cwd)


def run_postmerge_phase(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> ShipResult:
    if not ctx.merge or not ctx.pr_closed:
        return ShipResult(Outcome.STALLED, detail="postmerge requires a closed merge PR")
    sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    if ctx.pr_closed:
        _ = sentinel.write_text(f"MERGE_RESULT={ctx.merge_result}\n", encoding="utf-8")
    post: finalize.FinalizeResult = finalize.postmerge(runner=runner, ctx=ctx, cwd=cwd)
    state_ctx = ctx.with_(
        pr_closed=ctx.pr_closed,
        stall_tracking=post.outcome is Outcome.STALLED,
        stall_step=post.status if post.outcome is Outcome.STALLED else ctx.stall_step,
    )
    if post.outcome is Outcome.OK:
        _write_terminal_finalize_if_terminal(ctx=state_ctx, result=Outcome.OK, step="")
    if post.outcome is Outcome.OK and _postmerge_should_flush(state_ctx):
        skip: run_logs.RefreshSkip = run_logs.finalize_postmerge_logs(state_ctx, merge_result=state_ctx.merge_result, runner=runner)
        if skip.skipped:
            _breadcrumb(step="warning", detail=f"post-merge flush skipped: {skip.reason}")
            stall_ctx = state_ctx.with_(stall_tracking=True, stall_step="postmerge-flush")
            _write_terminal_finalize_if_terminal(ctx=stall_ctx, result=Outcome.STALLED, step="postmerge-flush")
            _write_ship_state(stall_ctx, phase="postmerge", terminal_outcome=Outcome.STALLED)
            return ShipResult(Outcome.STALLED, detail=f"post-merge flush skipped: {skip.reason}")
    if post.outcome is not Outcome.OK:
        _write_terminal_finalize_if_terminal(ctx=state_ctx, result=post.outcome, step=post.status)
        _write_ship_state(state_ctx, phase="postmerge", terminal_outcome=post.outcome)
        return ShipResult(post.outcome, detail=post.detail or post.status)
    _write_ship_state(state_ctx, phase="done", terminal_outcome=Outcome.OK)
    return ShipResult(
        Outcome.OK,
        pr_number=ctx.pr_number,
        pr_url=ctx.pr_url,
        merge_result=ctx.merge_result,
    )
