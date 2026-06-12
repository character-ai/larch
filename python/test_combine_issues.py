# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Tests for combine issue filtering."""

from __future__ import annotations

import json

import combine_issues
from proc import CommandResult


class Runner:
    def __init__(self, stdout: str):
        self.stdout = stdout
    def run(self, argv, **_kwargs):
        if argv[:3] == ["gh", "issue", "list"]:
            return CommandResult(tuple(argv), 0, self.stdout, "", 0.01)
        return CommandResult(tuple(argv), 0, '{"nameWithOwner":"o/r"}', "", 0.01)


def test_fetch_filters_busy_titles(monkeypatch, capsys):
    issues = [
        {"number":1,"title":"[IMPLEMENTING] busy"},
        {"number":2,"title":"[DESIGNED] keep"},
        {"number":3,"title":"normal"},
        {"number":4,"title":"[IN PROGRESS] legacy"},
    ]
    monkeypatch.setattr(combine_issues.proc, "run", Runner(json.dumps(issues)).run)
    assert combine_issues.fetch_main(["--repo", "o/r"]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["COUNT"] == "2"


def test_fetch_oos_only(monkeypatch, capsys):
    issues = [{"number":1,"title":"[OOS] one"},{"number":2,"title":"not"}]
    monkeypatch.setattr(combine_issues.proc, "run", Runner(json.dumps(issues)).run)
    assert combine_issues.fetch_main(["--repo", "o/r", "--oos"]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["COUNT"] == "1"
