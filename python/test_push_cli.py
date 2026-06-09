# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for push_cli."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import push_cli


def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_force_status_map_dirty_worktree(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout=" M file\n")])
    monkeypatch.setattr(push_cli, "proc", runner)
    assert push_cli.force_main([]) == 1
    out = capsys.readouterr().out
    assert "PUSHED=false" in out
    assert "STATUS=dirty_worktree" in out


def test_branch_push_dedupes_stderr(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(stdout="feature\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n"), _res(stdout="feature\n"), _res(1, stderr="nope\n")])
    monkeypatch.setattr(push_cli, "proc", runner)
    assert push_cli.branch_main([]) == 1
    captured = capsys.readouterr()
    assert "BRANCH=feature" in captured.out
    assert "(repeated 3 times)" in captured.err
