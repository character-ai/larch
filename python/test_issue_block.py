# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for block-issue GraphQL helper."""

from __future__ import annotations

import json
from typing import Any

from larch.issue import issue_block
from larch.core import proc


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_graphql_success_and_warning(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout="owner/repo\n")
        if calls == 2:
            return _result(argv, stdout=json.dumps({"data": {"repository": {"ia": {"id": "A"}, "ib": {"id": "B"}}}}))
        return _result(argv, stdout=json.dumps({"data": {"addBlockedBy": {"issue": {"blockedBy": {"nodes": [{"number": 99}]}}}}}))

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    assert issue_block.add_blocked_by_main(["1", "2"]) == 0
    captured = capsys.readouterr()
    assert "SUCCESS=true" in captured.out
    assert "✓ #1 is now blocked by #2" in captured.out
    assert "WARNING=" in captured.err


def test_mutation_failure(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout="owner/repo\n")
        if calls == 2:
            return _result(argv, stdout=json.dumps({"data": {"repository": {"ia": {"id": "A"}, "ib": {"id": "B"}}}}))
        return _result(argv, returncode=1, stderr="mutation failed")

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    assert issue_block.add_blocked_by_main(["1", "2"]) == 1
    assert "ERROR=addBlockedBy mutation failed:" in capsys.readouterr().err


def test_mutation_success_without_warning(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout="owner/repo\n")
        if calls == 2:
            return _result(argv, stdout=json.dumps({"data": {"repository": {"ia": {"id": "A"}, "ib": {"id": "B"}}}}))
        return _result(
            argv,
            stdout=json.dumps({"data": {"addBlockedBy": {"issue": {"blockedBy": {"nodes": [{"number": 2}]}}}}}),
        )

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    assert issue_block.add_blocked_by_main(["1", "2"]) == 0
    captured = capsys.readouterr()
    assert "SUCCESS=true" in captured.out
    assert captured.err == ""


def test_lookup_failure(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "repo", "view"]:
            return _result(argv, stdout="owner/repo\n")
        return _result(argv, returncode=1, stderr="bad")

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    assert issue_block.add_blocked_by_main(["1", "2"]) == 1
    assert "ERROR=GraphQL node-ID lookup failed:" in capsys.readouterr().err
