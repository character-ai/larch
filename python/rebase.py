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
from errors import NeedsUserInput, ShipError, Stalled, TransientNetworkError
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
                    raise NeedsUserInput(
                        _redact_outbound(
                            "fixer waterfall could not resolve conflicts",
                        ),
                    )
                if _unmerged_paths(runner, cwd=cwd):
                    raise NeedsUserInput(
                        _redact_outbound(
                            "conflicts remain after fixer waterfall",
                        ),
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
        _abort_rebase(runner, cwd=cwd)
        combined = f"{fetch_result.stdout}\n{fetch_result.stderr}"
        if retry.is_transient_net_signature(combined):
            raise TransientNetworkError(
                _redact_outbound("fetch failed with transient network signature"),
                result=fetch_result,
            )
        raise Stalled(_redact_outbound("fetch failed"))

    if git.is_ancestor(runner, base_target, "HEAD", cwd=cwd):
        rebased = False
    else:
        rebase_result = git.rebase(runner, base_target, cwd=cwd)
        if rebase_result.returncode == 0:
            rebased = True
        elif _unmerged_paths(runner, cwd=cwd):
            rebased = True
            _resolve_conflicts(
                runner,
                launch_fn,
                repo=repo,
                run_id=run_id,
                cwd=cwd,
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
