# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for git_cli."""

from __future__ import annotations

import pytest

from proc import CommandResult
from test_support import RecordingRunner

import git_cli


def _ok(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 0, stdout, stderr, 0.01)


def _fail(stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 1, "", stderr, 0.01)


def test_count_commits_missing_main_status_file(monkeypatch, tmp_path, capsys):
    runner = RecordingRunner(responses=[_fail(), _fail()])
    monkeypatch.setattr(git_cli, "proc", runner)
    status_file = tmp_path / "status"
    monkeypatch.setenv("COUNT_COMMITS_STATUS_FILE", str(status_file))
    assert git_cli.count_commits_main([]) == 0
    assert capsys.readouterr().out.strip() == "0"
    assert status_file.read_text(encoding="utf-8").strip() == "missing_main_ref"


def test_branch_info_emits_detached_empty_branch(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_ok("abc123\n"), _ok("\n")])
    monkeypatch.setattr(git_cli, "proc", runner)
    assert git_cli.branch_info_main([]) == 0
    out = capsys.readouterr().out
    assert "HEAD_SHA=abc123" in out
    assert "CURRENT_BRANCH=" in out


def test_clean_tree_fail_closed_probe_error(monkeypatch, capsys):
    runner = RecordingRunner(responses=[CommandResult(("git",), 128, "", "no repo\n", 0.01)])
    monkeypatch.setattr(git_cli, "proc", runner)
    assert git_cli.clean_tree_main(["--fail-closed"]) == 1
    out = capsys.readouterr().out
    assert "CLEAN=unknown" in out
    assert "PROBE_ERROR=git exited 128" in out


def test_check_phantom_dirty_clean_omits_optional_keys(monkeypatch, capsys):
    runner = RecordingRunner()
    monkeypatch.setattr(git_cli, "proc", runner)

    def _clean_probe(*_args: object, **_kwargs: object) -> git_cli.phantom.PhantomDirtyResult:
        return git_cli.phantom.PhantomDirtyResult(status="clean")

    monkeypatch.setattr(git_cli.phantom, "check_phantom_dirty", _clean_probe)
    assert (
        git_cli.check_phantom_dirty_main(
            ["--baseline", "/tmp/base.z", "--step", "s1", "--phantom-paths-dir", "/tmp/p"],
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "STATUS=clean" in out
    assert "REASON=" not in out
    assert "PHANTOM_COUNT=" not in out
    assert "PHANTOM_PATHS_FILE=" not in out


def test_check_phantom_dirty_parse_error_emits_unknown(monkeypatch, capsys):
    runner = RecordingRunner()
    monkeypatch.setattr(git_cli, "proc", runner)
    assert git_cli.check_phantom_dirty_main(["--unknown"]) == 0
    out = capsys.readouterr().out
    assert "STATUS=unknown" in out
    assert "REASON=unknown-flag" in out


def test_emit_kv_rejects_multiline_values() -> None:
    with pytest.raises(ValueError, match="newline"):
        git_cli._emit_kv("ERROR", "line1\nline2")  # pyright: ignore[reportPrivateUsage]
