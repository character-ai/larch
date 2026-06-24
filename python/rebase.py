"""Rebase component: fetch/rebase, conflict resolution, force-push (Phase 3)."""

from __future__ import annotations

import os
import random
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import agents
import coder_delta_guards
import config
import git
import redact
import retry
from errors import PrePushConflictHandoff, ShipError, Stalled, TransientNetworkError
from outcomes import Outcome
from proc import CommandResult, Runner

_redact_outbound = redact.redact_outbound

ConflictLaunchFn = Callable[[str, str], agents.TierAttempt]


@dataclass(frozen=True)
class RebaseResult:
    outcome: Outcome
    rebased: bool
    pushed: bool
    new_version: str | None
    attempts: int
    detail: str


@dataclass(frozen=True)
class RebasePushResult:
    exit_code: int
    skipped_already_pushed: bool = False
    skipped_already_fresh: bool = False
    conflict_files: str = ""
    rebase_error: str = ""
    push_error: str = ""


def _conflict_launch_output_dir(tmpdir: str | None) -> Path:
    if tmpdir:
        return Path(tmpdir) / ".conflict-launch"
    env_tmp = os.environ.get(config.ENV_IMPLEMENT_TMPDIR)
    if env_tmp:
        return Path(env_tmp) / ".conflict-launch"
    msg = _redact_outbound("conflict launch output dir not configured")
    raise Stalled(msg)


def _sync_local_main(
    runner: Runner,
    *,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> None:
    base_target = f"{base_remote}/{base_ref}"
    branch = git.try_current_branch(runner, cwd=cwd)

    if branch == "main":
        result, rc = git.sync_local_main(
            runner,
            base_remote=base_remote,
            base_ref=base_ref,
            cwd=cwd,
        )
        if rc != 0 and result == "refusing to update local 'main' while checked out on main":
            raise Stalled(_redact_outbound(f"cli.py git sync-local-main: {result}"))
        return

    if git.try_rev_parse(runner, "main", cwd=cwd) is not None:
        remote_main = git.try_rev_parse(runner, base_target, cwd=cwd)
        if remote_main is None:
            return  # rebase-only parity; not widened into git.sync_local_main

    result, rc = git.sync_local_main(
        runner,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    )
    if rc != 0 and result == "refusing to update local 'main' while checked out on main":
        raise Stalled(_redact_outbound(f"cli.py git sync-local-main: {result}"))


def _is_empty_or_already_applied_rebase_error(text: str) -> bool:
    lowered = text.lower()
    if "nothing to commit" in lowered:
        return True
    if "no changes" in lowered:
        return True
    return "all merge conflicts were fixed" in lowered


def _abort_rebase(runner: Runner, *, cwd: str | None) -> None:
    _ = git.rebase(runner, "--abort", cwd=cwd)


def _write_handoff_flag(tmpdir: str | None) -> None:
    root = tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR)
    if not root:
        raise Stalled(_redact_outbound("handoff flag tmpdir not configured"))
    flag = Path(root) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    try:
        _ = flag.write_text("", encoding="utf-8")
    except OSError as exc:
        msg = f"cannot write {config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME}"
        raise Stalled(_redact_outbound(msg)) from exc


def _unmerged_paths(runner: Runner, *, cwd: str | None) -> list[str]:
    try:
        return git.unmerged_paths(runner, cwd=cwd)
    except ShipError:
        raise Stalled(_redact_outbound("git diff --diff-filter=U failed")) from None


def _path_has_conflict_markers(path: str, *, cwd: str | None) -> bool:
    root = Path(cwd) if cwd else Path.cwd()
    file_path = root / path
    if not file_path.is_file():
        return False
    try:
        text = file_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return True
    marker_re = re.compile(r"^(<<<<<<<|=======|>>>>>>>)", re.MULTILINE)
    return marker_re.search(text) is not None


def _stage_resolved_conflict_files(
    *,
    runner: Runner,
    conflict_paths: tuple[str, ...] | list[str],
    cwd: str | None,
) -> tuple[list[str], list[str]]:
    """Stage only conflict paths that exist and no longer contain conflict markers."""
    staged: list[str] = []
    still_marked: list[str] = []
    root = Path(cwd) if cwd else Path.cwd()
    for path in conflict_paths:
        if _path_has_conflict_markers(path, cwd=cwd):
            still_marked.append(path)
            continue
        if not (root / path).exists():
            continue
        _ = git.add(runner, path, cwd=cwd)
        staged.append(path)
    return staged, still_marked


def _reset_conflict_paths(
    *,
    runner: Runner,
    conflict_paths: tuple[str, ...] | list[str],
    cwd: str | None,
) -> None:
    for path in conflict_paths:
        _ = git.restore_staged(runner, path, cwd=cwd)
        _ = runner.run(["git", "checkout", "--merge", "--", path], cwd=cwd)


def make_conflict_launch_fn(
    *,
    runner: Runner,
    repo: str,
    run_id: str,
    output_dir: str | Path,
    cwd: str | None = None,
) -> ConflictLaunchFn:
    """Build a fixer launch_fn using ``build_launch_argv`` / ``launch_tier`` parity."""
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    seen_token_records: set[str] = set()

    def launch(tier: str, conflict_csv: str) -> agents.TierAttempt:  # lint-keyword-only: ok constrained by ConflictLaunchFn Callable type
        output = out_root / f"conflict-{tier}.out"
        failure_log = out_root / f"conflict-{tier}.fail.log"
        if tier in {"codex", "cursor"}:
            Path(f"{output}.token-record").unlink(missing_ok=True)
        result = agents.launch_tier(
            runner=runner,
            tier=tier,
            role=config.FIXER_ROLE,
            output=str(output),
            run_id=run_id,
            repo=repo,
            conflict_files=conflict_csv,
            cwd=cwd,
        )
        if tier in {"codex", "cursor"}:
            implement_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR)
            _ = agents.ingest_launcher_token_sidecar(
                runner,
                launcher_stdout=result.stdout + result.stderr,
                output=output,
                tmpdir=implement_tmpdir,
                implement_tmpdir=implement_tmpdir,
                seen=seen_token_records,
                cwd=cwd,
                allow_output_fallback=True,
            )
        launcher_capture = result.stdout + result.stderr
        launcher_exit = agents.resolve_launcher_exit(
            captured_text=launcher_capture,
            output_file=output,
            process_rc=result.returncode,
        )
        failure = agents.classify_launch_failure(
            launcher_exit=launcher_exit,
            sidecar=failure_log,
            tool=tier,
            output_file=output,
        )
        if not launcher_capture.endswith("\n"):
            launcher_capture += "\n"
        launcher_capture += f"LAUNCHER_FAILURE_CLASS={failure.failure_class}\n"
        _ = failure_log.write_text(launcher_capture, encoding="utf-8")
        return agents.TierAttempt(
            tier=tier,
            wrapper_rc=result.returncode,
            launcher_exit=launcher_exit,
            failure=failure,
            failure_log=failure_log,
        )

    return launch


def _resolve_conflicts(
    *,
    runner: Runner,
    launch_fn: ConflictLaunchFn,
    repo: str,
    run_id: str,
    cwd: str | None,
    tmpdir: str | None = None,
    enable_pre_push_handoff: bool = False,
) -> None:
    _ = repo, run_id

    def _handoff_or_stall(conflict_files: tuple[str, ...], detail: str) -> None:  # lint-keyword-only: ok internal nested closure
        if enable_pre_push_handoff and conflict_files:
            _write_handoff_flag(tmpdir)
            raise PrePushConflictHandoff(
                conflict_files=conflict_files,
                resume_phase=config.SHIP_PR_RRR_RESUME_PHASE,
                caller_kind=config.SHIP_PR_PRE_PUSH_CALLER_KIND,
            )
        raise Stalled(_redact_outbound(detail))

    while True:
        unmerged = _unmerged_paths(runner, cwd=cwd)
        if unmerged:
            conflict_csv = ",".join(unmerged)
            baseline_tracked: frozenset[str] = git.tracked_dirty_paths(runner, cwd=cwd)
            baseline_untracked: frozenset[str] = git.untracked_dirty_paths(runner, cwd=cwd)
            baseline_staged: tuple[str, ...] = coder_delta_guards.staged_dirty_paths(runner, cwd=cwd)
            resolved = False
            for index, tier in enumerate(config.FIXER_TIER_ORDER):
                forbidden: tuple[str, ...] = coder_delta_guards.coder_forbidden_paths(runner, cwd=cwd)
                attempt = launch_fn(tier, conflict_csv)
                if (
                    coder_delta_guards.revert_forbidden_paths(
                        runner,
                        cwd=cwd,
                        forbidden=forbidden,
                        baseline_staged=baseline_staged,
                    )
                    > 0
                ):
                    git.paths_delta_revert(
                        runner,
                        baseline_tracked,
                        baseline_untracked,
                        cwd=cwd,
                    )
                    _reset_conflict_paths(runner=runner, conflict_paths=unmerged, cwd=cwd)
                    raise Stalled(_redact_outbound("conflict fixer touched forbidden path"))
                tier_succeeded = attempt.launcher_exit == 0 and attempt.wrapper_rc == 0
                still_marked: list[str] = []
                if tier_succeeded:
                    _, still_marked = _stage_resolved_conflict_files(
                        runner=runner,
                        conflict_paths=unmerged,
                        cwd=cwd,
                    )
                else:
                    _reset_conflict_paths(runner=runner, conflict_paths=unmerged, cwd=cwd)
                unmerged_remaining = _unmerged_paths(runner, cwd=cwd)
                active_paths = unmerged_remaining or unmerged
                markers_remain = bool(still_marked) or any(
                    _path_has_conflict_markers(path, cwd=cwd) for path in active_paths
                )
                if tier_succeeded and not unmerged_remaining and not markers_remain:
                    resolved = True
                    break
                git.paths_delta_revert(runner, baseline_tracked, baseline_untracked, cwd=cwd)
                _reset_conflict_paths(runner=runner, conflict_paths=unmerged, cwd=cwd)
                if not tier_succeeded:
                    failure_class = agents.effective_failure_class(attempt)
                    if index == 0 and attempt.wrapper_rc == 0 and failure_class == "other":
                        _handoff_or_stall(
                            tuple(active_paths),
                            "first fixer could not resolve conflicts",
                        )
            if not resolved:
                remaining_after = tuple(_unmerged_paths(runner, cwd=cwd) or unmerged)
                _handoff_or_stall(
                    remaining_after,
                    "fixer waterfall could not resolve conflicts",
                )

        continue_result = git.rebase_continue(runner, cwd=cwd)
        if continue_result.returncode == 0:
            if _unmerged_paths(runner, cwd=cwd):
                continue
            return

        unmerged_after = _unmerged_paths(runner, cwd=cwd)
        combined = f"{continue_result.stdout}\n{continue_result.stderr}"
        if unmerged_after:
            continue
        if _is_empty_or_already_applied_rebase_error(combined):
            skip_result = git.rebase_skip(runner, cwd=cwd)
            if skip_result.returncode != 0:
                _abort_rebase(runner, cwd=cwd)
                raise Stalled(_redact_outbound("git rebase --skip failed"))
            continue
        _abort_rebase(runner, cwd=cwd)
        raise Stalled(_redact_outbound("rebase --continue failed without unmerged paths"))


def _force_push_branch(
    runner: Runner,
    *,
    cwd: str | None,
    sleep_fn: Callable[[float], None] = time.sleep,
    expected_remote_oid: str | None = None,
) -> CommandResult:
    status = git.status_porcelain(runner, cwd=cwd)
    if status.returncode != 0:
        raise Stalled(_redact_outbound("git status failed before force-push"))
    if status.stdout.strip():
        raise Stalled(_redact_outbound("dirty worktree before force-push"))

    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        raise Stalled(_redact_outbound("not on a named branch before force-push"))

    remote = "origin"
    refspec = branch
    _ = git.fetch(runner, remote, branch, cwd=cwd)

    def _push() -> CommandResult:
        if expected_remote_oid:
            return git.force_push_with_lease_expecting(
                runner,
                remote,
                f"refs/heads/{refspec}",
                expected_remote_oid,
                cwd=cwd,
            )
        return git.force_push_with_lease(runner, remote, refspec, cwd=cwd)

    first = _push()
    if first.returncode == 0:
        return first

    _ = git.fetch(runner, remote, branch, cwd=cwd)
    head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    remote_tip = git.try_rev_parse(runner, f"{remote}/{branch}", cwd=cwd)
    if head and remote_tip and head == remote_tip:
        return CommandResult(first.argv, 0, "", "", first.duration)

    sleep_fn(5)
    second = _push()
    if second.returncode == 0:
        return second
    raise Stalled(_redact_outbound("force-push failed after retry"))


def rebase_and_push(
    *,
    runner: Runner,
    launch_fn: ConflictLaunchFn | None = None,
    base_remote: str = "origin",
    base_ref: str = "main",
    repo: str,
    run_id: str,
    cwd: str | None = None,
    tmpdir: str | None = None,
    rebase_attempt: int = 0,
    max_attempts: int = config.REBASE_MAX_ATTEMPTS,
    defer_push: bool = False,
    allow_conflict_fix: bool = True,
    enable_pre_push_handoff: bool = False,
) -> RebaseResult:
    """Rebase onto base, resolve conflicts, optionally force-push.

    When ``defer_push`` is True, rebase runs locally but force-push is skipped and
    ``RebaseResult.pushed`` is False. ``RebaseResult.new_version`` is always None
    (versioning is handled by the release flow).
    """
    if launch_fn is None:
        launch_fn = make_conflict_launch_fn(
            runner=runner,
            repo=repo,
            run_id=run_id,
            output_dir=_conflict_launch_output_dir(tmpdir),
            cwd=cwd,
        )
    if rebase_attempt >= max_attempts:
        raise Stalled(_redact_outbound("rebase attempt cap exceeded"))

    base_err = git.validate_base_remote_ref(base_remote, base_ref)
    if base_err is not None:
        raise Stalled(_redact_outbound(base_err))

    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        raise Stalled(_redact_outbound("detached HEAD or no current branch"))

    rebased = False

    base_target = f"{base_remote}/{base_ref}"
    fetch_result = git.fetch(runner, base_remote, base_ref, cwd=cwd)
    if fetch_result.returncode != 0:
        combined = f"{fetch_result.stdout}\n{fetch_result.stderr}"
        if retry.is_transient_net_signature(combined):
            raise TransientNetworkError(
                _redact_outbound("fetch failed with transient network signature"),
                result=fetch_result,
            )
        _abort_rebase(runner, cwd=cwd)
        raise Stalled(_redact_outbound("fetch failed"))

    if git.is_ancestor(runner, base_target, "HEAD", cwd=cwd):
        rebased = False
    else:
        rebase_result = git.rebase(runner, base_target, cwd=cwd)
        if rebase_result.returncode == 0:
            rebased = True
        elif _unmerged_paths(runner, cwd=cwd):
            rebased = True
            if not allow_conflict_fix:
                raise Stalled(_redact_outbound("rebase conflicts require manual resolution"))
            _resolve_conflicts(
                runner=runner,
                launch_fn=launch_fn,
                repo=repo,
                run_id=run_id,
                cwd=cwd,
                tmpdir=tmpdir,
                enable_pre_push_handoff=enable_pre_push_handoff,
            )
        else:
            _abort_rebase(runner, cwd=cwd)
            raise Stalled(_redact_outbound("rebase failed without conflicts"))

    _sync_local_main(runner, base_remote=base_remote, base_ref=base_ref, cwd=cwd)

    pushed = False
    if not defer_push:
        _ = _force_push_branch(runner, cwd=cwd)
        pushed = True

    return RebaseResult(
        outcome=Outcome.OK,
        rebased=rebased,
        pushed=pushed,
        new_version=None,
        attempts=rebase_attempt + 1,
        detail="",
    )


def _rebase_push_jitter_sleep(*, attempt: int, sleep_fn: Callable[[float], None], rng: random.Random) -> None:
    base = 1 * (2 ** (attempt - 1))
    jitter = rng.randint(0, base // 2)
    sleep_for = base + jitter - base // 4
    sleep_fn(max(1, sleep_for))


def _rebase_push_force_with_lease(
    runner: Runner,
    *,
    push_remote: str,
    branch: str,
    expected_remote_oid: str,
    cwd: str | None,
    sleep_fn: Callable[[float], None] | None = None,
    rng: random.Random | None = None,
) -> tuple[bool, str]:
    """Three-attempt force-with-lease loop (push rebase parity)."""
    if sleep_fn is None:
        sleep_fn = time.sleep
    if rng is None:
        rng = random.Random()
    lease_arg = f"--force-with-lease=refs/heads/{branch}:{expected_remote_oid}"
    push_max = 3
    last_output = ""
    for push_attempt in range(1, push_max + 1):
        if not git.try_current_branch(runner, cwd=cwd):
            return False, f"Not on a branch (detached HEAD) before push attempt {push_attempt}"
        def attempt_push() -> tuple[CommandResult, int, str]:
            result = runner.run(["git", "push", lease_arg], cwd=cwd)
            return result, result.returncode, result.stdout + result.stderr

        push_result = retry.with_transient_retry(attempt_push).value
        if push_result.returncode == 0:
            return True, ""
        last_output = (push_result.stdout + push_result.stderr).replace("\n", " ").strip()
        _ = _transient_retry_git_result(lambda: git.fetch(runner, push_remote, branch, cwd=cwd))
        local_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
        remote_head = git.try_rev_parse(runner, f"{push_remote}/{branch}", cwd=cwd)
        if local_head and remote_head and local_head == remote_head:
            return True, ""
        if push_attempt < push_max:
            _rebase_push_jitter_sleep(attempt=push_attempt, sleep_fn=sleep_fn, rng=rng)
    return False, last_output


def _transient_retry_git_result(command: Callable[[], CommandResult]) -> CommandResult:
    def attempt() -> tuple[CommandResult, int, str]:
        result = command()
        return result, result.returncode, result.stdout + result.stderr

    return retry.with_transient_retry(attempt).value


def rebase_push(
    runner: Runner,
    *,
    continue_mode: bool = False,
    no_push: bool = False,
    skip_if_pushed: bool = False,
    keep_on_conflict: bool = False,
    base_remote: str = "origin",
    base_ref: str = "main",
    cwd: str | None = None,
) -> RebasePushResult:
    """CLI parity primitive for ``push rebase``."""
    base_err = git.validate_base_remote_ref(base_remote, base_ref)
    if base_err is not None:
        return RebasePushResult(exit_code=3, rebase_error=base_err)
    if skip_if_pushed and not no_push:
        return RebasePushResult(exit_code=3, rebase_error="--skip-if-pushed is only valid with --no-push")
    if skip_if_pushed and continue_mode:
        return RebasePushResult(exit_code=3, rebase_error="--skip-if-pushed cannot be used with --continue")
    if keep_on_conflict and not no_push:
        return RebasePushResult(exit_code=3, rebase_error="--keep-on-conflict is only valid with --no-push")
    if continue_mode and no_push and not keep_on_conflict:
        return RebasePushResult(
            exit_code=3,
            rebase_error="--continue --no-push requires --keep-on-conflict to safely handle nested conflicts",
        )

    if skip_if_pushed:
        branch = git.try_current_branch(runner, cwd=cwd)
        if branch:
            remote = _transient_retry_git_result(
                lambda: runner.run(
                    ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
                    cwd=cwd,
                ),
            )
            if remote.returncode == 0 and remote.stdout.strip():
                return RebasePushResult(exit_code=0, skipped_already_pushed=True)

    base_target = f"{base_remote}/{base_ref}"
    if continue_mode:
        if not git.rebase_in_progress(runner, cwd=cwd):
            return RebasePushResult(exit_code=3, rebase_error="--continue called but no rebase is in progress")
        rebase_result = runner.run(["git", "rebase", "--continue"], cwd=cwd, env={**os.environ, "GIT_EDITOR": "true"})
    else:
        if not git.try_current_branch(runner, cwd=cwd):
            return RebasePushResult(exit_code=3, rebase_error="Not on a branch (detached HEAD)")
        fetch_result = _transient_retry_git_result(lambda: git.fetch(runner, base_remote, base_ref, cwd=cwd))
        if no_push and fetch_result.returncode != 0:
            return RebasePushResult(exit_code=3, rebase_error=f"git fetch {base_remote} {base_ref} failed (network/auth issue)")
        if no_push and git.is_ancestor(runner, base_target, "HEAD", cwd=cwd):
            return RebasePushResult(exit_code=0, skipped_already_fresh=True)
        rebase_result = git.rebase(runner, base_target, cwd=cwd)

    if rebase_result.returncode != 0:
        conflicts = ",".join(git.try_unmerged_paths(runner, cwd=cwd))
        if conflicts:
            if no_push and not keep_on_conflict:
                _abort_rebase(runner, cwd=cwd)
            return RebasePushResult(exit_code=1, conflict_files=conflicts)
        err = (rebase_result.stdout + rebase_result.stderr).replace("\n", " ").strip()
        if not continue_mode:
            _abort_rebase(runner, cwd=cwd)
        return RebasePushResult(exit_code=3, rebase_error=err)

    if no_push:
        return RebasePushResult(exit_code=0)

    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        return RebasePushResult(exit_code=2, push_error="Not on a branch (detached HEAD) before push")
    push_remote = git.resolve_branch_push_remote(runner, branch, cwd=cwd)
    _ = _transient_retry_git_result(lambda: git.fetch(runner, push_remote, branch, cwd=cwd))
    expected_remote_oid = git.try_rev_parse(runner, f"{push_remote}/{branch}", cwd=cwd)
    if expected_remote_oid is None:
        remote_probe = _transient_retry_git_result(
            lambda: runner.run(
                ["git", "ls-remote", "--heads", push_remote, f"refs/heads/{branch}"],
                cwd=cwd,
            ),
        )
        if remote_probe.returncode == 0 and remote_probe.stdout.strip():
            expected_remote_oid = remote_probe.stdout.strip().split()[0]
    pushed, push_error = _rebase_push_force_with_lease(
        runner,
        push_remote=push_remote,
        branch=branch,
        expected_remote_oid=expected_remote_oid or "",
        cwd=cwd,
    )
    if pushed:
        return RebasePushResult(exit_code=0)
    return RebasePushResult(exit_code=2, push_error=push_error)
