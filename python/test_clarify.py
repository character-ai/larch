# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportUnknownVariableType=false
"""Tests for clarify.py."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import clarify
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
    assert clarify.clarify_state(runner, "7", repo="o/r") == expected
    assert name


def test_clarify_state_flattens_paginated_chunks() -> None:
    payload = _comments("<!-- larch:clarify-request id=1 -->") + _comments(
        "<!-- larch:clarify-response id=1 -->"
    )
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert clarify.clarify_state(runner, "7", repo="o/r").state == "response-pending"




def test_clarify_state_flattens_slurp_pages() -> None:
    payload = json.dumps([
        [{"body": "<!-- larch:clarify-request id=1 -->"}],
        [{"body": "<!-- larch:clarify-response id=1 -->"}],
    ])
    runner = RecordingRunner(responses=[_result(stdout=payload)])
    assert clarify.clarify_state(runner, "7", repo="o/r").state == "response-pending"


def test_missing_repo_resolves_with_gh_repo_view() -> None:
    runner = RecordingRunner(responses=[_result(stdout="o/r\n"), _result(stdout="[]")])
    assert clarify.clarify_state(runner, "7", repo=None).state == "clean"
    assert runner.calls[0] == ["gh", "repo", "view", "--json", "nameWithOwner", "--jq", ".nameWithOwner"]


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
    assert not runner.calls


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
        runner, "7", "request", "1", str(content), repo="o/r"
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


def test_comment_post_response_kind_and_parse_miss(tmp_path: Path) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(responses=[_result(stdout="not a url\n")])
    result = clarify.clarify_comment_post(
        runner, "7", "response", "2", str(content), repo="o/r"
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


def test_comment_redaction_truncation_fails_before_post(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = CapturingRunner(responses=[_result(stdout="unused")])
    monkeypatch.setattr(clarify.redact, "redact", lambda _text: "[content truncated boom]")
    with pytest.raises(ShipError, match="redaction failed"):
        clarify.clarify_comment_post(runner, "7", "request", "1", str(content), repo="o/r")
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
        runner, "7", "request", "1", str(content), repo="o/r"
    )
    assert result.comment_id == "8"
    assert len(runner.calls) == 2


def test_label_add_create_and_metadata() -> None:
    runner = RecordingRunner(
        responses=[_result(stdout=""), _result(), _result()],
    )
    result = clarify.clarify_label(runner, "7", "add", repo="o/r", create_if_missing=True)
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
    assert clarify.clarify_label(runner, "7", "add", repo="o/r", create_if_missing=True).changed
    assert clarify.clarify_label(runner, "7", "add", repo="o/r", create_if_missing=True).changed
    create_calls = [call for call in runner.calls if call[:3] == ["gh", "label", "create"]]
    assert len(create_calls) == 2


def test_label_add_exact_present_skips_mutation() -> None:
    runner = RecordingRunner(responses=[_result(stdout=f"{clarify.LABEL_NAME}\n")])
    result = clarify.clarify_label(runner, "7", "add", repo="o/r", create_if_missing=True)
    assert result.changed is False
    assert len(runner.calls) == 1


def test_label_different_case_is_absent_for_add_and_remove() -> None:
    runner = RecordingRunner(responses=[_result(stdout="Needs-Design-Clarification\n"), _result()])
    assert clarify.clarify_label(runner, "7", "add", repo="o/r").changed is True
    runner = RecordingRunner(responses=[_result(stdout="Needs-Design-Clarification\n")])
    assert clarify.clarify_label(runner, "7", "remove", repo="o/r").changed is False
    assert len(runner.calls) == 1


def test_label_remove_present_calls_remove() -> None:
    runner = RecordingRunner(responses=[_result(stdout=f"{clarify.LABEL_NAME}\n"), _result()])
    assert clarify.clarify_label(runner, "7", "remove", repo="o/r").changed is True
    assert runner.calls[1][-2:] == ["--remove-label", clarify.LABEL_NAME]


@pytest.mark.parametrize("message", ["already exists", "ALREADY BEEN TAKEN"])
def test_label_duplicate_create_errors_are_nonfatal(message: str) -> None:
    runner = RecordingRunner(responses=[_result(), _result(rc=1, stderr=message), _result()])
    assert clarify.clarify_label(runner, "7", "add", repo="o/r", create_if_missing=True).changed


@pytest.mark.parametrize("action", ["add", "remove"])
def test_label_mutation_failure_raises(action: str) -> None:
    labels = "" if action == "add" else f"{clarify.LABEL_NAME}\n"
    runner = RecordingRunner(responses=[_result(stdout=labels), _result(rc=1, stderr="boom")])
    with pytest.raises(ShipError, match="boom"):
        clarify.clarify_label(runner, "7", action, repo="o/r")


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


def test_success_outputs_go_through_emit_kv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    emitted: list[tuple[str, str]] = []
    content = tmp_path / "content.md"
    content.write_text("body", encoding="utf-8")
    runner = RecordingRunner(responses=[_result(stdout="url#issuecomment-9\n")])
    monkeypatch.setattr(clarify, "proc", runner)
    monkeypatch.setattr(clarify.logging_util, "quiet_init", lambda **_: None)
    monkeypatch.setattr(clarify.logging_util, "emit_kv", lambda k, v: emitted.append((k, v)))
    assert clarify.clarify_comment_post_main(
        ["--issue", "7", "--kind", "request", "--id", "1", "--content-file", str(content), "--repo", "o/r"]
    ) == 0
    assert emitted == [
        ("POSTED", "true"),
        ("COMMENT_ID", "9"),
        ("COMMENT_URL", "url#issuecomment-9"),
        ("MARKER", "<!-- larch:clarify-request id=1 -->"),
    ]
