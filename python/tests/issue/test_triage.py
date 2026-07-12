"""Tests for immutable evidence, safe probes, and triage mutation gates."""
# pylint: disable=missing-function-docstring,redefined-outer-name,too-many-arguments  # pytest cases and fixtures are self-describing

from __future__ import annotations

import json
import shutil
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any

import pytest

from larch.core import proc
from larch.issue import triage


def _result(
    argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = ""
) -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def _snapshot(
    *,
    body: str = "Original report",
    title: str = "Bug report",
    state: str = "OPEN",
    state_reason: str = "",
    updated_at: str = "2026-07-12T10:00:00Z",
    labels: list[dict[str, str]] | None = None,
    comments: list[dict[str, str]] | None = None,
    number: int = 7,
) -> str:
    return json.dumps(
        {
            "number": number,
            "title": title,
            "body": body,
            "state": state,
            "stateReason": state_reason,
            "url": f"https://github.com/owner/repo/issues/{number}",
            "updatedAt": updated_at,
            "labels": labels or [],
            "comments": comments or [],
        },
    )


@pytest.fixture
def triage_root() -> Generator[Path, None, None]:
    root = Path(tempfile.mkdtemp(prefix="claude-triage-", dir="/tmp"))
    try:
        yield root
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_apply_missing_operator_authorization_makes_zero_github_calls(
    monkeypatch: Any, triage_root: Path
) -> None:
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    body = triage_root / "body.md"
    body.write_text("diagnosis", encoding="utf-8")
    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main(
        [
            "7",
            "--repo",
            "owner/repo",
            "--verdict",
            "valid",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
            "--triage-root",
            str(triage_root),
            "--body-file",
            str(body),
        ],
    )
    assert rc == triage.EXIT_AUTHORIZATION
    assert not calls


def test_valid_apply_preserves_original_and_verifies_readback(
    monkeypatch: Any,
    capsys: Any,
    triage_root: Path,
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("## Summary\n\nCorrected diagnosis.", encoding="utf-8")
    calls = 0
    expected_body = (
        "Original report\n\n<!-- larch:triage:start -->\n"
        "## Summary\n\nCorrected diagnosis.\n<!-- larch:triage:end -->\n"
    )

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        if calls == 1:
            return _result(argv, stdout=_snapshot())
        if calls == 2:
            assert argv[:4] == ["gh", "issue", "edit", "7"]
            assert Path(argv[-1]).read_text(encoding="utf-8") == expected_body
            return _result(argv)
        return _result(
            argv,
            stdout=_snapshot(body=expected_body, updated_at="2026-07-12T10:00:01Z"),
        )

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main(
        [
            "7",
            "--repo",
            "owner/repo",
            "--verdict",
            "valid",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
            "--triage-root",
            str(triage_root),
            "--body-file",
            str(body_file),
            "--operator-invoked",
        ],
    )
    assert rc == 0
    output = capsys.readouterr().out
    assert "TRIAGE_VERDICT=valid" in output
    assert "ISSUE_UPDATED=true" in output
    assert "UPDATED_AT=2026-07-12T10:00:01Z" in output


def test_stale_snapshot_refuses_before_mutation(
    monkeypatch: Any, capsys: Any, triage_root: Path
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("diagnosis", encoding="utf-8")
    calls = 0

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal calls
        calls += 1
        return _result(argv, stdout=_snapshot(updated_at="2026-07-12T10:00:02Z"))

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main(
        [
            "7",
            "--repo",
            "owner/repo",
            "--verdict",
            "valid",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
            "--triage-root",
            str(triage_root),
            "--body-file",
            str(body_file),
            "--operator-invoked",
        ],
    )
    assert rc == triage.EXIT_STALE
    assert calls == 1
    assert "TRIAGE_FAILURE=stale-snapshot" in capsys.readouterr().err


def test_close_stops_when_snapshot_changes_between_mutations(
    monkeypatch: Any,
    triage_root: Path,
) -> None:
    comment_file = triage_root / "comment.md"
    comment_file.write_text("Verified as invalid.", encoding="utf-8")
    calls: list[list[str]] = []
    marked = "<!-- larch:triage-verdict:invalid -->\nVerified as invalid."

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        command = list(argv)
        calls.append(command)
        position = len(calls)
        if position in {1, 2}:
            return _result(command, stdout=_snapshot())
        if position == 3:
            assert command[:4] == ["gh", "issue", "comment", "7"]
            return _result(command)
        if position == 4:
            return _result(
                command,
                stdout=_snapshot(
                    updated_at="2026-07-12T10:00:01Z",
                    comments=[{"body": marked}],
                ),
            )
        return _result(
            command,
            stdout=_snapshot(
                updated_at="2026-07-12T10:00:02Z",
                comments=[{"body": marked}],
            ),
        )

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main(
        [
            "7",
            "--repo",
            "owner/repo",
            "--verdict",
            "invalid",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
            "--triage-root",
            str(triage_root),
            "--comment-file",
            str(comment_file),
            "--operator-invoked",
        ],
    )
    assert rc == triage.EXIT_STALE
    assert len(calls) == 5
    assert not any(command[:4] == ["gh", "issue", "close", "7"] for command in calls)


@pytest.mark.parametrize(
    ("title", "body", "labels"),
    [
        ("[IMPLEMENTING] report", "body", []),
        ("report", "<!-- larch:plan:start -->", []),
        ("report", "body", [{"name": "needs-clarification"}]),
        ("Credential exposure", "body", []),
    ],
)
def test_protected_and_security_state_refuses(
    monkeypatch: Any,
    triage_root: Path,
    title: str,
    body: str,
    labels: list[dict[str, str]],
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("diagnosis", encoding="utf-8")
    monkeypatch.setattr(
        triage.proc,
        "run",
        lambda argv, **_: _result(
            list(argv), stdout=_snapshot(title=title, body=body, labels=labels)
        ),
    )
    rc = triage.apply_main(
        [
            "7",
            "--repo",
            "owner/repo",
            "--verdict",
            "valid",
            "--expected-updated-at",
            "2026-07-12T10:00:00Z",
            "--triage-root",
            str(triage_root),
            "--body-file",
            str(body_file),
            "--operator-invoked",
        ],
    )
    assert rc == triage.EXIT_PROTECTED


def test_sanitize_outbound_redacts_and_neutralizes() -> None:
    raw = (
        "mail me at person@example.com http://10.1.2.3/x <!-- larch:plan:start --> sk-"
        + "a" * 24
    )
    sanitized = triage.sanitize_outbound(raw)
    assert "person@example.com" not in sanitized
    assert "http://10.1.2.3" not in sanitized
    assert "<!-- larch:" not in sanitized
    assert "<REDACTED-PII>" in sanitized
    assert "<INTERNAL-URL>" in sanitized
    assert "<REDACTED-TOKEN>" in sanitized


def test_inspect_reads_only_immutable_git_object(
    monkeypatch: Any, capsys: Any, tmp_path: Path
) -> None:
    sha = "a" * 40
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        command = list(argv)
        calls.append(command)
        if command[-3:] == ["remote", "get-url", "origin"]:
            return _result(command, stdout="git@github.com:owner/repo.git\n")
        if "ls-remote" in command:
            return _result(command, stdout=f"{sha}\trefs/heads/main\n")
        if "cat-file" in command:
            return _result(command)
        if "show" in command:
            assert command[-1] == f"{sha}:src/app.py"
            return _result(command, stdout="immutable content\n")
        raise AssertionError(command)

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.inspect_main(
        [
            "--repo-root",
            str(tmp_path),
            "--ref",
            "refs/heads/main",
            "--path",
            "src/app.py",
        ],
    )
    assert rc == 0
    assert all("checkout" not in call and "reset" not in call for call in calls)
    output = capsys.readouterr().out
    assert f"IMMUTABLE_SHA={sha}" in output
    assert "immutable content" in output


@pytest.mark.parametrize("value", ["../secret", "/etc/passwd", "--option", "bad\\path"])
def test_inspect_rejects_unsafe_paths_without_git_calls(
    monkeypatch: Any, tmp_path: Path, value: str
) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(triage.proc, "run", lambda argv, **_: calls.append(list(argv)))
    assert (
        triage.inspect_main(["--repo-root", str(tmp_path), "--path", value])
        == triage.EXIT_USAGE
    )
    assert not calls


def test_probe_rejects_shell_syntax_without_execution(monkeypatch: Any) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(triage.proc, "run", lambda argv, **_: calls.append(list(argv)))
    rc = triage.probe_main(["--name", "codex-model-readonly", "--arg", "model;rm"])
    assert rc == triage.EXIT_USAGE
    assert not calls


def test_probe_runs_fixed_argv_with_scrubbed_environment(
    monkeypatch: Any, capsys: Any
) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    def fake_run(argv: list[str], **kwargs: object) -> proc.CommandResult:
        assert argv == ["git", "--version"]
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "OPENAI_API_KEY" not in env
        return _result(argv, stdout="git version 2.0\n")

    monkeypatch.setattr(triage.proc, "run", fake_run)
    assert triage.probe_main(["--name", "git-version"]) == 0
    assert "PROBE_STATUS=completed" in capsys.readouterr().out
