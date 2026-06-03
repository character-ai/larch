"""Post-review finalize phases for the ship-pr Python driver."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import config
import git
import rebase
import run_logs
import tracking_issue
from errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from outcomes import Outcome
from proc import Runner
from run_context import RunContext


@dataclass(frozen=True)
class FinalizeResult:
    outcome: Outcome
    status: str
    detail: str = ""
    local_cleanup_status: str = ""
    verify_main_status: str = ""
    rename_branch: str = ""
    rename_status: str = ""
    cleanup_removed: bool = False
    sentinel_written: bool = False
    stash_ref: str = ""


def _bool_text(value: object) -> str:
    return "true" if value else "false"


def _result_from_error(exc: Exception) -> FinalizeResult:
    if isinstance(exc, TransientNetworkError):
        return FinalizeResult(Outcome.TRANSIENT, "transient", str(exc))
    if isinstance(exc, NeedsUserInput):
        return FinalizeResult(Outcome.NEEDS_USER_INPUT, "needs-user-input", str(exc))
    return FinalizeResult(Outcome.STALLED, "stalled", str(exc))


def postbump(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> FinalizeResult:
    """Refresh run logs, rebase, and force-push before PR creation."""
    try:
        branch = git.try_current_branch(runner, cwd=cwd)
        target = ctx.branch_name or ctx.branch
        if not branch or (target and branch != target):
            return FinalizeResult(Outcome.STALLED, "branch-invalid", "wrong branch")
        if branch in {"main", "master"} and not (ctx.forked or ctx.forked_target):
            return FinalizeResult(Outcome.STALLED, "branch-protected", "refusing postbump on protected branch")
        _ = run_logs.flush_logs_pre(runner, ctx.with_(state_file=None), cwd=cwd)
        base_remote = "upstream" if ctx.forked or ctx.forked_target else "origin"
        remote_tip = git.try_rev_parse(runner, f"origin/{branch}", cwd=cwd)
        remote_missing = remote_tip is None
        if remote_missing:
            probe = runner.run(["git", "ls-remote", "--exit-code", "origin", f"refs/heads/{branch}"], cwd=cwd)
            if probe.returncode not in {0, 2}:
                raise TransientNetworkError("remote branch probe failed", result=probe)
        result = rebase.rebase_and_push(
            runner,
            repo=ctx.repo,
            run_id=ctx.run_id,
            cwd=cwd,
            tmpdir=ctx.tmpdir,
            base_remote=base_remote,
            base_ref="main",
            defer_push=ctx.repo_unavailable or remote_missing,
            allow_conflict_fix=False,
        )
    except (NeedsUserInput, ShipError, Stalled, TransientNetworkError) as exc:
        return _result_from_error(exc)
    status = "rebased" if result.rebased else "already-fresh"
    if ctx.repo_unavailable or not result.pushed:
        status = f"{status}-push-skipped"
    return FinalizeResult(Outcome.OK, status)


def postmerge(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> FinalizeResult:
    """Delete the local feature branch and verify main; never writes done manifest."""
    if ctx.draft:
        return FinalizeResult(
            Outcome.OK,
            "skipped-draft",
            local_cleanup_status="skipped-draft",
            verify_main_status="skipped",
        )
    if not ctx.merge:
        return FinalizeResult(
            Outcome.OK,
            "skipped-merge-false",
            local_cleanup_status="skipped-merge-false",
            verify_main_status="skipped",
        )
    if ctx.final_bail_reason:
        return FinalizeResult(
            Outcome.OK,
            "skipped-bail",
            local_cleanup_status="skipped-bail",
            verify_main_status="skipped",
        )

    branch = ctx.branch_name or ctx.branch
    if not branch or branch == "main":
        return FinalizeResult(Outcome.STALLED, "branch-invalid", "invalid branch")

    cleanup_status = "success"
    switch = runner.run(["git", "switch", "main"], cwd=cwd)
    if switch.returncode != 0:
        cleanup_status = "partial"
    pull = runner.run(["git", "pull", "--ff-only", "origin", "main"], cwd=cwd)
    if pull.returncode != 0:
        cleanup_status = "partial"
    delete = runner.run(["git", "branch", "-D", "--", branch], cwd=cwd)
    if delete.returncode != 0:
        cleanup_status = "partial"

    expected_title = ctx.pr_title
    if ctx.pr_number is not None and expected_title:
        expected_title = f"{expected_title} (#{ctx.pr_number})"
    actual = git.log_subject(runner, "main", cwd=cwd)
    suffix = f"(#{ctx.pr_number})" if ctx.pr_number is not None else ""
    title_ok = bool(
        expected_title
        and (actual == expected_title or actual.startswith(expected_title) or (suffix and actual.endswith(suffix)))
    )
    verify_status = "verified" if title_ok else "unexpected"
    outcome = Outcome.OK if cleanup_status == "success" and title_ok else Outcome.STALLED
    return FinalizeResult(
        outcome,
        "ok" if outcome is Outcome.OK else "postmerge-failed",
        local_cleanup_status=cleanup_status,
        verify_main_status=verify_status,
    )


def _rename_issue(
    runner: Runner,
    ctx: RunContext,
    state: str,
    *,
    cwd: str | None,
) -> str:
    issue = ctx.issue_number or ctx.issue
    if not issue or ctx.repo_unavailable:
        return "skipped"
    current = ctx.pr_title or f"Issue {issue}"
    result = runner.run(
        ["gh", "issue", "view", str(issue), "--repo", ctx.repo, "--json", "title,state"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return "failed"
    try:
        data = json.loads(result.stdout or "{}")
        if str(data.get("state", "")).upper() not in {"", "OPEN"}:
            return "skipped"
        current = str(data.get("title") or current)
    except json.JSONDecodeError:
        return "failed"
    try:
        _ = tracking_issue.rename(
            runner,
            issue,
            state,
            repo=ctx.repo,
            current_title=current,
            cwd=cwd,
        )
    except ShipError:
        return "failed"
    return "ok"


def auto_stash_stalled_changes(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> str:
    status = git.status_porcelain(runner, cwd=cwd)
    if status.returncode != 0:
        return "git-status-failed"
    if not status.stdout.strip():
        return ""
    label = f"larch-stalled-{ctx.issue_number or 'unknown'}-{ctx.stall_step or 'unknown'}"
    pushed = runner.run(["git", "stash", "push", "-u", "-m", label], cwd=cwd)
    if pushed.returncode != 0:
        return ""
    listed = runner.run(["git", "stash", "list", "--format=%gD %gs"], cwd=cwd)
    for line in listed.stdout.splitlines():
        if label in line:
            return line.split()[0]
    return ""


def _write_stalled_sentinel(
    runner: Runner,
    ctx: RunContext,
    *,
    stash_ref: str,
    cwd: str | None,
) -> bool:
    result = runner.run(["git", "rev-parse", "--git-dir"], cwd=cwd)
    if result.returncode != 0 or not result.stdout.strip():
        return False
    git_dir = Path(cwd or ".") / result.stdout.strip()
    path = git_dir / "larch-stalled-run.txt"
    path.parent.mkdir(parents=True, exist_ok=True)
    issue = ctx.issue_number or ctx.issue
    issue_url = f"https://github.com/{ctx.repo}/issues/{issue}" if issue and ctx.repo else ""
    timestamp = datetime.now(UTC).isoformat()
    content = (
        f"ISSUE_NUMBER={issue}\n"
        f"ISSUE_URL={issue_url}\n"
        f"STALL_STEP={ctx.stall_step or 'unknown'}\n"
        f"STASH_REF={stash_ref}\n"
        f"TIMESTAMP={timestamp}\n"
    )
    tmp = path.with_suffix(".txt.tmp")
    _ = tmp.write_text(content, encoding="utf-8")
    _ = tmp.replace(path)
    return True


def teardown(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> FinalizeResult:
    """Terminal cleanup; preserves artifacts on stalled runs."""
    rename_branch = "C"
    rename_status = "skipped"
    if ctx.stall_tracking:
        rename_branch = "A"
        rename_status = _rename_issue(runner, ctx, "stalled", cwd=cwd)
    elif not ctx.done_rename_applied and (ctx.pr_number is not None or ctx.design_only_done):
        rename_branch = "B"
        rename_status = _rename_issue(runner, ctx, "done", cwd=cwd)

    tmpdir = Path(ctx.tmpdir)
    _ = (tmpdir / ".run-cleaned-up").write_text("", encoding="utf-8")
    stash_ref = ""
    sentinel_written = False
    if ctx.run_id:
        _ = run_logs.load_or_recover_manifest(ctx)
        if ctx.stall_tracking:
            _ = run_logs.update_manifest(
                ctx,
                status=config.MANIFEST_STATUS_PARTIAL,
                steps_ran={"stalled_at_step": ctx.stall_step or "unknown"},
            )
    if ctx.stall_tracking:
        stash_ref = auto_stash_stalled_changes(runner, ctx, cwd=cwd)
        sentinel_written = _write_stalled_sentinel(
            runner,
            ctx,
            stash_ref=stash_ref,
            cwd=cwd,
        )
        return FinalizeResult(
            Outcome.OK,
            "stalled-preserved",
            rename_branch=rename_branch,
            rename_status=rename_status,
            sentinel_written=sentinel_written,
            stash_ref=stash_ref,
        )

    removed = False
    if tmpdir.exists() and _cleanup_target_ok(ctx, tmpdir):
        shutil.rmtree(tmpdir, ignore_errors=True)
        removed = not tmpdir.exists()
    status = "cleaned" if removed else "cleanup-skipped"
    return FinalizeResult(
        Outcome.OK,
        status,
        rename_branch=rename_branch,
        rename_status=rename_status,
        cleanup_removed=removed,
    )


def _cleanup_target_ok(ctx: RunContext, tmpdir: Path) -> bool:
    raw = str(tmpdir)
    cache_root = Path.home() / ".cache" / "larch" / "sessions"
    allowed_prefixes = (
        "/tmp/",  # noqa: S108 - parity allowlist for session tmpdirs.
        "/private/tmp/",
        "/var/folders/",
        "/private/var/folders/",
        str(cache_root) + "/",
    )
    if not raw.startswith(allowed_prefixes):
        return False
    prefix = ctx.expected_tmpdir_basename_prefix
    if not prefix:
        repo = Path.cwd().name or "_"
        prefix = f"claude-implement-{repo[:32]}-"
    if prefix and not tmpdir.name.startswith(prefix):
        session_file = tmpdir / "session-id"
        if not ctx.expected_session_id or not session_file.is_file():
            return False
        return session_file.read_text(encoding="utf-8").strip() == ctx.expected_session_id
    if ctx.expected_session_id:
        session_file = tmpdir / "session-id"
        if not session_file.is_file():
            return False
        return session_file.read_text(encoding="utf-8").strip() == ctx.expected_session_id
    return True


def write_finalize_state(ctx: RunContext, path: str | Path) -> None:
    """Write implement-finalize.sh-compatible state for prompt-side Step 18."""
    data = {
        "BRANCH_NAME": ctx.branch_name or ctx.branch,
        "PR_NUMBER": "" if ctx.pr_number is None else str(ctx.pr_number),
        "PR_TITLE": ctx.pr_title,
        "PR_URL": ctx.pr_url,
        "ISSUE_NUMBER": ctx.issue_number or ctx.issue,
        "REPO": ctx.repo,
        "DRAFT": _bool_text(ctx.draft),
        "MERGE": _bool_text(ctx.merge),
        "DEFERRED": _bool_text(ctx.deferred),
        "REPO_UNAVAILABLE": _bool_text(ctx.repo_unavailable),
        "PR_CLOSED": _bool_text(ctx.pr_closed),
        "DESIGN_ONLY_DONE": _bool_text(ctx.design_only_done),
        "BAIL_NEEDS_USER_INPUT": _bool_text(ctx.bail_needs_user_input),
        "STALL_TRACKING": _bool_text(ctx.stall_tracking),
        "STALL_STEP": ctx.stall_step,
        "DONE_RENAME_APPLIED": _bool_text(ctx.done_rename_applied),
        "RUN_ID": ctx.run_id,
        "EXPECTED_SESSION_ID": ctx.expected_session_id,
        "EXPECTED_TMPDIR_BASENAME_PREFIX": ctx.expected_tmpdir_basename_prefix,
        "NO_LOGS_COMMIT": _bool_text(ctx.no_logs_commit),
        "FORKED_TARGET": _bool_text(ctx.forked_target or ctx.forked),
        "MERGE_RESULT": ctx.merge_result,
    }
    for key, value in data.items():
        if "\n" in str(value) or "\r" in str(value):
            msg = f"finalize-state value for {key} contains a newline"
            raise ShipError(msg)
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    _ = tmp.write_text("".join(f"{key}={value}\n" for key, value in data.items()), encoding="utf-8")
    _ = tmp.replace(target)
