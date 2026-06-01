"""Tests for push.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import pytest

import config
import push
from errors import ShipError
from proc import CommandResult
from run_context import RunContext


def _empty_str_lists() -> list[list[str]]:
    return []


def _empty_command_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_str_lists)
    responses: list[CommandResult] = field(default_factory=_empty_command_results)
    _index: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        if self._index >= len(self.responses):
            msg = f"no response for call {argv}"
            raise AssertionError(msg)
        result = self.responses[self._index]
        self._index += 1
        return result


def _push_git_responses(*extra: CommandResult) -> list[CommandResult]:
    return [
        CommandResult(
            ("git", "status", "--porcelain", "--untracked-files=all"),
            0,
            "",
            "",
            0.01,
        ),
        CommandResult(
            ("git", "symbolic-ref", "--short", "HEAD"),
            0,
            "feat/x\n",
            "",
            0.01,
        ),
        *extra,
    ]


def _ctx(**kwargs: object) -> RunContext:
    base = RunContext(
        branch="feat/x",
        issue="1",
        repo="o/r",
        run_id="run-1",
        tmpdir="/tmp/impl",
        merge=True,
        draft=False,
        forked=False,
        manifest_path="/tmp/impl/manifest.json",
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
    )
    return base.with_(**kwargs)


def test_assert_clean_worktree_refuses_dirty() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                " M file\n",
                "",
                0.01,
            ),
        ],
    )
    with pytest.raises(ShipError, match="uncommitted"):
        push.assert_clean_worktree(runner)


def test_push_branch_retries_then_succeeds() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "fail", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
        ),
    )
    result = push.push_branch(
        runner,
        _ctx(),
        sleeper=lambda _s: None,
    )
    assert result.status == "pushed"
    assert result.attempts == 2


def test_push_branch_fork_uses_origin() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
        ),
    )
    result = push.push_branch(runner, _ctx(forked=True), sleeper=lambda _s: None)
    assert result.remote == "origin"


def test_push_branch_refuses_detached_head() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                "",
                "",
                0.01,
            ),
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 1, "", "", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="detached HEAD"):
        _ = push.push_branch(runner, _ctx(), sleeper=lambda _s: None)


def test_push_skips_retry_when_stderr_unchanged() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
        ),
    )
    result = push.push_branch(
        runner,
        _ctx(),
        sleeper=lambda _s: None,
    )
    assert result.status == "failed"
    assert result.attempts == config.PUSH_MAX_ATTEMPTS
