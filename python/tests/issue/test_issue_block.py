"""Tests for fail-closed block-issue GraphQL helpers."""
# pylint: disable=missing-function-docstring,duplicate-code  # pytest cases and local fakes are self-describing

from __future__ import annotations

import json
from typing import Any

from larch.core import proc
from larch.issue import issue_block


def _result(
    argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
) -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def _lookup() -> str:
    return json.dumps({"data": {"repository": {"ia": {"id": "A"}, "ib": {"id": "B"}}}})


def _mutation(field: str) -> str:
    return json.dumps({"data": {field: {"issue": {"id": "A"}}}})


def _snapshot(updated_at: str = "2026-07-12T10:00:00Z") -> str:
    return json.dumps(
        {
            "number": 1,
            "title": "Issue",
            "body": "Body",
            "state": "OPEN",
            "stateReason": "",
            "url": "https://github.com/owner/repo/issues/1",
            "updatedAt": updated_at,
            "labels": [],
            "comments": [],
        }
    )


def test_missing_operator_authorization_makes_zero_calls(
    monkeypatch: Any, capsys: Any
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    assert issue_block.add_blocked_by_main(["1", "2", "--repo", "owner/repo"]) == 2
    assert not calls
    assert "--operator-invoked is required" in capsys.readouterr().err


def test_verified_add_success(monkeypatch: Any, capsys: Any) -> None:
    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:3] == ["gh", "api", "graphql"] and "LOOKUP_SENTINEL" not in argv:
            query = argv[-1]
            if "query=query" in query:
                return _result(argv, stdout=_lookup())
            return _result(argv, stdout=_mutation("addBlockedBy"))
        if "dependencies/blocked_by" in " ".join(argv):
            return _result(argv, stdout='[{"number": 2}]')
        raise AssertionError(argv)

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    rc = issue_block.add_blocked_by_main(
        ["1", "2", "--repo", "owner/repo", "--operator-invoked"]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "SUCCESS=true" in output
    assert "RELATION_VERIFIED=true" in output
    assert "✓ #1 is now blocked by #2" in output


def test_verified_remove_success(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout=_lookup())
        if calls == 2:
            return _result(argv, stdout=_mutation("removeBlockedBy"))
        return _result(argv, stdout="[]")

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    rc = issue_block.remove_blocked_by_main(
        ["1", "2", "--repo", "owner/repo", "--operator-invoked"]
    )
    assert rc == 0
    assert "is no longer blocked by" in capsys.readouterr().out


def test_malformed_mutation_payload_fails_closed(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout=_lookup())
        return _result(argv, stdout='{"data":{"addBlockedBy":{}}}')

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    rc = issue_block.add_blocked_by_main(
        ["1", "2", "--repo", "owner/repo", "--operator-invoked"]
    )
    assert rc == 8
    assert "omitted its issue postcondition payload" in capsys.readouterr().err


def test_absent_requested_relation_fails_closed(monkeypatch: Any, capsys: Any) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout=_lookup())
        if calls == 2:
            return _result(argv, stdout=_mutation("addBlockedBy"))
        return _result(argv, stdout="[]")

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    rc = issue_block.add_blocked_by_main(
        ["1", "2", "--repo", "owner/repo", "--operator-invoked"]
    )
    assert rc == 8
    assert "failed exact read-back" in capsys.readouterr().err


def test_triage_expected_timestamp_is_required(capsys: Any) -> None:
    rc = issue_block.add_blocked_by_main(
        ["1", "2", "--repo", "owner/repo", "--operator-invoked", "--triage-controlled"],
    )
    assert rc == 2
    assert "requires a valid --expected-updated-at" in capsys.readouterr().err


def test_triage_dependency_rechecks_and_returns_fresh_timestamp(
    monkeypatch: Any, capsys: Any
) -> None:
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls in {1, 3}:
            return _result(argv, stdout=_snapshot())
        if calls == 2:
            return _result(argv, stdout=_lookup())
        if calls == 4:
            return _result(argv, stdout=_mutation("addBlockedBy"))
        if calls == 5:
            return _result(argv, stdout='[{"number": 2}]')
        return _result(argv, stdout=_snapshot("2026-07-12T10:00:01Z"))

    monkeypatch.setattr(issue_block.proc, "run", fake_run)
    rc = issue_block.add_blocked_by_main(
        [
            "1",
            "2",
            "--repo",
            "owner/repo",
            "--operator-invoked",
            "--triage-controlled",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
        ]
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "RELATION_VERIFIED=true" in output
    assert "UPDATED_AT=2026-07-12T10:00:01Z" in output
