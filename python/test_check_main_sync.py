# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Parity tests for check_main_sync and git check-main-sync CLI."""

from __future__ import annotations

import subprocess
from pathlib import Path

from larch.core.proc import CommandResult, ProcRunner
from test_support import RecordingRunner

from larch.core import config
from larch.git import git


def _ok(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 0, stdout, stderr, 0.01)


def _fail(rc: int = 1, stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, "", stderr, 0.01)


def _run_git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def _make_flush_only_empty_diff_repo(tmp_path: Path) -> Path:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX
    bare = tmp_path / "remote.git"
    local = tmp_path / "repo"
    subprocess.run(["git", "init", "--bare", str(bare)], check=True, capture_output=True)
    subprocess.run(["git", "init", str(local)], check=True, capture_output=True)
    _run_git(local, "remote", "add", "origin", str(bare))
    _run_git(local, "config", "user.email", "test@test")
    _run_git(local, "config", "user.name", "Test")
    (local / "README.md").write_text("init\n", encoding="utf-8")
    _run_git(local, "add", "README.md")
    _run_git(local, "commit", "-m", "init")
    _run_git(local, "branch", "-M", "main")
    _run_git(local, "push", "-u", "origin", "main")

    log_dir = local / "larch-logs"
    log_dir.mkdir()
    (log_dir / "run.md").write_text("a\n", encoding="utf-8")
    _run_git(local, "add", "larch-logs/run.md")
    _run_git(local, "commit", "-m", f"{prefix} run one")

    (log_dir / "run.md").unlink()
    _run_git(local, "add", "larch-logs/run.md")
    _run_git(local, "commit", "-m", f"{prefix} run two")
    return local


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
    monkeypatch.setattr(git, "proc", runner)
    assert git.check_main_sync_main([]) == 1
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
    monkeypatch.setattr(git, "proc", runner)
    assert git.check_main_sync_main([]) == 0
    out = capsys.readouterr().out
    assert "SYNC_STATUS=reset" in out
    assert "AHEAD_COUNT=1" in out


def test_check_main_sync_mixed_ahead_blocked() -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("2\n"),
            _ok(f"{prefix} run xyz\nfix: real change\n"),
            _ok("larch-logs/a.md\ncode.sh\n"),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "blocked"
    assert result.ahead_count == 2
    assert result.exit_code == 1


def test_check_main_sync_flush_dirty_refuses_reset() -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("1\n"),
            _ok(f"{prefix} run flushdirty\n"),
            _ok("larch-logs/y.md\n"),
            _ok(" M README.md\n"),
        ],
    )
    result = git.check_main_sync(runner)
    assert result.status == "probe-error"
    assert result.exit_code == 2
    assert result.error
    assert "not clean" in result.error


def test_check_main_sync_bad_args_exit_two(capsys) -> None:
    assert git.check_main_sync_main(["--unknown-flag"]) == 2
    assert "unknown flag" in capsys.readouterr().err


def test_check_main_sync_empty_diff_flush_only_resets(tmp_path: Path) -> None:
    repo = _make_flush_only_empty_diff_repo(tmp_path)
    diff = subprocess.run(
        ["git", "diff", "--name-only", "origin/main", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert diff == ""

    result = git.check_main_sync(ProcRunner(), cwd=str(repo))
    assert result.status == "reset"
    assert result.ahead_count == 2

    after = subprocess.run(
        ["git", "rev-list", "--count", "origin/main..HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert after == "0"


def test_check_main_sync_cli_mixed_ahead_blocked(monkeypatch, capsys) -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX
    runner = RecordingRunner(
        responses=[
            _ok("main\n"),
            _ok("2\n"),
            _ok(f"{prefix} run xyz\nfix: real change\n"),
            _ok("larch-logs/a.md\ncode.sh\n"),
        ],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.check_main_sync_main([]) == 1
    out = capsys.readouterr().out
    assert "SYNC_STATUS=blocked" in out
    assert "AHEAD_COUNT=2" in out
