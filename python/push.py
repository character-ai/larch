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
    refspec = f"HEAD:refs/heads/{branch}"
    last_stderr = ""
    for attempt in range(1, config.PUSH_MAX_ATTEMPTS + 1):
        result = git.push(runner, remote, refspec, cwd=cwd)
        if result.returncode == 0:
            return PushResult(remote=remote, attempts=attempt, status="pushed")
        stderr = result.stderr.strip()
        if (
            stderr
            and stderr == last_stderr
            and attempt < config.PUSH_MAX_ATTEMPTS
        ):
            continue
        last_stderr = stderr
        if attempt < config.PUSH_MAX_ATTEMPTS:
            backoff = config.TRANSIENT_RETRY_BACKOFF_SEC[
                min(attempt - 1, len(config.TRANSIENT_RETRY_BACKOFF_SEC) - 1)
            ]
            jitter = random.uniform(0.0, 0.5)
            sleeper(float(backoff) + jitter)
    return PushResult(remote=remote, attempts=config.PUSH_MAX_ATTEMPTS, status="failed")
