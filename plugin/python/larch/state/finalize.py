"""Post-review finalize phases for the ship-pr Python driver."""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import shutil
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from larch.core import config, process_identity
from larch import io as larch_io
from larch.bgjob import registry as bgjob_registry
from larch.report import progress_file
from larch.git import gh
from larch.git import git
from larch.core import logging_util
from larch.core import proc
from larch.core import retry
from larch.core import rust_runtime
from larch.core.repo_roots import RepoRootProbeOptions, repo_root_probe
from larch.report import run_log_manifest
from larch.state import session_env
from larch.issue import tracking_issue
from larch.implement import scope_disposition
from larch.errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from larch.outcomes import Outcome
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext

POSTBUMP_CHECKPOINT_MAX_BYTES = 64
LS_REMOTE_NOT_FOUND_RC = 2
_TITLE_PR_SUFFIX_RE = re.compile(r"\s+\(#([0-9]+)\)$")
_SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+$")


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
    rebase_status: str = ""
    force_push_status: str = ""
    log_write_status: str = ""
    branch_deleted: bool = False
    issue_url: str = ""
    conflict_files: str = ""


def _bool_text(value: object) -> str:
    return "true" if value else "false"


def _title_matches(
    *,
    actual: str,
    expected: str,
    pr_number: object | None = None,
    allow_plain_prefix: bool = False,
    suffix_match: str = "contains",
) -> bool:
    raw_expected = expected
    match = _TITLE_PR_SUFFIX_RE.search(raw_expected)
    expected_number = match.group(1) if match else ""
    normalized_expected = raw_expected[: match.start()].rstrip() if match else raw_expected
    if not normalized_expected:
        return False
    if pr_number is not None:
        suffix_number = str(pr_number)
    elif allow_plain_prefix:
        suffix_number = expected_number
    else:
        suffix_number = ""
    suffix = f"(#{suffix_number})" if suffix_number else ""
    numbered_expected = f"{normalized_expected} {suffix}" if suffix else normalized_expected

    if actual == raw_expected:
        return True
    if allow_plain_prefix and actual.startswith(raw_expected):
        return True
    if numbered_expected and (actual == numbered_expected or actual.startswith(numbered_expected)):
        return True
    if suffix:
        if suffix_match == "endswith":
            return actual.endswith(suffix)
        return suffix in actual
    return False


def _result_from_error(exc: Exception, *, status: str = "stalled") -> FinalizeResult:
    if isinstance(exc, TransientNetworkError):
        return FinalizeResult(
            Outcome.TRANSIENT,
            status,
            str(exc),
            rebase_status="skipped-resume",
            force_push_status="absent",
            log_write_status="skipped",
        )
    if isinstance(exc, NeedsUserInput):
        return FinalizeResult(
            Outcome.NEEDS_USER_INPUT,
            status,
            str(exc),
            rebase_status="skipped-resume",
            force_push_status="absent",
            log_write_status="skipped",
        )
    return FinalizeResult(
        Outcome.STALLED,
        status,
        str(exc),
        rebase_status="skipped-resume",
        force_push_status="absent",
        log_write_status="skipped",
    )


@dataclass(frozen=True)
class PostbumpPreflight:
    # Historical name; no version bump occurs — /release owns versions (Phase 1 #3364 retired per-PR bumping).
    ok: bool
    status: str = "ok"
    detail: str = ""
    branch: str = ""


# Historical name; validates branch/cwd before the force-push gate (no bump).
def postbump_preflight(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> PostbumpPreflight:
    repo_root = repo_root_probe(runner=runner, options=RepoRootProbeOptions(runner_cwd=cwd))
    if repo_root.returncode != 0:
        return PostbumpPreflight(ok=False, status="postbump-cwd-not-repo", detail="cwd is not in a repo")
    branch_result = runner.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=cwd)
    if branch_result.returncode != 0:
        branch = None
    else:
        branch = branch_result.stdout.strip() or None
    target = ctx.branch_name or ctx.branch
    if branch is None and branch_result.returncode == 0:
        branch = target
    if not branch or (target and branch != target):
        return PostbumpPreflight(ok=False, status="branch-mismatch", detail="wrong branch", branch=branch or "")
    if branch in {"main", "master"} and not (ctx.forked or ctx.forked_target):
        return PostbumpPreflight(ok=False, status="branch-mismatch", detail="protected branch", branch=branch)
    return PostbumpPreflight(ok=True, branch=branch)


def _postbump_checkpoint_status(ctx: RunContext) -> str:
    # Historical name; checks the force-push-gate sentinel (no bump occurs).
    path = Path(ctx.tmpdir) / ".postbump-phase"
    if not path.exists():
        return "ok"
    try:
        if path.is_symlink() or path.stat().st_size > POSTBUMP_CHECKPOINT_MAX_BYTES:
            return "corrupt"
        text = path.read_text(encoding="utf-8").replace("\r", "").strip()
    except (OSError, UnicodeDecodeError):
        return "corrupt"
    if not text or not text[0].islower() or not all(
        part.islower() or part.isdigit() or part == "-" for part in text
    ):
        return "corrupt"
    if text != "force-push-gate":
        path.unlink(missing_ok=True)
        return "ok"
    path.unlink(missing_ok=True)
    return "ok"


def _remote_head_oid(*, runner: Runner, remote: str, branch: str, cwd: str | None) -> str:
    remote_result = runner.run(
        ["git", "ls-remote", "--exit-code", "--heads", remote, branch],
        cwd=cwd,
    )
    if remote_result.returncode != 0:
        return ""
    fields: list[str] = remote_result.stdout.split()
    return fields[0] if fields else ""


def _retry_fetch(*, runner: Runner, remote: str, ref: str, cwd: str | None) -> bool:
    def attempt() -> tuple[CommandResult, int, str]:
        result = git.fetch(runner, remote, ref, cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    return retry.with_transient_retry(attempt).last_returncode == 0


@dataclass(frozen=True)
class RebaseNoPushResult:
    """Outcome of the pre-PR (postbump) rebase gate.

    ``status`` is one of ``already-fresh`` / ``rebased`` / ``failed``.
    ``conflict_files`` carries the unmerged paths captured before aborting a
    failed rebase so the stall is actionable (issue #5930).
    """

    status: str
    conflict_files: tuple[str, ...] = ()


def _rebase_failed_detail(conflict_files: tuple[str, ...]) -> str:
    if conflict_files:
        return f"rebase failed; conflicts in: {', '.join(conflict_files)}"
    return "rebase failed"


def _rebase_no_push(
    runner: Runner,
    *,
    base_remote: str,
    cwd: str | None,
) -> RebaseNoPushResult:
    if not _retry_fetch(runner=runner, remote=base_remote, ref="main", cwd=cwd):
        return RebaseNoPushResult("failed")
    base = f"{base_remote}/main"
    if git.is_ancestor(runner, base, "HEAD", cwd=cwd):
        return RebaseNoPushResult("already-fresh")
    result = git.rebase(runner, base, cwd=cwd)
    if result.returncode == 0:
        return RebaseNoPushResult("rebased")
    conflict_files = tuple(git.try_unmerged_paths(runner, cwd=cwd))
    if git.rebase_in_progress(runner, cwd=cwd):
        _ = git.rebase(runner, "--abort", cwd=cwd)
    return RebaseNoPushResult("failed", conflict_files=conflict_files)


@dataclass(frozen=True)
class LocalCleanupResult:
    cleanup_success: bool
    current_branch: str
    branch_deleted: bool


def _numeric_stdout(result: CommandResult) -> int:
    text = result.stdout.strip() or "0"
    return int(text) if text.isdigit() else 0


def _local_cleanup(
    *,
    runner: Runner,
    branch: str,
    cwd: str | None,
) -> LocalCleanupResult:
    checkout = runner.run(["git", "checkout", "main"], cwd=cwd)
    if checkout.returncode != 0:
        current = git.try_current_branch(runner, cwd=cwd) or "unknown"
        return LocalCleanupResult(cleanup_success=False, current_branch=current, branch_deleted=False)
    current = "main"
    _ = _retry_fetch(runner=runner, remote="origin", ref="main", cwd=cwd)
    def pull_attempt() -> tuple[CommandResult, int, str]:
        result = runner.run(["git", "pull", "--ff-only", "origin", "main"], cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    pull = retry.with_transient_retry(pull_attempt)
    if pull.last_returncode != 0:
        ahead_after = _numeric_stdout(
            runner.run(["git", "rev-list", "--count", "origin/main..HEAD"], cwd=cwd),
        )
        if ahead_after > 0:
            logging_util.BreadcrumbWriter().emit(
                f"local cleanup: pull failed; local main is ahead of origin/main by {ahead_after} commit(s)",
                quiet=False,
            )
        return LocalCleanupResult(cleanup_success=False, current_branch=current, branch_deleted=False)
    branch_check = runner.run(["git", "check-ref-format", "--branch", branch], cwd=cwd)
    if branch_check.returncode != 0:
        return LocalCleanupResult(cleanup_success=False, current_branch=current, branch_deleted=False)
    branch_ref = runner.run(["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"], cwd=cwd)
    if branch_ref.returncode == 1:
        return LocalCleanupResult(cleanup_success=True, current_branch=current, branch_deleted=False)
    if branch_ref.returncode != 0:
        return LocalCleanupResult(cleanup_success=False, current_branch=current, branch_deleted=False)
    deleted = runner.run(["git", "branch", "-D", "--", branch], cwd=cwd).returncode == 0
    return LocalCleanupResult(cleanup_success=deleted, current_branch=current, branch_deleted=deleted)


def postbump(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> FinalizeResult:
    """Rebase and force-push before PR creation. Name is a historical holdover; /release owns versions."""
    try:
        preflight = postbump_preflight(runner=runner, ctx=ctx, cwd=cwd)
        if not preflight.ok:
            return FinalizeResult(
                Outcome.STALLED,
                preflight.status,
                preflight.detail,
                rebase_status="skipped-resume",
                force_push_status="absent",
                log_write_status="skipped",
            )
        if _postbump_checkpoint_status(ctx) != "ok":
            return FinalizeResult(
                Outcome.STALLED,
                "postbump-state-corrupt",
                "postbump checkpoint corrupt",
                rebase_status="skipped-resume",
                force_push_status="absent",
                log_write_status="skipped",
            )
        branch = preflight.branch
        base_remote = "upstream" if ctx.forked or ctx.forked_target else "origin"
        rebase = _rebase_no_push(runner, base_remote=base_remote, cwd=cwd)
        rebase_status = rebase.status
        if rebase_status == "failed":
            return FinalizeResult(
                Outcome.STALLED,
                "rebase-failed",
                _rebase_failed_detail(rebase.conflict_files),
                rebase_status="failed",
                force_push_status="absent",
                log_write_status="skipped",
                conflict_files=",".join(rebase.conflict_files),
            )
        if ctx.repo_unavailable:
            return FinalizeResult(
                Outcome.OK,
                "ok",
                rebase_status=rebase_status,
                force_push_status="skipped-repo-unavailable",
                log_write_status="skipped",
            )
        remote_state = git.remote_branch_state(runner, branch, cwd=cwd).state
        if remote_state == "absent":
            return FinalizeResult(
                Outcome.OK,
                "ok",
                rebase_status=rebase_status,
                force_push_status="absent",
                log_write_status="skipped",
            )
        if remote_state != "present":
            return FinalizeResult(
                Outcome.STALLED,
                "remote-check-failed",
                "remote branch probe failed",
                rebase_status=rebase_status,
                force_push_status="failed",
                log_write_status="skipped",
            )
        remote_tip = _remote_head_oid(runner=runner, remote="origin", branch=branch, cwd=cwd)
        if not remote_tip:
            remote_tip = git.try_rev_parse(runner, f"origin/{branch}", cwd=cwd)
        if not remote_tip:
            return FinalizeResult(
                Outcome.STALLED,
                "remote-check-failed",
                "remote branch OID unavailable",
                rebase_status=rebase_status,
                force_push_status="failed",
                log_write_status="skipped",
            )
        push_result = git.force_push_recovery(
            runner,
            branch=branch,
            remote="origin",
            expected_remote_oid=remote_tip,
            cwd=cwd,
        )
        if push_result.pushed and push_result.status in {"pushed", "noop_same_ref"}:
            return FinalizeResult(
                Outcome.OK,
                "ok",
                rebase_status=rebase_status,
                force_push_status=push_result.status,
                log_write_status="skipped",
            )
        return FinalizeResult(
            Outcome.STALLED,
            "push-failed",
            push_result.status,
            rebase_status=rebase_status,
            force_push_status="failed",
            log_write_status="skipped",
        )
    except TransientNetworkError as exc:
        return _result_from_error(exc, status="rebase-failed")
    except NeedsUserInput as exc:
        return _result_from_error(exc, status="needs-user-input")
    except Stalled as exc:
        detail = str(exc).lower()
        if "force" in detail or "push" in detail:
            status = "push-failed"
        elif "remote" in detail:
            status = "remote-check-failed"
        else:
            status = "rebase-failed"
        return _result_from_error(exc, status=status)
    except ShipError as exc:
        detail = str(exc).lower()
        status = "remote-check-failed" if "remote" in detail else "rebase-failed"
        return _result_from_error(exc, status=status)


def postmerge(
    *,
    runner: Runner,
    ctx: RunContext,
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

    cleanup = _local_cleanup(runner=runner, branch=branch, cwd=cwd)
    cleanup_status = "success" if cleanup.cleanup_success else "partial"
    if not cleanup.cleanup_success:
        return FinalizeResult(
            Outcome.STALLED,
            "local-cleanup-failed",
            f"failed to delete local branch {branch}",
            local_cleanup_status=cleanup_status,
            branch_deleted=cleanup.branch_deleted,
        )

    expected_title = ctx.pr_title or ""
    actual = git.log_subject(runner, "HEAD", cwd=cwd)
    title_ok = _title_matches(actual=actual, expected=expected_title, pr_number=ctx.pr_number)
    verify_status = "verified" if title_ok else "unexpected"
    return FinalizeResult(
        Outcome.OK,
        "ok",
        local_cleanup_status=cleanup_status,
        verify_main_status=verify_status,
        branch_deleted=cleanup.branch_deleted,
    )


def _rename_issue(
    *,
    runner: Runner,
    ctx: RunContext,
    state: str,
    cwd: str | None,
) -> str:
    issue = ctx.issue_number or ctx.issue
    if not issue or ctx.repo_unavailable:
        return "skipped"
    result = gh.issue_view_field_read(runner, str(issue), "title,state", repo=ctx.repo, cwd=cwd)
    if result.returncode != 0:
        return "failed"
    current = ""
    issue_state = ""
    try:
        parsed: object = json.loads(result.stdout or "{}")
        if isinstance(parsed, dict):
            data = cast("dict[str, object]", parsed)
            title = data.get("title")
            if isinstance(title, str) and title.strip():
                current = title
                issue_state = str(data.get("state", ""))
    except json.JSONDecodeError:
        pass
    if not current:
        return "failed"
    if state == "stalled" and issue_state.upper() != "OPEN":
        return "skipped"
    try:
        if ctx.run_id and current.startswith(
            config.TRACKING_ISSUE_PREFIX_BY_STATE["implementing"]
        ):
            _ = tracking_issue.rename_terminal_with_lease(
                runner,
                state,
                run=tracking_issue.ImplementationLeaseRun(
                    issue=issue, repo=ctx.repo, run_id=ctx.run_id, cwd=cwd
                ),
            )
        else:
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
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
) -> str:
    status = git.status_porcelain(runner, cwd=cwd)
    if status.returncode != 0:
        return "git-status-failed"
    if not status.stdout.strip():
        return ""
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    label = f"larch-stalled-{ctx.issue_number or 'unknown'}-{ctx.stall_step or 'unknown'}-{timestamp}"
    pushed = runner.run(["git", "stash", "push", "-u", "-m", label], cwd=cwd)
    if pushed.returncode != 0:
        return "git-stash-failed"
    listed = runner.run(["git", "stash", "list", "--format=%gD %gs"], cwd=cwd)
    if listed.returncode != 0:
        return "git-stash-list-failed"
    for line in listed.stdout.splitlines():
        if label in line:
            return line.split()[0]
    return ""


def _write_stalled_sentinel(
    *,
    runner: Runner,
    ctx: RunContext,
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
    data = {
        "ISSUE_NUMBER": issue or "",
        "ISSUE_URL": issue_url,
        "STALL_STEP": ctx.stall_step or "unknown",
        "STASH_REF": stash_ref,
        "TIMESTAMP": timestamp,
    }
    for key, value in data.items():
        if "\n" in str(value) or "\r" in str(value):
            msg = f"stalled sentinel value for {key} contains a newline"
            raise ShipError(msg)
    content = "".join(f"{key}={value}\n" for key, value in data.items())
    tmp = path.with_suffix(".txt.tmp")
    _ = tmp.write_text(content, encoding="utf-8")
    _ = tmp.replace(path)
    return True


_STALE_LIVE_COVERAGE_MISMATCH = "coverage artifact does not match live repository inputs"


def _is_stale_live_coverage_mismatch(exc: BaseException) -> bool:
    """True only for the canonical post-merge live-fingerprint ShipError."""
    return isinstance(exc, ShipError) and str(exc) == _STALE_LIVE_COVERAGE_MISMATCH


def _teardown_disposition_link_kind(
    *,
    tmpdir: Path | None,
    repo_root: Path,
    manifest_path: Path | None,
    allow_persisted_recovery: bool,
) -> str:
    """Resolve closes/part-of for done-rename; recover from exact stale-live mismatch."""
    try:
        return scope_disposition.disposition_link_kind(
            tmpdir,
            repo_root=repo_root,
            manifest_path=manifest_path,
        )
    except ShipError as exc:
        if not _is_stale_live_coverage_mismatch(exc):
            raise
        if not allow_persisted_recovery:
            raise
        if tmpdir is None:
            raise ShipError(_STALE_LIVE_COVERAGE_MISMATCH) from exc
        logging_util.BreadcrumbWriter().emit(
            "teardown: live coverage no longer matches repository inputs; "
            "using validated persisted disposition",
            quiet=False,
        )
        coverage = scope_disposition.load_coverage(tmpdir)
        if coverage is None:
            raise ShipError(_STALE_LIVE_COVERAGE_MISMATCH) from exc
        record = scope_disposition.load_disposition(tmpdir, coverage=coverage)
        return "part-of" if record and record.disposition == "proceed-partial" else "closes"


def teardown(*, runner: Runner, ctx: RunContext, cwd: str | None = None) -> FinalizeResult:
    """Terminal cleanup; preserves artifacts on stalled runs."""
    tmpdir = Path(ctx.tmpdir)
    persisted_repo_root = progress_file.resolve_persisted_repo_root(tmpdir=tmpdir)
    if persisted_repo_root is None:
        if scope_disposition.load_coverage(tmpdir) is not None:
            raise ShipError("persisted repository root is required for teardown coverage validation")
        persisted_repo_root = Path(cwd).resolve() if cwd else Path.cwd()
    rename_branch = "C"
    rename_status = "skipped"
    if ctx.stall_tracking:
        rename_branch = "A"
        rename_status = _rename_issue(runner=runner, ctx=ctx, state="stalled", cwd=cwd)
    elif not ctx.done_rename_applied and (ctx.pr_number is not None or ctx.design_only_done):
        link_kind = _teardown_disposition_link_kind(
            tmpdir=tmpdir if ctx.tmpdir else None,
            repo_root=persisted_repo_root,
            manifest_path=Path(ctx.manifest_path) if ctx.manifest_path else None,
            allow_persisted_recovery=(tmpdir / "post-merge-sentinel").is_file(),
        )
        if link_kind != "part-of":
            rename_branch = "B"
            rename_status = _rename_issue(runner=runner, ctx=ctx, state="done", cwd=cwd)

    sentinel_detail = ""
    try:
        _ = (tmpdir / ".run-cleaned-up").write_text("", encoding="utf-8")
    except (OSError, ShipError) as exc:
        sentinel_detail = f"run-cleaned-up sentinel write failed: {exc}"
        logging_util.BreadcrumbWriter().emit(
            f"teardown: {sentinel_detail}",
            quiet=False,
        )
    stash_ref = ""
    sentinel_written = False
    teardown_run_id = run_log_manifest.effective_run_id(ctx)
    if teardown_run_id and not bgjob_registry.has_live_entry(repo_root=persisted_repo_root, run_id=teardown_run_id):
        _ = rust_runtime.progress_deactivate(
            runner,
            repo_root=str(persisted_repo_root),
            run_id=teardown_run_id,
            cwd=cwd,
        )
    issue_url = ""
    issue_number = ctx.issue_number or ctx.issue
    if issue_number and not ctx.repo_unavailable:
        url = rust_runtime.issue_info(
            runner,
            issue=str(issue_number),
            field="url",
            repo=ctx.repo or None,
        )
        if url:
            issue_url = url

    if ctx.stall_tracking:
        stash_ref = auto_stash_stalled_changes(runner=runner, ctx=ctx, cwd=cwd)
        sentinel_written = _write_stalled_sentinel(
            runner=runner,
            ctx=ctx,
            stash_ref=stash_ref,
            cwd=cwd,
        )
        return FinalizeResult(
            Outcome.OK,
            "stalled-preserved",
            detail=sentinel_detail,
            rename_branch=rename_branch,
            rename_status=rename_status,
            sentinel_written=sentinel_written,
            stash_ref=stash_ref,
            issue_url=issue_url,
        )

    removed = False
    if tmpdir.exists() and _cleanup_target_ok(ctx=ctx, tmpdir=tmpdir, cwd=cwd):
        _ = kill_session_background_processes(runner=runner, ctx=ctx)
        shutil.rmtree(tmpdir, ignore_errors=True)
        removed = not tmpdir.exists()
    status = "cleaned" if removed else "cleanup-skipped"
    return FinalizeResult(
        Outcome.OK,
        status,
        detail=sentinel_detail,
        rename_branch=rename_branch,
        rename_status=rename_status,
        cleanup_removed=removed,
        issue_url=issue_url,
    )


def cache_sessions_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    root = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".cache"
    return root / "larch" / "sessions"


read_finalize_state = session_env.read_finalize_state
write_finalize_state_merged = session_env.write_finalize_state_merged


def _write_finalize_text_safely(*, target: Path, text: str) -> None:
    try:
        larch_io.secure_atomic_write(target, text)
    except OSError as exc:
        raise ShipError(f"cannot write finalize state: {target}") from exc


def _collect_ancestor_pids(*, runner: Runner, pid: str, max_depth: int = 32) -> set[str]:
    if not pid.isdigit():
        return set()
    ancestors: set[str] = set()
    seen = {pid}
    current = pid
    for _ in range(max_depth):
        result = runner.run(["ps", "-o", "ppid=", "-p", current])
        if result.returncode != 0:
            break
        parent = result.stdout.strip()
        if not parent.isdigit() or parent in {"0", "1"} or parent in seen:
            break
        ancestors.add(parent)
        seen.add(parent)
        current = parent
    return ancestors


def kill_session_background_processes(*, runner: Runner, ctx: RunContext) -> bool:
    tmpdir = ctx.tmpdir
    if not tmpdir:
        return False
    current_pid = str(os.getpid())
    parent_pid = str(os.getppid())
    skip: set[str] = {pid for pid in (current_pid, parent_pid) if pid.isdigit() and pid != "0"}
    live_ancestors = _collect_ancestor_pids(runner=runner, pid=current_pid)
    skip.update(live_ancestors)
    if parent_pid.isdigit() and parent_pid not in {"0", "1"} and parent_pid not in live_ancestors:
        skip.update(_collect_ancestor_pids(runner=runner, pid=parent_pid))
    current = runner.run(["sh", "-c", "printf '%s %s' $$ ${PPID:-}"])
    probe_pids: set[str] = {pid for pid in current.stdout.split() if pid.isdigit()}
    for pid in probe_pids:
        if pid not in skip:
            skip.update(_collect_ancestor_pids(runner=runner, pid=pid))
    skip.update(probe_pids)
    physical = ""
    try:
        physical = str(Path(tmpdir).resolve(strict=False))
    except OSError:
        physical = ""
    script = (
        "ps -A -o pid= -o args= | "
        'awk -v needle="$1" -v physical="$2" '
        "'index($0, needle)>0 || (physical != \"\" && physical != needle && index($0, physical)>0) {print $0}'"
    )
    result = runner.run(["sh", "-c", script, "sh", tmpdir, physical])
    killed = False
    for raw in result.stdout.splitlines():
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=1)
        pid = parts[0]
        command = parts[1] if len(parts) > 1 else ""
        if not pid or pid in skip:
            continue
        process_identity.append_kill_log(
            path=pathlib.Path(tmpdir) / config.FINALIZE_KILL_LOG_FILE,
            event=process_identity.KillLogEvent(
                event="signal",
                signal="SIGTERM",
                pid=int(pid) if pid.isdigit() else 0,
                pgid=0,
                command=command,
                caller="session kill-background-processes",
                reason="tmpdir-scoped-background-cleanup",
                tmpdir_needle=tmpdir,
                physical_needle=physical,
            ),
        )
        term = runner.run(["kill", "-TERM", pid])
        killed = killed or term.returncode == 0
    return killed


def _cleanup_target_ok(*, ctx: RunContext, tmpdir: Path, cwd: str | None = None) -> bool:
    try:
        resolved = tmpdir.resolve(strict=False)
    except OSError:
        return False
    if ".." in tmpdir.parts:
        return False
    cache_root = cache_sessions_root()
    allowed_roots = (
        Path("/tmp").resolve(strict=False),  # noqa: S108 - parity allowlist for session tmpdirs.
        Path("/private/tmp").resolve(strict=False),
        Path("/var/folders").resolve(strict=False),
        Path("/private/var/folders").resolve(strict=False),
        cache_root.resolve(strict=False),
    )
    if not any(resolved == root or root in resolved.parents for root in allowed_roots):
        return False
    prefix = ctx.expected_tmpdir_basename_prefix
    if not prefix:
        repo = Path(cwd or Path.cwd()).resolve().name or "_"
        prefix = f"claude-implement-{repo[:32]}-"
    if prefix and not tmpdir.name.startswith(prefix):
        session_file = resolved / "session-id"
        if not ctx.expected_session_id or not session_file.is_file():
            return False
        return session_file.read_text(encoding="utf-8").strip() == ctx.expected_session_id
    if ctx.expected_session_id:
        session_file = resolved / "session-id"
        if not session_file.is_file():
            return False
        return session_file.read_text(encoding="utf-8").strip() == ctx.expected_session_id
    return True


def write_finalize_state(*, ctx: RunContext, path: str | Path) -> None:
    """Write finalize state for prompt-side Step 18."""
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
    _write_finalize_text_safely(
        target=target,
        text="".join(f"{key}={value}\n" for key, value in data.items()),
    )


# ---------------------------------------------------------------------------
# C4c CLI surfaces
# ---------------------------------------------------------------------------


class _SubprocessRunner:
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        return proc.run(argv, timeout=timeout, cwd=cwd, env=env, check=check, stdout=stdout, stderr=stderr)


def _emit_finalize_result(result: FinalizeResult, *, subcommand: str = "") -> None:
    print(f"STATUS={result.status}")
    print(f"OUTCOME={result.outcome.value}")
    print(f"FINALIZE_WARNINGS={result.detail}")
    print(f"LOG_WRITE_STATUS={result.log_write_status}")
    print(f"REBASE_STATUS={result.rebase_status}")
    print(f"CONFLICT_FILES={result.conflict_files}")
    print(f"FORCE_PUSH_STATUS={result.force_push_status}")
    print(f"LOCAL_CLEANUP_STATUS={result.local_cleanup_status}")
    print(f"VERIFY_MAIN_STATUS={result.verify_main_status}")
    print(f"RENAME_BRANCH={result.rename_branch}")
    print(f"RENAME_STATUS={result.rename_status}")
    print(f"ISSUE_URL={result.issue_url}")
    print(f"STASH_REF={result.stash_ref}")
    print(f"SENTINEL_WRITTEN={_bool_text(result.sentinel_written)}")
    if subcommand:
        print(f"FINALIZE_SUBCOMMAND={subcommand}")


def _load_state_file_kv(path: Path) -> dict[str, str]:
    return larch_io.read_kvs(
        path,
        duplicate_policy="last",
        skip_comments=True,
        cr_strip="suffix",
    )


def _allowed_finalize_path(path: Path) -> bool:
    try:
        resolved = path.resolve(strict=False)
    except OSError:
        return False
    allowed_roots = (
        Path("/tmp").resolve(strict=False),  # noqa: S108 - parity allowlist for session tmpdirs.
        Path("/private/tmp").resolve(strict=False),
        Path("/var/folders").resolve(strict=False),
        Path("/private/var/folders").resolve(strict=False),
        cache_sessions_root().resolve(strict=False),
    )
    return any(resolved == root or root in resolved.parents for root in allowed_roots)


def _load_state_file_checked(path: Path) -> dict[str, str]:
    if not _allowed_finalize_path(path):
        raise ValueError("--state-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root")
    if not path.is_file() or not os.access(path, os.R_OK):
        raise ValueError("--state-file must exist and be readable")
    rows: list[str] = []
    for line_no, line in enumerate(larch_io.read_text(path, errors="replace").splitlines(), start=1):
        if not line or line.startswith("#"):
            continue
        if not re.match(r"^[A-Z_][A-Z0-9_]*=", line):
            raise ValueError(f"malformed state-file line {line_no}")
        rows.append(line)
    parsed = larch_io.parse_kv(
        "\n".join(rows),
        duplicate_policy="all",
        key_pattern=r"[A-Z_][A-Z0-9_]*",
    )
    duplicates = [key for key, values in parsed.items() if len(values) != 1]
    if duplicates:
        raise ValueError(f"duplicate state-file key: {duplicates[0]}")
    return {key: values[0] for key, values in parsed.items()}


def _require_state_keys(*, data: Mapping[str, str], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key not in data:
            raise ValueError(f"state-file missing required key: {key}")


def _require_bool_state(*, data: Mapping[str, str], keys: tuple[str, ...]) -> None:
    for key in keys:
        value = data.get(key, "")
        if value not in {"true", "false"}:
            raise ValueError(f"state-file key {key} must be true or false")


_COMMON_REQUIRED_KEYS = (
    *session_env.FINALIZE_STATE_CORE_KEYS,
    "DONE_RENAME_APPLIED",
)
_COMMON_BOOL_KEYS = (
    "DRAFT",
    "MERGE",
    "DEFERRED",
    "REPO_UNAVAILABLE",
    "PR_CLOSED",
    "DESIGN_ONLY_DONE",
    "BAIL_NEEDS_USER_INPUT",
    "STALL_TRACKING",
    "DONE_RENAME_APPLIED",
)
_POSTBUMP_REQUIRED_KEYS = (
    "BRANCH_NAME",
    "ISSUE_NUMBER",
    "PR_TITLE",
    "REPO",
    "REPO_UNAVAILABLE",
    "FORKED_TARGET",
    "BUMP_TYPE",
    "NEW_VERSION",
)
_POSTBUMP_BOOL_KEYS = ("FORKED_TARGET", "REPO_UNAVAILABLE")


def _validate_finalize_cli_args(
    *,
    phase: str,
    state_file: str,
    implement_tmpdir: str = "",
    final_bail_reason_file: str = "",
) -> None:
    if not state_file:
        raise ValueError("--state-file is required")
    state_path = Path(state_file)
    data = _load_state_file_checked(state_path)
    if phase in {"postbump", "teardown"}:
        if not implement_tmpdir:
            raise ValueError("--implement-tmpdir is required")
        tmpdir_path = Path(implement_tmpdir)
        if not _allowed_finalize_path(tmpdir_path):
            raise ValueError("--implement-tmpdir must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root")
        try:
            state_resolved = state_path.resolve(strict=False)
            tmp_resolved = tmpdir_path.resolve(strict=False)
        except OSError as exc:
            raise ValueError("state-file or implement-tmpdir resolution failed") from exc
        if not (state_resolved == tmp_resolved or tmp_resolved in state_resolved.parents):
            raise ValueError("--state-file must live under --implement-tmpdir for teardown")
    if phase == "postmerge":
        if not final_bail_reason_file:
            raise ValueError("--final-bail-reason-file is required")
        bail_path = Path(final_bail_reason_file)
        if not _allowed_finalize_path(bail_path):
            raise ValueError("--final-bail-reason-file must be under /tmp/, /private/tmp/, /var/folders/, or the larch cache sessions root")
    if phase == "postbump":
        _require_state_keys(data=data, keys=_POSTBUMP_REQUIRED_KEYS)
        _require_bool_state(data=data, keys=_POSTBUMP_BOOL_KEYS)
        if data.get("BUMP_TYPE") not in {"MAJOR", "MINOR", "PATCH", "NONE"}:
            raise ValueError("state-file key BUMP_TYPE must be one of MAJOR, MINOR, PATCH, NONE")
        branch = data.get("BRANCH_NAME", "")
        if not branch:
            raise ValueError("state-file key BRANCH_NAME must be non-empty for postbump")
        if branch in {"main", "master"} and data.get("FORKED_TARGET") != "true":
            raise ValueError("state-file key BRANCH_NAME must not be main or master")
        bump_type = data.get("BUMP_TYPE", "")
        new_version = data.get("NEW_VERSION", "")
        if bump_type != "NONE" and not new_version:
            raise ValueError("state-file key NEW_VERSION must be non-empty when BUMP_TYPE is not NONE")
        if bump_type != "NONE" and not _SEMVER_RE.match(new_version):
            raise ValueError("state-file key NEW_VERSION must be semver when BUMP_TYPE is not NONE")
    else:
        _require_state_keys(data=data, keys=_COMMON_REQUIRED_KEYS)
        _require_bool_state(data=data, keys=_COMMON_BOOL_KEYS)


def _finalize_usage_error(message: str) -> int:
    print(f"implement-finalize: {message}", file=sys.stderr)
    return 2


def _ctx_from_tmpdir(tmpdir: str) -> RunContext:
    env = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = tmpdir
    state = Path(tmpdir) / "finalize-state.sh"
    if state.is_file():
        env["SHIP_PR_STATE_FILE"] = str(state)
        for key, value in larch_io.read_kvs(
            state,
            duplicate_policy="last",
            cr_strip="suffix",
        ).items():
            _ = env.setdefault(key, value)
    return RunContext.from_env(env=env)


def _ctx_from_state_file(
    state_file: str,
    *,
    implement_tmpdir: str | None = None,
    final_bail_reason_file: str | None = None,
) -> RunContext:
    env = dict(os.environ)
    state_path = Path(state_file)
    env["SHIP_PR_STATE_FILE"] = state_file
    env.update(_load_state_file_kv(state_path))
    tmpdir = implement_tmpdir or env.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir and state_path.parent.is_dir():
        tmpdir = str(state_path.parent)
    if tmpdir:
        env["IMPLEMENT_TMPDIR"] = tmpdir
    if final_bail_reason_file:
        bail_path = Path(final_bail_reason_file)
        if bail_path.is_file():
            bail_text = bail_path.read_text(encoding="utf-8", errors="replace").strip()
            if bail_text:
                env["FINAL_BAIL_REASON"] = bail_text.replace("\n", " ")[:1024]
    return RunContext.from_env(env=env)


def implement_finalize_main(*, argv: list[str] | None = None, phase: str = "") -> int:
    parser = argparse.ArgumentParser(prog=f"cli.py implement-finalize {phase}")
    _ = parser.add_argument("--state-file", required=True)
    if phase in {"postbump", "teardown"}:
        _ = parser.add_argument("--implement-tmpdir", required=True)
    else:
        _ = parser.add_argument("--implement-tmpdir", default="")
    if phase == "postmerge":
        _ = parser.add_argument("--final-bail-reason-file", required=True)
    else:
        _ = parser.add_argument("--final-bail-reason-file", default="")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code or 2)
    try:
        _validate_finalize_cli_args(
            phase=phase,
            state_file=args.state_file,
            implement_tmpdir=args.implement_tmpdir,
            final_bail_reason_file=args.final_bail_reason_file,
        )
    except ValueError as exc:
        return _finalize_usage_error(str(exc))
    ctx = _ctx_from_state_file(
        args.state_file,
        implement_tmpdir=args.implement_tmpdir,
        final_bail_reason_file=args.final_bail_reason_file,
    )
    runner = _SubprocessRunner()
    cwd = str(Path.cwd())
    if phase == "postbump":
        result = postbump(runner=runner, ctx=ctx, cwd=cwd)
    elif phase == "postmerge":
        result = postmerge(runner=runner, ctx=ctx, cwd=cwd)
    elif phase == "teardown":
        result = teardown(runner=runner, ctx=ctx, cwd=cwd)
    else:
        return _finalize_usage_error("unknown phase")
    _emit_finalize_result(result, subcommand=phase)
    return 0


def implement_finalize_postbump_main(argv: list[str] | None = None) -> int:
    return implement_finalize_main(argv=argv, phase="postbump")


def implement_finalize_postmerge_main(argv: list[str] | None = None) -> int:
    return implement_finalize_main(argv=argv, phase="postmerge")


def implement_finalize_teardown_main(argv: list[str] | None = None) -> int:
    return implement_finalize_main(argv=argv, phase="teardown")


def cleanup_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement cleanup")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    tmpdir = Path(args.implement_tmpdir)
    ctx = _ctx_from_tmpdir(str(tmpdir))
    if tmpdir.exists() and _cleanup_target_ok(ctx=ctx, tmpdir=tmpdir, cwd=str(Path.cwd())):
        shutil.rmtree(tmpdir, ignore_errors=True)
        cleaned = not tmpdir.exists()
        print(f"CLEANED={_bool_text(cleaned)}")
        if not cleaned:
            print("ERROR=cleanup-tmpdir failed")
            return 1
        return 0
    print("CLEANED=false")
    print("ERROR=cleanup target rejected")
    return 2
