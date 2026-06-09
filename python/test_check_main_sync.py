# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Parity tests for check_main_sync and git check-main-sync CLI."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import config
import git
import git_cli


def _ok(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 0, stdout, stderr, 0.01)


def _fail(rc: int = 1, stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, "", stderr, 0.01)


def test_check_main_sync_not_on_main() -> None:
    runner = RecordingRunner(
        responses=[
            _ok("feature/foo\n"),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "not-main"
    assert result.exit_code == 0


def test_check_main_sync_in_sync() -> None:
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("0\n"),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "ok"
    assert result.ahead_count == 0
    assert result.exit_code == 0


def test_check_main_sync_blocked_non_log_commit() -> None:
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("1\n"),
            _ok("feat: real change\n"),
            _ok("code.sh\n"),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "blocked"
    assert result.ahead_count == 1
    assert result.exit_code == 1
    assert result.error


def test_check_main_sync_probe_error_missing_origin_main() -> None:
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _fail(128),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "probe-error"
    assert result.exit_code == 2
    assert result.error


def test_check_main_sync_cli_blocked_exit_one(monkeypatch, capsys) -> None:
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("1\n"),
            _ok("feat: change\n"),
            _ok("x.txt\n"),
        ],
    )
    monkeypatch.setattr(git_cli, "proc", runner)
    assert git_cli.check_main_sync_main([]) == 1
    out = capsys.readouterr().out
    assert "SYNC_STATUS=blocked" in out
    assert "AHEAD_COUNT=1" in out
    assert "ERROR=" in out


def test_check_main_sync_cli_flush_reset(monkeypatch, capsys) -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("1\n"),
            _ok(f"{prefix} run abc\n"),
            _ok("larch-logs/run.md\n"),
            _ok(""),
            _ok(""),
        ],
    )
    monkeypatch.setattr(git_cli, "proc", runner)
    assert git_cli.check_main_sync_main([]) == 0
    out = capsys.readouterr().out
    assert "SYNC_STATUS=reset" in out
    assert "AHEAD_COUNT=1" in out
