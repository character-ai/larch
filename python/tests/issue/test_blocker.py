# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
"""Tests for blocker.py."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from larch.issue import blocker
from larch.core.proc import CommandResult
from test_support import RecordingRunner


def _result(rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("gh",), rc, stdout, stderr, 0.01)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Depends on #150", [150]),
        ("blocked by #151", [151]),
        ("Blocked on #152", [152]),
        ("Requires #153", [153]),
        ("Needs #154", [154]),
        ("DEPENDS ON #155", [155]),
        ("Depends on **#156**", [156]),
        ("Depends on [#150](https://example.test)", []),
        ("[Depends on #150](https://example.test)", [150]),
        ("Depends on#150", []),
        ("Depends on #1502", [1502]),
        ("Depends on #150a", [150]),
        ("Depends on\n#150", []),
        ("`Depends on #1`\nDepends on #2", [2]),
        ("`Depends on #1\nDepends on #2`", [1, 2]),
        ("Depends on owner/repo#150", []),
    ],
)
def test_parse_prose_blockers(text: str, expected: list[int]) -> None:
    assert blocker.parse_prose_blockers(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("This does not affect release. Depends on #150", [150]),
        ("This is not a blocker, but blocked by #151", [151]),
        ("Not blocked by #152", []),
        ("No longer needs #153", []),
    ],
)
def test_parse_prose_blockers_scopes_negation(text: str, expected: list[int]) -> None:
    assert blocker.parse_prose_blockers(text) == expected


def test_native_open_blockers_case_insensitive_and_paginated() -> None:
    payload = json.dumps([{"number": 3, "state": "open"}]) + json.dumps(
        [{"number": "2", "state": "OPEN"}, {"number": 4, "state": "closed"}]
    )
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert blocker.native_open_blockers(runner, "7", repo="o/r") == [2, 3]


@pytest.mark.parametrize("result", [_result(stdout=""), _result(stdout="not json"), _result(rc=1)])
def test_native_open_blockers_fail_open(result: CommandResult) -> None:
    runner = RecordingRunner(responses=[result])
    assert blocker.native_open_blockers(runner, "7", repo="o/r") == []


def test_prose_open_blockers_parses_body_and_comment_bodies() -> None:
    comments = json.dumps([{"body": "Needs #9"}]) + json.dumps([{"body": "Blocked by #7"}])
    runner = RecordingRunner(
        responses=[
            _result(stdout=json.dumps({"title": "t", "body": "Depends on #8\nRequires #5"})),
            _result(stdout=comments),
            _result(stdout=json.dumps({"state": "closed", "url": "u"})),
            _result(stdout=json.dumps({"state": "OPEN", "url": "u"})),
            _result(rc=1),
        ]
    )
    assert blocker.prose_open_blockers(runner, "7", repo="o/r") == [8]
    assert runner.calls[1] == ["gh", "api", "/repos/o/r/issues/7/comments", "--paginate"]


def test_prose_open_blockers_keeps_comment_refs_when_body_fails() -> None:
    runner = RecordingRunner(
        responses=[
            _result(rc=1),
            _result(stdout=json.dumps([{"body": "Needs #9"}])),
            _result(stdout=json.dumps({"state": "OPEN", "url": "u"})),
        ]
    )
    assert blocker.prose_open_blockers(runner, "7", repo="o/r") == [9]


def test_prose_open_blockers_keeps_body_refs_when_comments_fail() -> None:
    runner = RecordingRunner(
        responses=[
            _result(stdout=json.dumps({"title": "t", "body": "Depends on #8"})),
            _result(rc=1),
            _result(stdout=json.dumps({"state": "OPEN", "url": "u"})),
        ]
    )
    assert blocker.prose_open_blockers(runner, "7", repo="o/r") == [8]


def test_prose_open_blockers_body_json_failure_does_not_drop_comments() -> None:
    runner = RecordingRunner(
        responses=[
            _result(stdout="not json"),
            _result(stdout=json.dumps([{"body": "Blocked by #10"}])),
            _result(stdout=json.dumps({"state": "OPEN", "url": "u"})),
        ]
    )
    assert blocker.prose_open_blockers(runner, "7", repo="o/r") == [10]


def test_all_open_blockers_short_circuits_native(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def native(_: Any, __: str, *, repo: str) -> list[int]:
        assert repo == "o/r"
        return [4]

    def prose(_: Any, __: str, *, repo: str) -> list[int]:
        nonlocal called
        assert repo == "o/r"
        called = True
        return []

    monkeypatch.setattr(blocker, "native_open_blockers", native)
    monkeypatch.setattr(blocker, "prose_open_blockers", prose)
    assert blocker.all_open_blockers(RecordingRunner(), "1", repo="o/r") == [4]
    assert called is False


def test_all_open_blockers_falls_back_to_prose(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(blocker, "native_open_blockers", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(blocker, "prose_open_blockers", lambda *_args, **_kwargs: [6])
    assert blocker.all_open_blockers(RecordingRunner(), "1", repo="o/r") == [6]


def test_all_open_cli_emit_kv(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(blocker.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(blocker.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(blocker, "all_open_blockers", lambda *_args, **_kwargs: [2, 4])
    assert blocker.all_open_blockers_main(["--issue", "1", "--repo", "o/r"]) == 0
    assert emitted == [("BLOCKERS", "2 4")]


def test_all_open_cli_empty_when_repo_unresolved(monkeypatch: pytest.MonkeyPatch) -> None:
    emitted: list[tuple[str, str]] = []
    monkeypatch.setattr(blocker.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(blocker.logging_util, "emit_kv", lambda key, value: emitted.append((key, value)))
    monkeypatch.setattr(blocker.gh, "resolve_repo", lambda _runner: None)
    assert blocker.all_open_blockers_main(["--issue", "1"]) == 0
    assert emitted == [("BLOCKERS", "")]


def test_all_open_cli_subprocess(tmp_path: Path) -> None:
    stub = tmp_path / "gh"
    stub.write_text(
        "#!/usr/bin/env bash\n"
        "if [[ $1 == api ]]; then printf '[{\"number\":12,\"state\":\"OPEN\"}]'; exit 0; fi\n"
        "echo unhandled >&2; exit 99\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    env = os.environ.copy()
    env["PATH"] = f"{tmp_path}:{env['PATH']}"
    result = subprocess.run(
        ["python3", "python/cli.py", "blocker", "all-open", "--issue", "1", "--repo", "o/r"],
        cwd=Path(__file__).resolve().parents[3],
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0
    assert "BLOCKERS=12" in result.stdout
