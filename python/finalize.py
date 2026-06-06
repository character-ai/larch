"""Post-review finalize phases for the ship-pr Python driver."""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
from contextlib import suppress
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import config
import git
import logging_util
import retry
import run_logs
import tracking_issue
from errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
from outcomes import Outcome
from proc import CommandResult, Runner
from run_context import RunContext

POSTBUMP_CHECKPOINT_MAX_BYTES = 64
LS_REMOTE_NOT_FOUND_RC = 2


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


def _bool_text(value: object) -> str:
    return "true" if value else "false"


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
    ok: bool
    status: str = "ok"
    detail: str = ""
    branch: str = ""


def postbump_preflight(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> PostbumpPreflight:
    repo_root = runner.run(["git", "rev-parse", "--show-toplevel"], cwd=cwd)
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


def _remote_head_oid(runner: Runner, remote: str, branch: str, *, cwd: str | None) -> str:
    remote_result = runner.run(
        ["git", "ls-remote", "--exit-code", "--heads", remote, branch],
        cwd=cwd,
    )
    if remote_result.returncode != 0:
        return ""
    fields = remote_result.stdout.split()
    return fields[0] if fields else ""


def _retry_fetch(runner: Runner, remote: str, ref: str, *, cwd: str | None) -> bool:
    def attempt() -> tuple[CommandResult, int, str]:
        result = git.fetch(runner, remote, ref, cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    return retry.with_transient_retry(attempt).last_returncode == 0


def _rebase_no_push(
    runner: Runner,
    *,
    base_remote: str,
    cwd: str | None,
) -> str:
    if not _retry_fetch(runner, base_remote, "main", cwd=cwd):
        return "failed"
    base = f"{base_remote}/main"
    if git.is_ancestor(runner, base, "HEAD", cwd=cwd):
        return "already-fresh"
    result = git.rebase(runner, base, cwd=cwd)
    if result.returncode == 0:
        return "rebased"
    _ = git.rebase(runner, "--abort", cwd=cwd)
    return "failed"


def _remote_branch_state(runner: Runner, branch: str, *, cwd: str | None) -> str:
    def attempt() -> tuple[CommandResult, int, str]:
        result = runner.run(["git", "ls-remote", "--exit-code", "--heads", "origin", branch], cwd=cwd)
        return result, result.returncode, result.stdout + result.stderr

    result = retry.with_transient_retry(attempt).value
    if result.returncode == 0:
        return "present"
    if result.returncode == LS_REMOTE_NOT_FOUND_RC:
        return "absent"
    return "error"


@dataclass(frozen=True)
class LocalCleanupResult:
    cleanup_success: bool
    current_branch: str
    branch_deleted: bool


def _numeric_stdout(result: CommandResult) -> int:
    text = result.stdout.strip() or "0"
    return int(text) if text.isdigit() else 0


def _local_cleanup(
    runner: Runner,
    branch: str,
    *,
    cwd: str | None,
) -> LocalCleanupResult:
    checkout = runner.run(["git", "checkout", "main"], cwd=cwd)
    if checkout.returncode != 0:
        current = git.try_current_branch(runner, cwd=cwd) or "unknown"
        return LocalCleanupResult(cleanup_success=False, current_branch=current, branch_deleted=False)
    current = "main"
    pre_fetch_sha = git.try_rev_parse(runner, "origin/main", cwd=cwd) or "origin/main"
    _ = _retry_fetch(runner, "origin", "main", cwd=cwd)
    ahead = _numeric_stdout(runner.run(["git", "rev-list", "--count", "origin/main..HEAD"], cwd=cwd))
    if ahead > 0:
        subjects = runner.run(["git", "log", "origin/main..HEAD", "--format=%s"], cwd=cwd)
        subject_lines = [line for line in subjects.stdout.splitlines() if line]
        all_flushes = bool(subject_lines) and subjects.returncode == 0 and all(
            line.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX) for line in subject_lines
        )
        diff = runner.run(["git", "diff", "--name-only", pre_fetch_sha, "HEAD"], cwd=cwd)
        diff_lines = [line for line in diff.stdout.splitlines() if line]
        larch_only = bool(diff_lines) and diff.returncode == 0 and all(
            line.startswith("larch-logs/") for line in diff_lines
        )
        if all_flushes and larch_only:
            _ = runner.run(["git", "reset", "--hard", "origin/main"], cwd=cwd)
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
        return LocalCleanupResult(cleanup_success=True, current_branch=current, branch_deleted=False)
    deleted = runner.run(["git", "branch", "-D", "--", branch], cwd=cwd).returncode == 0
    return LocalCleanupResult(cleanup_success=True, current_branch=current, branch_deleted=deleted)


def postbump(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
) -> FinalizeResult:
    """Rebase and force-push before PR creation."""
    try:
        preflight = postbump_preflight(runner, ctx, cwd=cwd)
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
        rebase_status = _rebase_no_push(runner, base_remote=base_remote, cwd=cwd)
        if rebase_status == "failed":
            return FinalizeResult(
                Outcome.STALLED,
                "rebase-failed",
                "rebase failed",
                rebase_status="failed",
                force_push_status="absent",
                log_write_status="skipped",
            )
        if ctx.repo_unavailable:
            return FinalizeResult(
                Outcome.OK,
                "ok",
                rebase_status=rebase_status,
                force_push_status="skipped-repo-unavailable",
                log_write_status="skipped",
            )
        remote_state = _remote_branch_state(runner, branch, cwd=cwd)
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
        remote_tip = _remote_head_oid(runner, "origin", branch, cwd=cwd)
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

    cleanup = _local_cleanup(runner, branch, cwd=cwd)
    cleanup_status = "success" if cleanup.cleanup_success else "partial"

    expected_title = ctx.pr_title or ""
    expected_with_number = expected_title
    if ctx.pr_number is not None and expected_title:
        expected_with_number = f"{expected_title} (#{ctx.pr_number})"
    actual = git.log_subject(runner, "HEAD", cwd=cwd)
    suffix = f"(#{ctx.pr_number})" if ctx.pr_number is not None else ""
    title_ok = bool(
        expected_title
        and (
            actual in (expected_title, expected_with_number)
            or actual.startswith(expected_with_number)
            or (suffix and suffix in actual)
        )
    )
    verify_status = "verified" if title_ok else "unexpected"
    return FinalizeResult(
        Outcome.OK,
        "ok",
        local_cleanup_status=cleanup_status,
        verify_main_status=verify_status,
        branch_deleted=cleanup.branch_deleted,
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
        if state == "stalled" and str(data.get("state", "")).upper() != "OPEN":
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


def _teardown_log_flush(runner: Runner, ctx: RunContext, *, cwd: str | None) -> bool:
    run_id = run_logs.effective_run_id(ctx)
    if not run_id or ctx.repo_unavailable:
        return True
    run_dir = Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id
    writer = logging_util.BreadcrumbWriter()
    try:
        run_dir.mkdir(parents=True, exist_ok=True)
        run_logs.render_execution_issues_batch(
            ctx,
            run_dir,
            step_label="teardown",
            source_label="execution-issues.md teardown safety-net",
        )
    except (OSError, ShipError) as exc:
        writer.emit(f"teardown log flush: execution-issues safety net failed: {exc}", quiet=False)
    try:
        recovery = run_logs.load_or_recover_manifest_checked(ctx)
    except (OSError, ShipError) as exc:
        writer.emit(f"teardown log flush: manifest recovery failed: {exc}", quiet=False)
        recovery = run_logs.ManifestRecovery(
            run_logs.Manifest(status=config.MANIFEST_STATUS_PARTIAL, version="1", run_id=run_id, steps_ran={}),
            recovery_ok=False,
        )
    if recovery.recovery_ok and ctx.stall_tracking:
        try:
            _ = run_logs.update_manifest(
                ctx,
                stalled_at_step=ctx.stall_step or "unknown",
            )
        except (OSError, ShipError) as exc:
            writer.emit(f"teardown log flush: stalled manifest update failed: {exc}", quiet=False)
            recovery = run_logs.ManifestRecovery(recovery.manifest, recovery_ok=False)
    post_merge_sentinel = Path(ctx.tmpdir) / "post-merge-sentinel"
    if not ctx.no_logs_commit and not post_merge_sentinel.exists():
        branch = git.try_current_branch(runner, cwd=cwd) or ""
        if branch not in {"main", "master"}:
            try:
                commit = run_logs.commit_larch_logs(
                    runner,
                    ctx,
                    Path(ctx.tmpdir) / "larch-logs",
                    cwd=cwd,
                )
                if commit.returncode != 0:
                    writer.emit("teardown log flush: larch-log commit failed", quiet=False)
                    recovery = run_logs.ManifestRecovery(recovery.manifest, recovery_ok=False)
            except (OSError, ShipError) as exc:
                writer.emit(f"teardown log flush: larch-log commit failed: {exc}", quiet=False)
                recovery = run_logs.ManifestRecovery(recovery.manifest, recovery_ok=False)
    return recovery.recovery_ok


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
    if run_logs.effective_run_id(ctx):
        _ = _teardown_log_flush(runner, ctx, cwd=cwd)
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
    if tmpdir.exists() and _cleanup_target_ok(ctx, tmpdir, cwd=cwd):
        _ = kill_session_background_processes(runner, ctx)
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


def cache_sessions_root() -> Path:
    xdg = os.environ.get("XDG_CACHE_HOME", "")
    root = Path(xdg) if xdg and Path(xdg).is_absolute() else Path.home() / ".cache"
    return root / "larch" / "sessions"


_FINALIZE_KEY_RE = re.compile(r"^[A-Z_][A-Z0-9_]*$")



def read_finalize_state(path: str | Path) -> dict[str, str]:
    target = Path(path)
    if not target.is_file():
        return {}
    data: dict[str, str] = {}
    for line in target.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        if not _FINALIZE_KEY_RE.match(key):
            continue
        try:
            parsed = shlex.split(value, posix=True)
        except ValueError:
            parsed = [value]
        data[key] = parsed[0] if len(parsed) == 1 else value
    for key, value in data.items():
        if "\n" in value or "\r" in value:
            msg = f"finalize-state value for {key} contains a newline"
            raise ShipError(msg)
    return data


def write_finalize_state_merged(path: str | Path, data: dict[str, str]) -> None:
    for key, value in data.items():
        if not _FINALIZE_KEY_RE.match(key):
            msg = f"invalid finalize-state key: {key}"
            raise ShipError(msg)
        if "\n" in str(value) or "\r" in str(value):
            msg = f"finalize-state value for {key} contains a newline"
            raise ShipError(msg)
    target = Path(path)
    _write_finalize_text_safely(
        target,
        "".join(f"{key}={data[key]}\n" for key in sorted(data)),
    )


def _write_finalize_text_safely(target: Path, text: str) -> None:
    if target.is_symlink():
        raise ShipError(f"refusing to write symlinked finalize-state path: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(target.suffix + ".tmp")
    if tmp.is_symlink():
        raise ShipError(f"refusing to write symlinked finalize-state temp path: {tmp}")
    with suppress(FileNotFoundError):
        tmp.unlink()
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(tmp, flags, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = None
            _ = handle.write(text)
        if target.is_symlink():
            raise ShipError(f"refusing to replace symlinked finalize-state path: {target}")
        _ = tmp.replace(target)
    finally:
        if fd is not None:
            os.close(fd)
        with suppress(OSError):
            if tmp.exists() and not tmp.is_symlink():
                tmp.unlink()


def kill_session_background_processes(runner: Runner, ctx: RunContext) -> bool:
    tmpdir = ctx.tmpdir
    if not tmpdir:
        return False
    current = runner.run(["sh", "-c", "printf '%s %s' $$ ${PPID:-}"])
    skip = {pid for pid in current.stdout.split() if pid.isdigit()}
    physical = ""
    try:
        physical = str(Path(tmpdir).resolve(strict=False))
    except OSError:
        physical = ""
    script = (
        "ps -A -o pid= -o args= | "
        'awk -v needle="$1" -v physical="$2" '
        "'index($0, needle)>0 || (physical != \"\" && physical != needle && index($0, physical)>0) {print $1}'"
    )
    result = runner.run(["sh", "-c", script, "sh", tmpdir, physical])
    killed = False
    for raw in result.stdout.splitlines():
        pid = raw.strip()
        if not pid or pid in skip:
            continue
        term = runner.run(["kill", "-TERM", pid])
        killed = killed or term.returncode == 0
    return killed


def _cleanup_target_ok(ctx: RunContext, tmpdir: Path, *, cwd: str | None = None) -> bool:
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
    _write_finalize_text_safely(
        target,
        "".join(f"{key}={value}\n" for key, value in data.items()),
    )
