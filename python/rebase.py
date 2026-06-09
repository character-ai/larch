"""Rebase component: fetch/rebase, conflict resolution, force-push (Phase 3)."""

from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import agents
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
    branch = git.try_current_branch(runner, cwd=cwd)
    if branch == "main":
        raise Stalled(
            _redact_outbound(
                "git-sync-local-main.sh: refusing to update local 'main' "
                "while checked out on main",
            ),
        )
    if git.try_rev_parse(runner, "main", cwd=cwd) is None:
        return
    base_target = f"{base_remote}/{base_ref}"
    local_main = git.try_rev_parse(runner, "main", cwd=cwd)
    remote_main = git.try_rev_parse(runner, base_target, cwd=cwd)
    if local_main and remote_main and local_main == remote_main:
        return
    if remote_main is None:
        return
    _ = git.branch_force(runner, "main", base_target, cwd=cwd)


def _is_empty_or_already_applied_rebase_error(text: str) -> bool:
    lowered = text.lower()
    if "nothing to commit" in lowered:
        return True
    if "no changes" in lowered:
        return True
    return "all merge conflicts were fixed" in lowered


def _abort_rebase(runner: Runner, *, cwd: str | None) -> None:
    _ = git.rebase(runner, "--abort", cwd=cwd)


def _is_plugin_json_path(path: str) -> bool:
    return path == config.PLUGIN_JSON_PATH or path.endswith(
        f"/{config.PLUGIN_JSON_PATH}",
    )


def _larch_bump_files() -> frozenset[str]:
    raw = os.environ.get(config.ENV_LARCH_VERSION_FILES, "")
    if not raw:
        raw = os.environ.get(config.ENV_LARCH_BUMP_FILES, "")
    return frozenset(segment.strip() for segment in raw.split(os.pathsep) if segment.strip())


def _is_bump_path(path: str) -> bool:
    base = Path(path).name
    if _is_plugin_json_path(path):
        return True
    if base in ("version.go", "go.sum"):
        return True
    return path in _larch_bump_files()


def _conflicts_are_non_bump_only(paths: tuple[str, ...]) -> bool:
    return bool(paths) and not any(_is_bump_path(path) for path in paths)


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


def _deterministic_prepass(
    runner: Runner,
    paths: list[str],
    *,
    cwd: str | None,
) -> list[str]:
    remaining: list[str] = []
    for path in paths:
        base = Path(path).name
        if base == "plugin.json" and _is_plugin_json_path(path):
            result = git.checkout_ours(runner, path, cwd=cwd)
            if result.returncode == 0:
                _ = git.add(runner, path, cwd=cwd)
            else:
                remaining.append(path)
            continue
        if base in ("version.go", "go.sum"):
            result = git.checkout_ours(runner, path, cwd=cwd)
            if result.returncode == 0:
                _ = git.add(runner, path, cwd=cwd)
            else:
                remaining.append(path)
            continue
        remaining.append(path)
    return remaining


def _unmerged_paths(runner: Runner, *, cwd: str | None) -> list[str]:
    try:
        return git.unmerged_paths(runner, cwd=cwd)
    except ShipError:
        raise Stalled(_redact_outbound("git diff --diff-filter=U failed")) from None


def make_conflict_launch_fn(
    runner: Runner,
    *,
    repo: str,
    run_id: str,
    output_dir: str | Path,
    cwd: str | None = None,
) -> ConflictLaunchFn:
    """Build a fixer launch_fn using ``build_launch_argv`` / ``launch_tier`` parity."""
    out_root = Path(output_dir)
    out_root.mkdir(parents=True, exist_ok=True)

    def launch(tier: str, conflict_csv: str) -> agents.TierAttempt:
        output = out_root / f"conflict-{tier}.out"
        failure_log = out_root / f"conflict-{tier}.fail.log"
        result = agents.launch_tier(
            runner,
            tier,
            role=config.FIXER_ROLE,
            output=str(output),
            run_id=run_id,
            repo=repo,
            conflict_files=conflict_csv,
            cwd=cwd,
        )
        launcher_exit = agents.parse_launcher_exit_text(result.stdout)
        failure = agents.classify_launch_failure(
            launcher_exit,
            failure_log if failure_log.is_file() else None,
            tool=tier,
            output_file=output,
        )
        flog: str | Path | None = failure_log if failure_log.is_file() else None
        return agents.TierAttempt(
            tier=tier,
            wrapper_rc=result.returncode,
            launcher_exit=launcher_exit,
            failure=failure,
            failure_log=flog,
        )

    return launch


def _resolve_conflicts(
    runner: Runner,
    launch_fn: ConflictLaunchFn,
    *,
    repo: str,
    run_id: str,
    cwd: str | None,
    tmpdir: str | None = None,
    enable_pre_push_handoff: bool = False,
) -> None:
    _ = repo, run_id
    while True:
        unmerged = _unmerged_paths(runner, cwd=cwd)
        if unmerged:
            remaining = _deterministic_prepass(runner, unmerged, cwd=cwd)
            if remaining:
                conflict_csv = ",".join(remaining)

                def _tier_launch(tier: str, csv: str = conflict_csv) -> agents.TierAttempt:
                    return launch_fn(tier, csv)

                waterfall = agents.run_waterfall(
                    config.FIXER_TIER_ORDER,
                    _tier_launch,
                    runner=runner,
                    cwd=cwd,
                )
                if waterfall.winning_tier is None:
                    conflict_files = tuple(remaining)
                    if enable_pre_push_handoff and _conflicts_are_non_bump_only(conflict_files):
                        _write_handoff_flag(tmpdir)
                        raise PrePushConflictHandoff(
                            conflict_files=conflict_files,
                            resume_phase=config.SHIP_PR_RRR_RESUME_PHASE,
                            caller_kind=config.SHIP_PR_PRE_PUSH_CALLER_KIND,
                        )
                    raise Stalled(
                        _redact_outbound("fixer waterfall could not resolve conflicts"),
                    )
                if _unmerged_paths(runner, cwd=cwd):
                    raise Stalled(_redact_outbound("conflicts remain after fixer waterfall"))

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
    runner: Runner,
    launch_fn: ConflictLaunchFn | None = None,
    *,
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
            runner,
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
                runner,
                launch_fn,
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
    """CLI parity primitive for ``rebase-push.sh``."""
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
            remote = runner.run(
                ["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
                cwd=cwd,
            )
            if remote.returncode == 0 and remote.stdout.strip():
                return RebasePushResult(exit_code=0, skipped_already_pushed=True)

    base_target = f"{base_remote}/{base_ref}"
    if continue_mode:
        git_dir = runner.run(["git", "rev-parse", "--git-dir"], cwd=cwd)
        if git_dir.returncode != 0 or not git_dir.stdout.strip():
            return RebasePushResult(exit_code=3, rebase_error="--continue called but no rebase is in progress")
        rebase_result = runner.run(["git", "rebase", "--continue"], cwd=cwd, env={**os.environ, "GIT_EDITOR": "true"})
    else:
        if not git.try_current_branch(runner, cwd=cwd):
            return RebasePushResult(exit_code=3, rebase_error="Not on a branch (detached HEAD)")
        fetch_result = git.fetch(runner, base_remote, base_ref, cwd=cwd)
        if no_push and fetch_result.returncode != 0:
            return RebasePushResult(exit_code=3, rebase_error=f"git fetch {base_remote} {base_ref} failed (network/auth issue)")
        if no_push and git.is_ancestor(runner, base_target, "HEAD", cwd=cwd):
            return RebasePushResult(exit_code=0, skipped_already_fresh=True)
        rebase_result = git.rebase(runner, base_target, cwd=cwd)

    if rebase_result.returncode != 0:
        conflicts = ",".join(git.unmerged_paths(runner, cwd=cwd))
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

    push_result = git.force_push_recovery(runner, remote="origin", cwd=cwd)
    if push_result.pushed:
        return RebasePushResult(exit_code=0)
    return RebasePushResult(exit_code=2, push_error=push_result.status)
