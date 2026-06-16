"""Tests for push.py."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

import config
import git
import push
from errors import ShipError
from proc import CommandResult
from run_context import RunContext

from test_support import RecordingRunner as _RecordingRunner, make_run_context
import phantom
import rebase


@dataclass
class RecordingRunner(_RecordingRunner):
    strict: bool = True


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
    base = make_run_context(branch="feat/x")
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


def test_push_backs_off_when_stderr_unchanged() -> None:
    runner = RecordingRunner(
        responses=_push_git_responses(
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "same error", 0.01),
        ),
    )
    sleeps: list[float] = []
    result = push.push_branch(runner, _ctx(), sleeper=sleeps.append)
    assert result.status == "failed"
    assert result.attempts == config.PUSH_MAX_ATTEMPTS
    assert len(sleeps) == config.PUSH_MAX_ATTEMPTS - 1


# CLI contract tests migrated from test_push_cli.py.
def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_force_status_map_dirty_worktree(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout=" M file\n")])
    monkeypatch.setattr(push, "proc", runner)
    assert push.force_main([]) == 1
    out = capsys.readouterr().out
    assert "PUSHED=false" in out
    assert "STATUS=dirty_worktree" in out


def test_checkpoint_probe_emits_rebase_outcome_on_skip(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    @dataclass
    class _RebaseResult:
        exit_code: int = 0
        skipped_already_fresh: bool = True
        skipped_already_pushed: bool = False
        conflict_files: str = ""
        rebase_error: str = ""

    @dataclass
    class _ProbeResult:
        dirty: object
        append_warn_error: str = ""

    @dataclass
    class _Dirty:
        status: str = "clean"
        reason: str = ""
        count: int = 0
        paths_file: str = ""

    def _stub_rebase_push(*_args: object, **_kwargs: object) -> _RebaseResult:
        return _RebaseResult()

    monkeypatch.setattr(rebase, "rebase_push", _stub_rebase_push)
    def _stub_probe_with_warn(*_args: object, **_kwargs: object) -> _ProbeResult:
        return _ProbeResult(dirty=_Dirty())

    monkeypatch.setattr(
        phantom,
        "probe_with_warn",
        _stub_probe_with_warn,
    )
    assert push.checkpoint_probe_main(["1.r", "plan"]) == 0
    out = capsys.readouterr().out
    assert "REBASE_OUTCOME=skipped" in out
    assert "SKIPPED_ALREADY_FRESH=true" in out
    assert "PHANTOM_STATUS=clean" in out


def test_branch_push_dedupes_stderr(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n")])
    monkeypatch.setattr(push, "proc", runner)
    assert push.branch_main([]) == 1
    captured = capsys.readouterr()
    assert "BRANCH=feature" in captured.out
    assert "(repeated 3 times)" in captured.err


def test_branch_main_unknown_argument_stderr_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    assert push.branch_main(["--bogus"]) == 1
    err = capsys.readouterr().err
    assert "git-push.sh: unknown argument: --bogus" in err


def test_force_main_detached_head_stderr_prefix(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def fake_recovery(*_args: object, **_kwargs: object) -> git.ForcePushResult:
        return git.ForcePushResult(pushed=False, status="detached_head", branch="")

    monkeypatch.setattr(git, "force_push_recovery", fake_recovery)
    assert push.force_main([]) == 2
    err = capsys.readouterr().err
    assert err.strip() == "git-force-push.sh: not on a named branch"
