# pyright: reportUnusedCallResult=false
"""Branch push orchestration for ``cli.py push branch`` and ``push force``."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

import argparse
import sys
import config
import git
from errors import ShipError
from proc import Runner
from run_context import RunContext
import logging_util
import phantom
import proc
import rebase


@dataclass(frozen=True)
class PushResult:
    remote: str
    attempts: int
    status: str
    branch: str = ""
    stderr: str = ""
    exit_code: int = 0


def assert_clean_worktree(runner: Runner, *, cwd: str | None = None) -> None:
    """Fail closed when the working tree has uncommitted changes (#2434)."""
    result = git.status_porcelain(runner, cwd=cwd)
    if result.returncode != 0:
        msg = "git status --porcelain failed before push"
        raise ShipError(msg)
    if result.stdout.strip():
        msg = "uncommitted working-tree changes detected before push"
        raise ShipError(msg)


def select_push_remote(_runner: Runner, _ctx: RunContext, *, cwd: str | None = None) -> str:
    """Fork-aware push always targets origin for ``cli.py push branch``."""
    _ = cwd
    return "origin"


def push_branch(
    runner: Runner,
    ctx: RunContext,
    *,
    cwd: str | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> PushResult:
    """Push current branch with retries and fork-aware remote selection."""
    if sleeper is None:
        sleeper = time.sleep
    assert_clean_worktree(runner, cwd=cwd)
    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        msg = "refusing push on detached HEAD"
        raise ShipError(msg)
    if branch != ctx.branch:
        msg = (
            f"checked-out branch {branch!r} does not match "
            f"RunContext.branch {ctx.branch!r}"
        )
        raise ShipError(msg)
    remote = select_push_remote(runner, ctx, cwd=cwd)
    for attempt in range(1, config.PUSH_MAX_ATTEMPTS + 1):
        result = git.push_set_upstream(runner, remote, "HEAD", cwd=cwd)
        if result.returncode == 0:
            return PushResult(remote=remote, attempts=attempt, status="pushed")
        if attempt < config.PUSH_MAX_ATTEMPTS:
            backoff = config.TRANSIENT_RETRY_BACKOFF_SEC[
                min(attempt - 1, len(config.TRANSIENT_RETRY_BACKOFF_SEC) - 1)
            ]
            jitter = random.uniform(0.0, 0.5)
            sleeper(float(backoff) + jitter)
    return PushResult(remote=remote, attempts=config.PUSH_MAX_ATTEMPTS, status="failed")


def push_current_branch(
    runner: Runner,
    *,
    cwd: str | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> PushResult:
    """No-arg push parity: named-branch guard, retries, deduped stderr."""
    if sleeper is None:
        sleeper = time.sleep
    branch = git.try_current_branch(runner, cwd=cwd)
    if not branch:
        return PushResult(remote="origin", attempts=0, status="detached_head", exit_code=1)
    stderr_blocks: list[str] = []
    last_exit = 0
    for attempt in range(1, config.PUSH_MAX_ATTEMPTS + 1):
        if not git.try_current_branch(runner, cwd=cwd):
            return PushResult(
                remote="origin",
                attempts=attempt,
                status="detached_head",
                branch=branch,
                stderr=f"git-push.sh: not on a named branch before attempt {attempt}\n",
                exit_code=1,
            )
        result = runner.run(["git", "push"], cwd=cwd)
        if result.returncode == 0:
            return PushResult(
                remote="origin",
                attempts=attempt,
                status="pushed",
                branch=branch,
                exit_code=0,
            )
        last_exit = result.returncode
        stderr_blocks.append(result.stderr)
        if attempt < config.PUSH_MAX_ATTEMPTS:
            sleeper(float(max(1, 2 ** (attempt - 1))))
    rendered: list[str] = []
    previous: str | None = None
    repeat = 0
    for block in stderr_blocks:
        if previous is not None and block == previous:
            repeat += 1
            continue
        if previous is not None:
            rendered.append(previous)
            if repeat:
                rendered.append(f"(repeated {repeat + 1} times)\n")
        previous = block
        repeat = 0
    if previous is not None:
        rendered.append(previous)
        if repeat:
            rendered.append(f"(repeated {repeat + 1} times)\n")
    return PushResult(
        remote="origin",
        attempts=config.PUSH_MAX_ATTEMPTS,
        status="failed",
        branch=branch,
        stderr="".join(rendered),
        exit_code=last_exit or 1,
    )


# CLI entrypoints migrated from push_cli.py.
_REBASE_FAILED_EXIT = 3
_CHECKPOINT_LOAD_ROUTING = "load-routing"


def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _checkpoint_next_for_exit(exit_code: int) -> str:
    if exit_code == 0:
        return "continue"
    return _CHECKPOINT_LOAD_ROUTING


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def _rebase_sanitize(text: str) -> str:
    return " ".join(text.split())


def _conflict_files_csv(result: rebase.RebasePushResult) -> str:
    if result.conflict_files:
        return result.conflict_files
    files: list[str] = git.try_unmerged_paths(proc)
    if not files:
        files = [item.path for item in git.try_conflict_files(proc)]
    return ",".join(files)


def _emit_rebase_checkpoint_keys(result: rebase.RebasePushResult) -> int:
    if result.skipped_already_pushed:
        _emit_kv(key="SKIPPED_ALREADY_PUSHED", value="true")
    if result.skipped_already_fresh:
        _emit_kv(key="SKIPPED_ALREADY_FRESH", value="true")
    if result.conflict_files:
        _emit_kv(key="CONFLICT_FILES", value=result.conflict_files)
    if result.rebase_error and result.exit_code != _REBASE_FAILED_EXIT:
        _emit_kv(key="REBASE_ERROR", value=_rebase_sanitize(result.rebase_error))

    if result.exit_code == 0:
        if result.skipped_already_pushed or result.skipped_already_fresh:
            _emit_kv(key="REBASE_OUTCOME", value="skipped")
        else:
            _emit_kv(key="REBASE_OUTCOME", value="ok")
        _emit_kv(key="ROUTE", value="continue")
        _emit_kv(key="CHECKPOINT_NEXT", value=_checkpoint_next_for_exit(result.exit_code))
        return 0
    if result.exit_code == 1:
        _emit_kv(key="REBASE_OUTCOME", value="conflict")
        _emit_kv(key="CONFLICT_FILES", value=_conflict_files_csv(result))
        _emit_kv(key="ROUTE", value="conflict")
        _emit_kv(key="CHECKPOINT_NEXT", value=_checkpoint_next_for_exit(result.exit_code))
        return 1
    if result.exit_code == _REBASE_FAILED_EXIT:
        _emit_kv(key="REBASE_OUTCOME", value="failed")
        err = result.rebase_error or "rebase-failed"
        _emit_kv(key="REBASE_ERROR", value=_rebase_sanitize(err))
        _emit_kv(key="ROUTE", value="bail")
        _emit_kv(key="CHECKPOINT_NEXT", value=_checkpoint_next_for_exit(result.exit_code))
        return 3
    _emit_kv(key="REBASE_OUTCOME", value="failed")
    _emit_kv(key="REBASE_ERROR", value=f"unexpected-rc-{result.exit_code}")
    _emit_kv(key="ROUTE", value="bail")
    _emit_kv(key="CHECKPOINT_NEXT", value=_checkpoint_next_for_exit(result.exit_code))
    return result.exit_code


def _is_trivial_conflict_file(path: str) -> bool:
    return path.startswith("larch-logs/")


def _split_conflict_csv(value: str) -> list[str]:
    return [item for item in value.split(",") if item]


def _current_unmerged_conflict_files() -> str:
    files = git.try_unmerged_paths(proc)
    if files:
        return ",".join(files)
    return ",".join(item.path for item in git.try_conflict_files(proc))


def _conflict_upstream_deleted(path: str) -> bool:
    for item in git.try_conflict_files(proc):
        if item.path == path:
            return not item.stage_2
    return False


def _resolve_trivial_conflict_file(path: str) -> bool:
    checkout = git.checkout_ours(proc, path)
    if checkout.returncode != 0:
        if not _conflict_upstream_deleted(path):
            print(f"WARN rebase-probe: failed to resolve trivial conflict {path}", file=sys.stderr)
            return False
        removed = git.rm(proc, path, force=True)
        if removed.returncode != 0:
            print(f"WARN rebase-probe: failed to resolve trivial conflict {path}", file=sys.stderr)
            return False
        return True
    staged = git.add(proc, path)
    if staged.returncode != 0:
        print(f"WARN rebase-probe: failed to stage trivial conflict {path}", file=sys.stderr)
        return False
    return True


def _empty_continue_result(result: rebase.RebasePushResult) -> bool:
    return _is_empty_or_already_applied_rebase_error(result.rebase_error)


def _is_empty_or_already_applied_rebase_error(text: str) -> bool:
    lowered = text.lower()
    if "nothing to commit" in lowered:
        return True
    if "no changes" in lowered:
        return True
    return "all merge conflicts were fixed" in lowered


def _continue_checkpoint_rebase() -> rebase.RebasePushResult:
    return rebase.rebase_push(
        proc,
        continue_mode=True,
        no_push=True,
        keep_on_conflict=True,
    )


def _handle_empty_continue_rc3(result: rebase.RebasePushResult) -> rebase.RebasePushResult | None:
    while True:
        unmerged = _current_unmerged_conflict_files()
        if unmerged:
            return rebase.RebasePushResult(exit_code=1, conflict_files=unmerged)
        if not _empty_continue_result(result):
            return None
        skipped = git.rebase_skip(proc)
        if skipped.returncode != 0:
            print("WARN rebase-probe: git rebase --skip failed after empty continue", file=sys.stderr)
            return None
        if not git.rebase_in_progress(proc):
            return rebase.RebasePushResult(exit_code=0)
        result = _continue_checkpoint_rebase()
        if result.exit_code != _REBASE_FAILED_EXIT:
            return result


def _checkpoint_rebase_result(
    *,
    base_remote: str,
    base_ref: str,
) -> rebase.RebasePushResult:
    result = rebase.rebase_push(
        proc,
        no_push=True,
        skip_if_pushed=True,
        keep_on_conflict=True,
        base_remote=base_remote,
        base_ref=base_ref,
    )
    if result.exit_code != 1:
        return result

    for _iteration in range(50):
        cf: str = _conflict_files_csv(result)
        if not cf:
            return rebase.RebasePushResult(exit_code=1, conflict_files="")
        conflicts: list[str] = _split_conflict_csv(cf)
        trivial = [path for path in conflicts if _is_trivial_conflict_file(path)]
        nontrivial = [path for path in conflicts if not _is_trivial_conflict_file(path)]
        if not trivial:
            return rebase.RebasePushResult(exit_code=1, conflict_files=cf)
        for path in trivial:
            if not _resolve_trivial_conflict_file(path):
                return rebase.RebasePushResult(
                    exit_code=1,
                    conflict_files=_current_unmerged_conflict_files(),
                )
        if nontrivial:
            cf_now = _current_unmerged_conflict_files()
            return rebase.RebasePushResult(exit_code=1, conflict_files=cf_now or ",".join(nontrivial))
        result = _continue_checkpoint_rebase()
        if result.exit_code == _REBASE_FAILED_EXIT:
            handled = _handle_empty_continue_rc3(result)
            if handled is None:
                return result
            result = handled
        if result.exit_code != 1:
            return result
    print(
        "WARN rebase-probe: trivial conflict pre-pass hit iteration cap; surfacing current conflicts",
        file=sys.stderr,
    )
    return rebase.RebasePushResult(exit_code=1, conflict_files=_current_unmerged_conflict_files())


def branch_main(argv: list[str]) -> int:
    if argv:
        print(f"git-push.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = push_current_branch(proc)
    if result.branch:
        _emit_kv(key="BRANCH", value=result.branch)
    if result.stderr:
        sys.stderr.write(result.stderr)
    return result.exit_code


def force_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push force")
    parser.add_argument("--expected-remote-oid", default=None)
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = git.force_push_recovery(
        proc,
        expected_remote_oid=args.expected_remote_oid,
    )
    if result.branch:
        _emit_kv(key="BRANCH", value=result.branch)
    elif result.status == "detached_head":
        print("git-force-push.sh: not on a named branch", file=sys.stderr)
    _emit_kv(key="PUSHED", value=str(result.pushed).lower())
    _emit_kv(key="STATUS", value=result.status)
    if result.pushed:
        return 0
    if result.status in {"detached_head", "branch_mismatch", "status_failed"}:
        return 2
    return 1


def rebase_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push rebase")
    parser.add_argument("--continue", dest="continue_mode", action="store_true")
    parser.add_argument("--no-push", action="store_true")
    parser.add_argument("--skip-if-pushed", action="store_true")
    parser.add_argument("--keep-on-conflict", action="store_true")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 3
    result = rebase.rebase_push(
        proc,
        continue_mode=args.continue_mode,
        no_push=args.no_push,
        skip_if_pushed=args.skip_if_pushed,
        keep_on_conflict=args.keep_on_conflict,
        base_remote=args.base_remote,
        base_ref=args.base_ref,
    )
    if result.skipped_already_pushed:
        _emit_kv(key="SKIPPED_ALREADY_PUSHED", value="true")
    if result.skipped_already_fresh:
        _emit_kv(key="SKIPPED_ALREADY_FRESH", value="true")
    if result.conflict_files:
        _emit_kv(key="CONFLICT_FILES", value=result.conflict_files)
    if result.rebase_error:
        _emit_kv(key="REBASE_ERROR", value=result.rebase_error)
    if result.push_error:
        _emit_kv(key="PUSH_ERROR", value=result.push_error)
    return result.exit_code


def checkpoint_probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py push checkpoint-probe")
    parser.add_argument("step_prefix")
    parser.add_argument("short_name")
    parser.add_argument("--base-remote", default=None)
    parser.add_argument("--base-ref", default=None)
    parser.add_argument("--forked-target", choices=("true", "false"), default="false")
    args = _parse(parser, argv)
    if args is None:
        return 2
    print(f"→ rebase-probe: {args.step_prefix} {args.short_name}", file=sys.stderr)
    base_remote = args.base_remote or ("upstream" if args.forked_target == "true" else "origin")
    base_ref = args.base_ref or "main"
    result = _checkpoint_rebase_result(
        base_remote=base_remote,
        base_ref=base_ref,
    )
    rc = _emit_rebase_checkpoint_keys(result)
    if rc != 0:
        return rc
    probe = phantom.probe_with_warn(proc, step=f"{args.step_prefix}-post-rebase")
    _emit_kv(key="PHANTOM_STATUS", value=probe.dirty.status)
    if probe.dirty.reason:
        _emit_kv(key="PHANTOM_REASON", value=probe.dirty.reason)
    if probe.dirty.status == "phantom":
        _emit_kv(key="PHANTOM_COUNT", value=probe.dirty.count)
        if probe.dirty.paths_file:
            _emit_kv(key="PHANTOM_PATHS_FILE", value=probe.dirty.paths_file)
    if probe.append_warn_error:
        _emit_kv(key="PHANTOM_APPEND_WARN_ERROR", value=probe.append_warn_error)
    return 0
