"""Branch push orchestration (parity with scripts/git-push.sh)."""

from __future__ import annotations

import random
import time
from collections.abc import Callable
from dataclasses import dataclass

import config
import git
from errors import ShipError
from proc import Runner
from run_context import RunContext


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
    """Fork-aware push always targets origin (parity with create-pr.sh / git-push.sh)."""
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
    """No-arg ``git-push.sh`` parity: named-branch guard, retries, deduped stderr."""
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
