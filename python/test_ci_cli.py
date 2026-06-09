# pyright: reportUnknownParameterType=false, reportMissingParameterType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""CLI contract tests for ci_cli."""

from __future__ import annotations

from proc import CommandResult
from test_support import RecordingRunner

import ci_cli


def _res(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), rc, stdout, stderr, 0.01)


def test_behind_count_fail_open(monkeypatch, capsys):
    runner = RecordingRunner(responses=[_res(1, stderr="fetch failed")])
    monkeypatch.setattr(ci_cli, "proc", runner)
    assert ci_cli.behind_count_main([]) == 0
    assert capsys.readouterr().out.strip() == "0"


def test_decide_usage_exit_one():
    assert ci_cli.decide_main([]) == 1
