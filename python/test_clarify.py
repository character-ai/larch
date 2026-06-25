# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportUnknownVariableType=false
"""Tests for clarify.py."""

from __future__ import annotations

import json
import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import clarify
import config
import logging_util
import redact
from errors import ShipError
from proc import CommandResult
from test_support import RecordingRunner as _RecordingRunner


def _result(
    argv: tuple[str, ...] = ("gh",),
    rc: int = 0,
    stdout: str = "",
    stderr: str = "",
) -> CommandResult:
    return CommandResult(argv, rc, stdout, stderr, 0.01)


@dataclass
class RecordingRunner(_RecordingRunner):
    strict: bool = True


def _comments(*bodies: str) -> str:
    return json.dumps([{"body": body, "id": idx + 1} for idx, body in enumerate(bodies)])


@pytest.mark.parametrize(
    ("name", "payload", "expected"),
    [
        ("clean", "[]", clarify.ClarifyState("clean", "", "")),
        ("id0ignored", _comments("<!-- larch:clarify-request id=0 -->"), clarify.ClarifyState("clean", "", "")),
        (
            "await",
            _comments("<!-- larch:clarify-request id=1 -->"),
            clarify.ClarifyState("awaiting-response", "1", ""),
        ),
        (
            "pending",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
            ),
            clarify.ClarifyState("response-pending", "1", "1"),
        ),
        (
            "dupreq",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-request id=1 -->",
            ),
            clarify.ClarifyState("ambiguous", "1", ""),
        ),
        (
            "dupresp",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
            ),
            clarify.ClarifyState("ambiguous", "1", "1"),
        ),
        (
            "orphan",
            _comments("<!-- larch:clarify-response id=1 -->"),
            clarify.ClarifyState("ambiguous", "", "1"),
        ),
        (
            "nonmono",
            _comments(
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-request id=1 -->",
            ),
            clarify.ClarifyState("ambiguous", "1", ""),
        ),
        (
            "gap_high_response",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-response id=2 -->",
            ),
            clarify.ClarifyState("ambiguous", "2", "2"),
        ),
        (
            "multi_done",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
                "<!-- larch:clarify-response id=2 -->",
            ),
            clarify.ClarifyState("response-pending", "2", "2"),
        ),
        (
            "multi_prog",
            _comments(
                "<!-- larch:clarify-request id=1 -->",
                "<!-- larch:clarify-response id=1 -->",
                "<!-- larch:clarify-request id=2 -->",
            ),
            clarify.ClarifyState("awaiting-response", "2", "1"),
        ),
        (
            "flex_space",
            _comments("<!--   larch:clarify-request   id=1   -->"),
            clarify.ClarifyState("awaiting-response", "1", ""),
        ),
    ],
)
def test_clarify_state_matrix(name: str, payload: str, expected: clarify.ClarifyState) -> None:
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert clarify.clarify_state(runner=runner, issue="7", repo="o/r") == expected
    assert name


def test_clarify_state_flattens_paginated_chunks() -> None:
    payload = _comments("<!-- larch:clarify-request id=1 -->") + _comments(
        "<!-- larch:clarify-response id=1 -->"
    )
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert clarify.clarify_state(runner=runner, issue="7", repo="o/r").state == "response-pending"




def test_clarify_state_flattens_slurp_pages() -> None:
    payload = json.dumps([
        [{"body": "<!-- larch:clarify-request id=1 -->"}],
        [{"body": "<!-- larch:clarify-response id=1 -->"}],
    ])
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert clarify.clarify_state(runner=runner, issue="7", repo="o/r").state == "response-pending"


def test_missing_repo_resolves_with_gh_repo_view() -> None:
    runner = RecordingRunner(responses=[_result(stdout="o/r\n"), _result(stdout="[]")])
    assert clarify.clarify_state(runner=runner, issue="7", repo=None).state == "clean"
    assert runner.calls[0] == ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]


def test_comment_fetch_writes_request_body_without_stdout_body(tmp_path: Path) -> None:
    out_file = tmp_path / "request.md"
    payload = _comments(
        "<!-- larch:clarify-request id=1 -->\nsecret question\nline two",
        "<!-- larch:clarify-response id=1 -->\nold response",
        "<!-- larch:clarify-request id=2 -->\nlatest question",
    )
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    result = clarify.clarify_comment_fetch(runner=runner, issue="7", comment_id="2", out_file=str(out_file), repo="o/r")
    assert result == clarify.ClarifyCommentFetchResult(
        fetched=True,
        comment_id="3",
        body_file=str(out_file),
    )
    assert out_file.read_text(encoding="utf-8") == "latest question"


def test_comment_fetch_cli_emits_file_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_file = tmp_path / "request.md"
    runner = RecordingRunner(
        responses=[_result(stdout=_comments("<!-- larch:clarify-request id=1 -->\nquestion body"))]
    )
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_fetch_main(
        ["--issue", "7", "--id", "1", "--out", str(out_file), "--repo", "o/r"]
    )
    out = capsys.readouterr().out
    assert rc == 0
    assert "FETCHED=true" in out
    assert "BODY_FILE=" in out
    assert "question body" not in out
    assert out_file.read_text(encoding="utf-8") == "question body"


def test_comment_fetch_missing_request_cli_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    out_file = tmp_path / "request.md"
    runner = RecordingRunner(
        responses=[_result(stdout=_comments("<!-- larch:clarify-request id=1 -->\nquestion body"))]
    )
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_fetch_main(
        ["--issue", "7", "--id", "2", "--out", str(out_file), "--repo", "o/r"]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert not out_file.exists()


def test_empty_repo_resolution_cli_fails(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_result(rc=1, stderr="no repo")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_state_main(["--issue", "7"])
    assert rc == 2
    assert "FAILED=true" in capsys.readouterr().out


def test_invalid_repo_state_cli_has_no_comments_call(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_state_main(["--issue", "7", "--repo", "bad..repo"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=invalid-repo" in out
    assert not any("stage-terminal-state" in " ".join(call) for call in runner.calls)


@dataclass
class CapturingRunner:
    responses: list[CommandResult]
    calls: list[list[str]] = field(default_factory=list)
    bodies: list[str] = field(default_factory=list)
    index: int = 0

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        if "--body-file" in argv:
            body_path = Path(argv[list(argv).index("--body-file") + 1])
            self.bodies.append(body_path.read_text(encoding="utf-8"))
        result = self.responses[self.index]
        self.index += 1
        return result


def test_comment_post_redacts_body_and_parses_stripped_url(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    secret = "sk-" + "a" * 25
    content.write_text(f"hello {secret}", encoding="utf-8")
    runner = CapturingRunner(
        responses=[_result(stdout="https://github.com/o/r/issues/7#issuecomment-123\n")]
    )
    result = clarify.clarify_comment_post(
        runner=runner, issue="7", kind="request", comment_id="1", content_file=str(content), repo="o/r"
    )
    marker = "<!-- larch:clarify-request id=1 -->"
    assert result == clarify.ClarifyCommentResult(
        posted=True,
        comment_id="123",
        comment_url="https://github.com/o/r/issues/7#issuecomment-123",
        marker=marker,
    )
    assert runner.bodies == [redact.redact(f"{marker}\nhello {secret}")]
    assert secret not in runner.bodies[0]


def test_comment_post_redacts_cursor_key(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    secret = "crsr_" + "0123456789abcdefghijklmnopqrstuvwxyzABCDEF"
    content.write_text(f"hello {secret}", encoding="utf-8")
    runner = CapturingRunner(
        responses=[_result(stdout="https://github.com/o/r/issues/7#issuecomment-123\n")]
    )
    result = clarify.clarify_comment_post(
        runner=runner, issue="7", kind="request", comment_id="1", content_file=str(content), repo="o/r"
    )
    marker = "<!-- larch:clarify-request id=1 -->"
    assert result == clarify.ClarifyCommentResult(
        posted=True,
        comment_id="123",
        comment_url="https://github.com/o/r/issues/7#issuecomment-123",
        marker=marker,
    )
    assert runner.bodies == [redact.redact(f"{marker}\nhello {secret}")]
    assert secret not in runner.bodies[0]
    assert "<REDACTED-TOKEN>" in runner.bodies[0]


def test_comment_post_response_kind_and_parse_miss(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(responses=[_result(stdout="not a url\n")])
    result = clarify.clarify_comment_post(
        runner=runner, issue="7", kind="response", comment_id="2", content_file=str(content), repo="o/r"
    )
    assert result.comment_id == ""
    assert result.comment_url == "not a url"
    assert result.marker == "<!-- larch:clarify-response id=2 -->"


@pytest.mark.parametrize("bad_id", ["0", "-1", "abc"])
def test_comment_invalid_id_cli(
    bad_id: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", bad_id, "--content-file", str(content)]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "ERROR=invalid-id" in out
    assert not runner.calls


def test_comment_content_file_validation_wins_before_repo_resolution(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", "1", "--content-file", "missing.md"]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "ERROR=content file not found: missing.md" in out
    assert not runner.calls


def test_comment_invalid_issue_is_not_invalid_id(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "abc", "--kind", "request", "--id", "1", "--content-file", str(content)]
    )
    assert rc == 1
    assert "invalid-id" not in capsys.readouterr().out


def test_comment_invalid_issue_is_stderr_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "abc", "--kind", "request", "--id", "1", "--content-file", str(content)]
    )
    captured = capsys.readouterr()
    assert rc == 1
    assert captured.out == ""
    assert "positive integer" in captured.err


def test_comment_invalid_kind_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "bad", "--id", "1", "--content-file", str(content)]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=invalid-kind" in out
    assert not runner.calls


def test_comment_invalid_repo_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        [
            "--issue",
            "7",
            "--kind",
            "request",
            "--id",
            "1",
            "--content-file",
            str(content),
            "--repo",
            "bad..repo",
        ]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "ERROR=invalid-repo" in out
    assert not runner.calls


def test_comment_non_utf8_content_file_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    content = tmp_path / "content.bin"
    content.write_bytes(b"\xff\xfe\xfd")
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", "1", "--content-file", str(content), "--repo", "o/r"]
    )
    out = capsys.readouterr().out
    assert rc == 1
    assert "FAILED=true" in out
    assert "utf-8" in out
    assert not runner.calls


def test_comment_post_multiline_stdout_flattens_comment_url(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(
        responses=[_result(stdout="https://github.com/o/r/issues/7#issuecomment-5\nextra\n")]
    )
    result = clarify.clarify_comment_post(
        runner=runner, issue="7", kind="request", comment_id="1", content_file=str(content), repo="o/r"
    )
    assert result.comment_id == "5"
    assert "\n" not in result.comment_url
    assert "extra" in result.comment_url


def test_comment_transient_retry_exhaustion_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            _result(rc=1, stderr="Could not resolve host")
            for _ in range(config.TRANSIENT_RETRY_MAX_ATTEMPTS)
        ]
    )
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", "1", "--content-file", str(content), "--repo", "o/r"]
    )
    out = capsys.readouterr().out
    assert rc == 2
    assert "FAILED=true" in out
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_comment_redaction_truncation_fails_before_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(responses=[_result(stdout="unused")])
    monkeypatch.setattr(clarify.redact, "redact", lambda _text: "[content truncated boom]")
    with pytest.raises(ShipError, match="redaction failed"):
        clarify.clarify_comment_post(runner=runner, issue="7", kind="request", comment_id="1", content_file=str(content), repo="o/r")
    assert not runner.calls


def test_comment_transient_retry_fails_once_then_succeeds(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(
        responses=[
            _result(rc=1, stderr="Could not resolve host"),
            _result(stdout="https://github.com/o/r/issues/7#issuecomment-8"),
        ]
    )
    result = clarify.clarify_comment_post(
        runner=runner, issue="7", kind="request", comment_id="1", content_file=str(content), repo="o/r"
    )
    assert result.comment_id == "8"
    assert len(runner.calls) == 2


def test_label_add_create_and_metadata() -> None:
    runner = RecordingRunner(
        responses=[_result(stdout=""), _result(), _result()],
    )
    result = clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r", create_if_missing=True)
    assert result == clarify.ClarifyLabelResult(changed=True, action="add", label=clarify.LABEL_NAME)
    assert runner.calls[1] == [
        "gh",
        "label",
        "create",
        clarify.LABEL_NAME,
        "--repo",
        "o/r",
        "--color",
        clarify.LABEL_COLOR,
        "--description",
        clarify.LABEL_DESCRIPTION,
    ]
    assert runner.calls[2][-2:] == ["--add-label", clarify.LABEL_NAME]




def test_label_repeated_add_with_omitted_label_creates_each_time() -> None:
    runner = RecordingRunner(
        responses=[_result(stdout=""), _result(), _result(), _result(stdout=""), _result(), _result()],
    )
    assert clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r", create_if_missing=True).changed
    assert clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r", create_if_missing=True).changed
    create_calls = [call for call in runner.calls if call[:3] == ["gh", "label", "create"]]
    assert len(create_calls) == 2


def test_label_add_exact_present_skips_mutation() -> None:
    runner = RecordingRunner(responses=[_result(stdout=f"{clarify.LABEL_NAME}\n")])
    result = clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r", create_if_missing=True)
    assert result.changed is False
    assert len(runner.calls) == 1


def test_label_different_case_is_absent_for_add_and_remove() -> None:
    runner = RecordingRunner(responses=[_result(stdout="Needs-Design-Clarification\n"), _result()])
    assert clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r").changed is True
    runner = RecordingRunner(responses=[_result(stdout="Needs-Design-Clarification\n")])
    assert clarify.clarify_label(runner=runner, issue="7", action="remove", repo="o/r").changed is False
    assert len(runner.calls) == 1


def test_label_remove_present_calls_remove() -> None:
    runner = RecordingRunner(responses=[_result(stdout=f"{clarify.LABEL_NAME}\n"), _result()])
    assert clarify.clarify_label(runner=runner, issue="7", action="remove", repo="o/r").changed is True
    assert runner.calls[1][-2:] == ["--remove-label", clarify.LABEL_NAME]


@pytest.mark.parametrize("message", ["already exists", "ALREADY BEEN TAKEN"])
def test_label_duplicate_create_errors_are_nonfatal(message: str) -> None:
    runner = RecordingRunner(responses=[_result(), _result(rc=1, stderr=message), _result()])
    assert clarify.clarify_label(runner=runner, issue="7", action="add", repo="o/r", create_if_missing=True).changed


@pytest.mark.parametrize("action", ["add", "remove"])
def test_label_mutation_failure_raises(action: str) -> None:
    labels = "" if action == "add" else f"{clarify.LABEL_NAME}\n"
    runner = RecordingRunner(responses=[_result(stdout=labels), _result(rc=1, stderr="boom")])
    with pytest.raises(ShipError, match="boom"):
        clarify.clarify_label(runner=runner, issue="7", action=action, repo="o/r")


def test_label_invalid_issue_and_action_are_stderr_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    assert clarify.clarify_label_main(["--issue", "0", "--action", "add"]) == 1
    first = capsys.readouterr()
    assert first.out == ""
    assert not runner.calls
    assert clarify.clarify_label_main(["--issue", "7", "--action", "bad"]) == 1
    second = capsys.readouterr()
    assert second.out == ""
    assert not runner.calls


def test_label_invalid_repo_cli(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(responses=[])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_label_main(["--issue", "7", "--action", "add", "--repo", "bad..repo"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "ERROR=invalid-repo" in out
    assert not runner.calls


def test_label_add_failure_cli_redacts_and_caps(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret = "ghp_" + "a" * 25
    runner = RecordingRunner(responses=[_result(stdout=""), _result(rc=1, stderr=secret + "x" * 600)])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    rc = clarify.clarify_label_main(["--issue", "7", "--action", "add", "--repo", "o/r"])
    out = capsys.readouterr().out
    error_line = next(line for line in out.splitlines() if line.startswith("ERROR="))
    assert rc == 2
    assert secret not in error_line
    assert len(error_line.removeprefix("ERROR=")) <= 500


def test_clarify_state_emits_kv_on_fd3_under_quiet_mode(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(responses=[_result(stdout="[]")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    logging_util.reset_quiet_state()
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        _ = os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = clarify.clarify_state_main(["--issue", "7", "--repo", "o/r"])
        _ = os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 4096).decode("utf-8")
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
        logging_util.reset_quiet_state()
    assert rc == 0
    assert "STATE=clean\n" in contract
    assert "LAST_REQUEST_ID=\n" in contract


def test_success_outputs_go_through_emit_kv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: list[tuple[str, str]] = []
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[_result(stdout="url#issuecomment-9\n")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(clarify.logging_util, "emit_kv", lambda *, key, value: emitted.append((key, value)))  # type: ignore[arg-type]
    assert clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", "1", "--content-file", str(content), "--repo", "o/r"]
    ) == 0
    assert emitted == [
        ("POSTED", "true"),
        ("COMMENT_ID", "9"),
        ("COMMENT_URL", "url#issuecomment-9"),
        ("MARKER", "<!-- larch:clarify-request id=1 -->"),
    ]


class DesignRunner:
    def __init__(self, responses: list[CommandResult] | None = None) -> None:
        self.responses = responses or []
        self.calls: list[list[str]] = []

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        self.calls.append(list(argv))
        if self.responses:
            return self.responses.pop(0)
        return _result(tuple(argv))


def _write_source_env(path: Path, design_tmpdir: Path, *, session_id: str = "RUN1", repo: str = "") -> None:
    rows = [
        f"export DESIGN_TMPDIR='{design_tmpdir}'",
        f"export SESSION_ID='{session_id}'",
    ]
    if repo:
        rows.append(f"export REPO='{repo}'")
    path.write_text("\n".join(rows) + "\n", encoding="utf-8")


def _design_args(source_env: Path, phase: str = "fetch") -> list[str]:
    return ["--session-env-path", str(source_env), "--claude-pid", "123", "--phase", phase, "--issue", "7"]


def test_design_clarify_env_merge_and_fetch_happy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="owner/from-file")
    monkeypatch.setenv("REPO", "owner/from-env")
    runner = DesignRunner()
    monkeypatch.setattr(clarify, "proc", runner)

    def fake_state(*, runner: object, issue: str, repo: str | None, cwd: str | None = None) -> clarify.ClarifyState:
        _ = runner, cwd
        assert issue == "7"
        assert repo == "owner/from-file"
        return clarify.ClarifyState("awaiting-response", "4", "")

    def fake_fetch(
        *,
        runner: object,
        issue: str,
        comment_id: str,
        out_file: str,
        repo: str | None,
        cwd: str | None = None,
    ) -> clarify.ClarifyCommentFetchResult:
        _ = runner, cwd
        assert issue == "7"
        assert comment_id == "4"
        assert repo == "owner/from-file"
        Path(out_file).write_text("question\n", encoding="utf-8")
        return clarify.ClarifyCommentFetchResult(fetched=True, comment_id="44", body_file=out_file)

    monkeypatch.setattr(clarify, "clarify_state", fake_state)
    monkeypatch.setattr(clarify, "clarify_comment_fetch", fake_fetch)
    assert clarify.design_clarify_main(_design_args(source_env)) == 0
    out = capsys.readouterr().out
    assert "CLARIFY_FETCH_STATUS=ok" in out
    assert "REQUEST_ID=4" in out
    assert "REPO=owner/from-file" in out
    result_env = (tmp_path / ".design-clarify-fetch-result.env").read_text(encoding="utf-8")
    assert "CLARIFY_FETCH_STATUS=ok\n" in result_env
    assert (tmp_path / "clarify-request.md").read_text(encoding="utf-8") == "question\n"


def test_design_clarify_absent_route_state_is_benign(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="")
    monkeypatch.setattr(
        clarify,
        "clarify_state",
        lambda *_args, **_kwargs: clarify.ClarifyState("awaiting-response", "1", ""),
    )

    def fake_fetch(
        *,
        runner: object,
        issue: str,
        comment_id: str,
        out_file: str,
        **_kwargs: object,
    ) -> clarify.ClarifyCommentFetchResult:
        _ = runner, issue, comment_id
        Path(out_file).write_text("question", encoding="utf-8")
        return clarify.ClarifyCommentFetchResult(fetched=True, comment_id="11", body_file=out_file)

    monkeypatch.setattr(clarify, "clarify_comment_fetch", fake_fetch)
    assert clarify.design_clarify_main(_design_args(source_env)) == 0
    assert "REPO=" not in (tmp_path / ".design-clarify-fetch-result.env").read_text(encoding="utf-8")


def test_design_clarify_route_state_failure_is_phase_split(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="")
    (tmp_path / "target.env").write_text("REPO=owner/repo\n", encoding="utf-8")
    (tmp_path / ".design-step0-route-state.env").symlink_to(tmp_path / "target.env")
    runner = DesignRunner()
    monkeypatch.setattr(clarify, "proc", runner)

    assert clarify.design_clarify_main(_design_args(source_env, "fetch")) == 1
    assert "CLARIFY_FETCH_STATUS=route-state-read-failed" in (
        tmp_path / ".design-clarify-fetch-result.env"
    ).read_text(encoding="utf-8")
    assert (tmp_path / "design-clarify-stage.stdout.log").is_file()
    assert (tmp_path / "design-failure-terminal-state.env").is_file()

    runner.calls.clear()
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 1
    assert "CLARIFY_PUBLISH_STATUS=route-state-read-failed" in (
        tmp_path / ".design-clarify-publish-result.env"
    ).read_text(encoding="utf-8")
    assert not runner.calls


@pytest.mark.parametrize(
    ("state", "request_id", "expected"),
    [
        ("clean", "", "unexpected-state"),
        ("awaiting-response", "", "unexpected-state"),
    ],
)
def test_design_clarify_fetch_failure_tokens_include_summary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    state: str,
    request_id: str,
    expected: str,
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="owner/repo")
    monkeypatch.setattr(clarify, "proc", DesignRunner())
    monkeypatch.setattr(
        clarify,
        "clarify_state",
        lambda *_args, **_kwargs: clarify.ClarifyState(state, request_id, ""),
    )
    assert clarify.design_clarify_main(_design_args(source_env)) == 1
    result = (tmp_path / ".design-clarify-fetch-result.env").read_text(encoding="utf-8")
    assert f"CLARIFY_FETCH_STATUS={expected}\n" in result
    assert "SUMMARY_OUTCOME=failed-clarify\n" in result


def test_design_clarify_fetch_direct_call_maps_state_and_fetch_failures(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="owner/repo")
    monkeypatch.setattr(clarify, "proc", DesignRunner())
    monkeypatch.setattr(clarify, "clarify_state", lambda *_args, **_kwargs: (_ for _ in ()).throw(ShipError("boom")))
    assert clarify.design_clarify_main(_design_args(source_env)) == 1
    assert "CLARIFY_FETCH_STATUS=state-failed" in (
        tmp_path / ".design-clarify-fetch-result.env"
    ).read_text(encoding="utf-8")

    monkeypatch.setattr(
        clarify,
        "clarify_state",
        lambda *_args, **_kwargs: clarify.ClarifyState("awaiting-response", "1", ""),
    )
    monkeypatch.setattr(
        clarify,
        "clarify_comment_fetch",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(clarify._ClarifyValidationError("bad")),  # pyright: ignore[reportPrivateUsage]
    )
    assert clarify.design_clarify_main(_design_args(source_env)) == 1
    assert "CLARIFY_FETCH_STATUS=fetch-failed" in (
        tmp_path / ".design-clarify-fetch-result.env"
    ).read_text(encoding="utf-8")


def test_design_clarify_pause_terminates_before_fetch_work(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, repo="owner/repo")
    (tmp_path / ".pause-requested").write_text("", encoding="utf-8")

    def fail_state(*_args: object, **_kwargs: object) -> clarify.ClarifyState:
        raise AssertionError("clarify_state should not run after pause")

    def fake_pause(argv: Sequence[str]) -> int:
        assert "--design-tmpdir" in argv
        print("PAUSE_OK=true")
        return 0

    monkeypatch.setattr(clarify, "clarify_state", fail_state)
    monkeypatch.setattr(clarify.design_pause, "pause_save_main", fake_pause)
    assert clarify.design_clarify_main(_design_args(source_env)) == 0
    assert "PAUSE_OK=true" in capsys.readouterr().out


def test_design_clarify_write_result_env_trust_boundaries(tmp_path: Path) -> None:
    target = tmp_path / "result.env"
    link = tmp_path / "link.env"
    link.symlink_to(target)
    with pytest.raises(clarify._ClarifyValidationError):  # pyright: ignore[reportPrivateUsage]
        clarify._write_result_env(path=link, rows=[("A", "1")])  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(clarify._ClarifyValidationError):  # pyright: ignore[reportPrivateUsage]
        clarify._write_result_env(path=target, rows=[("A", "bad\nvalue")])  # pyright: ignore[reportPrivateUsage]
    clarify._write_result_env(path=target, rows=[("A", "1"), ("B", "2")])  # pyright: ignore[reportPrivateUsage]
    assert target.read_text(encoding="utf-8") == "A=1\nB=2\n"
    assert not list(tmp_path.glob(".result.env.*"))


def test_design_clarify_read_result_env_trust_boundaries(tmp_path: Path) -> None:
    source = tmp_path / "state.env"
    source.write_text("REQUEST_ID=2\nIGNORED=x\nPLAN_FILE=plan.md\n", encoding="utf-8")
    assert clarify._read_result_env(path=source, allow_keys=clarify.REQUEST_STATE_ALLOW) == {  # pyright: ignore[reportPrivateUsage]
        "REQUEST_ID": "2",
        "PLAN_FILE": "plan.md",
    }
    link = tmp_path / "link.env"
    link.symlink_to(source)
    with pytest.raises(OSError, match="regular file"):
        clarify._read_result_env(path=link, allow_keys=clarify.REQUEST_STATE_ALLOW)  # pyright: ignore[reportPrivateUsage]
    with pytest.raises(OSError, match="regular file"):
        clarify._read_result_env(path=tmp_path / "missing.env", allow_keys=clarify.REQUEST_STATE_ALLOW)  # pyright: ignore[reportPrivateUsage]


def _seed_publish(tmp_path: Path, *, request_id: str = "2", session_id: str = "RUN1") -> Path:
    source_env = tmp_path / "source-env.sh"
    _write_source_env(source_env, tmp_path, session_id=session_id, repo="owner/repo")
    plan = tmp_path / "clarify-plan.md"
    response = tmp_path / "clarify-response.md"
    plan.write_text("## Plan\n\nDo it.\n", encoding="utf-8")
    response.write_text("Response.\n", encoding="utf-8")
    (tmp_path / ".design-clarify-request.env").write_text(
        "\n".join(
            [
                f"REQUEST_ID={request_id}",
                f"REQUEST_BODY_FILE={tmp_path / 'clarify-request.md'}",
                f"PLAN_FILE={plan}",
                f"RESPONSE_FILE={response}",
                "ISSUE_NUMBER=7",
                "REPO=owner/repo",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return source_env


def test_design_clarify_publish_happy_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_env = _seed_publish(tmp_path)
    runner = DesignRunner(
        [
            _result(stdout="PLAN_WRITE_OK=true\n"),
            _result(stdout="PUBLISH_OK=true\n"),
            _result(stdout="RENAMED=true\n"),
        ]
    )
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(
        clarify,
        "clarify_comment_post",
        lambda *_args, **_kwargs: clarify.ClarifyCommentResult(
            posted=True,
            comment_id="123",
            comment_url="url",
            marker="marker",
        ),
    )
    monkeypatch.setattr(
        clarify,
        "clarify_label",
        lambda *_args, **_kwargs: clarify.ClarifyLabelResult(
            changed=True,
            action="remove",
            label=clarify.LABEL_NAME,
        ),
    )
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 0
    out = capsys.readouterr().out
    assert "CLARIFY_PUBLISH_STATUS=ok" in out
    assert "PUBLISH_OK=true" in out
    assert "RENAMED=true" in out
    assert any(call[2:4] == ["named-block", "write"] for call in runner.calls)
    assert any(call[2:4] == ["design", "log-publish"] for call in runner.calls)
    assert any(call[2:4] == ["tracking-issue", "rename"] for call in runner.calls)
    assert "<REDACTED-TOKEN>" not in (tmp_path / "clarify-plan.redacted.md").read_text(encoding="utf-8")


def test_design_clarify_publish_empty_session_warns_and_skips_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_env = _seed_publish(tmp_path, session_id="")
    runner = DesignRunner([_result(stdout="PLAN_WRITE_OK=true\n")])
    monkeypatch.setattr(clarify, "proc", runner)

    def ok_comment_post(*_args: object, **_kwargs: object) -> clarify.ClarifyCommentResult:
        return clarify.ClarifyCommentResult(
            posted=True,
            comment_id="123",
            comment_url="url",
            marker="marker",
        )

    monkeypatch.setattr(clarify, "clarify_comment_post", ok_comment_post)
    monkeypatch.setattr(
        clarify,
        "clarify_label",
        lambda *_args, **_kwargs: clarify.ClarifyLabelResult(
            changed=True,
            action="remove",
            label=clarify.LABEL_NAME,
        ),
    )
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 0
    out = capsys.readouterr().out
    assert "SESSION_ID missing" in out
    assert "PUBLISH_OK=false" in out
    assert not any(call[2:4] == ["design", "log-publish"] for call in runner.calls)
    assert not any(call[2:4] == ["tracking-issue", "rename"] for call in runner.calls)


def test_design_clarify_publish_invalid_request_id_exits_2_without_result_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    source_env = _seed_publish(tmp_path, request_id="0")
    runner = DesignRunner()
    monkeypatch.setattr(clarify, "proc", runner)
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 2
    captured = capsys.readouterr()
    assert "REQUEST_ID must be a positive integer" in captured.err
    assert not (tmp_path / ".design-clarify-publish-result.env").exists()
    assert not runner.calls


def test_design_clarify_publish_failure_paths(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source_env = _seed_publish(tmp_path)
    (tmp_path / "clarify-plan.md").unlink()
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 1
    assert "CLARIFY_PUBLISH_STATUS=missing-artifact" in (
        tmp_path / ".design-clarify-publish-result.env"
    ).read_text(encoding="utf-8")

    source_env = _seed_publish(tmp_path)
    runner = DesignRunner([_result(rc=1, stderr="plan failed\n")])
    monkeypatch.setattr(clarify, "proc", runner)
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 1
    assert "CLARIFY_PUBLISH_STATUS=plan-write-failed" in (
        tmp_path / ".design-clarify-publish-result.env"
    ).read_text(encoding="utf-8")

    source_env = _seed_publish(tmp_path)
    runner = DesignRunner([_result(stdout=""), _result(rc=9, stderr="publish failed\n"), _result(stdout="")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(
        clarify,
        "clarify_comment_post",
        lambda *_args, **_kwargs: clarify.ClarifyCommentResult(
            posted=True,
            comment_id="123",
            comment_url="url",
            marker="marker",
        ),
    )
    monkeypatch.setattr(
        clarify,
        "clarify_label",
        lambda *_args, **_kwargs: clarify.ClarifyLabelResult(
            changed=True,
            action="remove",
            label=clarify.LABEL_NAME,
        ),
    )
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 0
    assert "PUBLISH_OK=false" in (tmp_path / ".design-clarify-publish-result.env").read_text(encoding="utf-8")
    assert any(call[2:4] == ["run-log", "append-failure"] for call in runner.calls)

    source_env = _seed_publish(tmp_path, session_id="")
    runner = DesignRunner([_result(stdout="PLAN_WRITE_OK=true\n")])
    monkeypatch.setattr(clarify, "proc", runner)

    def fail_comment_post(*_args: object, **_kwargs: object) -> clarify.ClarifyCommentResult:
        raise ShipError("comment post failed")

    monkeypatch.setattr(clarify, "clarify_comment_post", fail_comment_post)
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 1
    result = (tmp_path / ".design-clarify-publish-result.env").read_text(encoding="utf-8")
    assert "CLARIFY_PUBLISH_STATUS=comment-post-failed\n" in result
    assert "PLAN_WRITE_OK=true\n" in result
    assert "SUMMARY_OUTCOME=failed-clarify\n" in result

    source_env = _seed_publish(tmp_path, session_id="")
    runner = DesignRunner([_result(stdout="PLAN_WRITE_OK=true\n")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(
        clarify,
        "clarify_comment_post",
        lambda *_args, **_kwargs: clarify.ClarifyCommentResult(
            posted=True,
            comment_id="123",
            comment_url="url",
            marker="marker",
        ),
    )

    def fail_label_remove(*_args: object, **_kwargs: object) -> clarify.ClarifyLabelResult:
        raise ShipError("label remove failed")

    monkeypatch.setattr(clarify, "clarify_label", fail_label_remove)
    assert clarify.design_clarify_main(_design_args(source_env, "publish")) == 1
    result = (tmp_path / ".design-clarify-publish-result.env").read_text(encoding="utf-8")
    assert "CLARIFY_PUBLISH_STATUS=label-remove-failed\n" in result
    assert "PLAN_WRITE_OK=true\n" in result
    assert "SUMMARY_OUTCOME=failed-clarify\n" in result
