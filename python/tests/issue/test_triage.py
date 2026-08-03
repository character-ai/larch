# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false
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
    edited = False
    expected_body = (
        "Original report\n\n<!-- larch:triage:start -->\n"
        "## Summary\n\nCorrected diagnosis.\n<!-- larch:triage:end -->\n"
    )
    expected_title = "[TRIAGED] Bug report"

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal edited
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="[]")
        if argv[:4] == ["gh", "issue", "edit", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            assert argv[:4] == ["gh", "issue", "edit", "7"]  # lint-gh-argv-literal: ok fixture assertion
            assert "--title" in argv
            assert argv[argv.index("--title") + 1] == expected_title
            assert Path(argv[-1]).read_text(encoding="utf-8") == expected_body
            edited = True
            return _result(argv)
        if not edited:
            return _result(argv, stdout=_snapshot())
        return _result(
            argv,
            stdout=_snapshot(
                body=expected_body,
                title=expected_title,
                updated_at="2026-07-12T10:00:01Z",
            ),
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


def test_valid_apply_bug_prefix_title_gets_triaged_infix(
    monkeypatch: Any,
    capsys: Any,
    triage_root: Path,
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("## Summary\n\nRoot cause.", encoding="utf-8")
    edited = False
    expected_body = (
        "Original report\n\n<!-- larch:triage:start -->\n"
        "## Summary\n\nRoot cause.\n<!-- larch:triage:end -->\n"
    )
    expected_title = "[BUG] [TRIAGED] Crash on startup"

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal edited
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="[]")
        if argv[:4] == ["gh", "issue", "edit", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            assert "--title" in argv
            assert argv[argv.index("--title") + 1] == expected_title
            edited = True
            return _result(argv)
        if not edited:
            return _result(argv, stdout=_snapshot(title="[BUG] Crash on startup"))
        return _result(
            argv,
            stdout=_snapshot(
                body=expected_body,
                title=expected_title,
                updated_at="2026-07-12T10:00:01Z",
            ),
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
    assert "ISSUE_UPDATED=true" in capsys.readouterr().out


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("[BUG] Crash on startup", "[BUG] [TRIAGED] Crash on startup"),
        ("[BUG]  Extra space", "[BUG] [TRIAGED] Extra space"),
        ("Plain issue", "[TRIAGED] Plain issue"),
        ("[BUG] [TRIAGED] Already done", "[BUG] [TRIAGED] Already done"),
        ("[TRIAGED] Already done", "[TRIAGED] Already done"),
    ],
)
def test_triaged_title(title: str, expected: str) -> None:
    assert triage._triaged_title(title) == expected  # pyright: ignore[reportPrivateUsage]


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
        if command[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            if len(calls) == 8:
                return _result(command, stdout=json.dumps([{"body": marked}]))
            return _result(command, stdout="[]")
        position = len(calls)
        if position in {1, 4}:
            return _result(command, stdout=_snapshot())
        if position == 6:
            assert command[:4] == ["gh", "issue", "comment", "7"]  # lint-gh-argv-literal: ok fixture assertion
            return _result(command)
        if position == 7:
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
    assert len(calls) == 9
    assert not any(command[:4] == ["gh", "issue", "close", "7"] for command in calls)  # lint-gh-argv-literal: ok fixture assertion


@pytest.mark.parametrize(
    ("title", "body", "labels"),
    [
        ("[IMPLEMENTING] report", "body", []),
        ("[DEBATING] report", "body", []),
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
            list(argv),
            stdout="[]"
            if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]  # lint-gh-argv-literal: ok fixture assertion
            else _snapshot(title=title, body=body, labels=labels),
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


def test_sanitize_outbound_rejects_malformed_triage_artifacts() -> None:
    with pytest.raises(triage.TriageError, match="only one validated triage block") as error:
        triage.sanitize_outbound(
            "outside\n<!-- larch:triage:start -->\nbody\n<!-- larch:triage:end -->",
            allow_triage_block=True,
        )
    assert error.value.exit_code == triage.EXIT_REDACTION


def test_sanitize_outbound_fails_closed_when_pii_survives_redaction(
    monkeypatch: Any,
) -> None:
    monkeypatch.setattr(
        triage.redact, "redact_outbound", lambda _value: "person@example.com"
    )
    with pytest.raises(triage.TriageError, match="redaction could not be verified") as error:
        triage.sanitize_outbound("person@example.com")
    assert error.value.exit_code == triage.EXIT_REDACTION


def test_protected_marker_inside_triage_block_refuses_update() -> None:
    snapshot = triage.IssueSnapshot(
        number=7,
        repo="owner/repo",
        title="Bug report",
        body=(
            "Original report\n\n<!-- larch:triage:start -->\n"
            "<!-- larch:plan:start -->\n<!-- larch:triage:end -->\n"
        ),
        state="OPEN",
        state_reason="",
        url="https://github.com/owner/repo/issues/7",
        updated_at="2026-07-12T10:00:00Z",
        labels=(),
        comments=(),
    )
    assert triage._has_protected_state(snapshot, allow_stale_title=False)  # pyright: ignore[reportPrivateUsage]


def test_valid_apply_reports_a_verified_noop(monkeypatch: Any, capsys: Any, triage_root: Path) -> None:
    body_file = triage_root / "body.md"
    block = "<!-- larch:triage:start -->\n## Summary\n\nCorrected diagnosis.\n<!-- larch:triage:end -->"
    body_file.write_text(block, encoding="utf-8")
    existing_body = f"Original report\n\n{block}\n"
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="[]")
        return _result(argv, stdout=_snapshot(body=existing_body, title="[TRIAGED] Bug report"))

    monkeypatch.setattr(triage.proc, "run", fake_run)
    assert triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "valid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--body-file", str(body_file), "--operator-invoked",
    ]) == 0
    output = capsys.readouterr().out
    assert "ISSUE_UPDATED=false" in output
    assert "UPDATED_AT=2026-07-12T10:00:00Z" in output
    assert not any(call[:4] == ["gh", "issue", "edit", "7"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


def test_paginated_security_comment_blocks_public_mutation(
    monkeypatch: Any, triage_root: Path
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("diagnosis", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout='[]\n[{"body": "api key exposed"}]')
        return _result(argv, stdout=_snapshot())

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "valid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--body-file", str(body_file), "--operator-invoked",
    ])
    assert rc == triage.EXIT_PROTECTED
    assert not any(call[:4] == ["gh", "issue", "edit", "7"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


def test_sensitive_pending_artifact_blocks_public_mutation(
    monkeypatch: Any, triage_root: Path
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("credential exposure", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv, stdout="[]" if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"] else _snapshot())  # lint-gh-argv-literal: ok fixture assertion

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "valid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--body-file", str(body_file), "--operator-invoked",
    ])
    assert rc == triage.EXIT_PROTECTED
    assert len(calls) == 2


def test_valid_apply_rechecks_snapshot_before_body_mutation(
    monkeypatch: Any, triage_root: Path
) -> None:
    body_file = triage_root / "body.md"
    body_file.write_text("diagnosis", encoding="utf-8")
    views = 0
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal views
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="[]")
        views += 1
        return _result(argv, stdout=_snapshot(updated_at="2026-07-12T10:00:01Z" if views == 2 else "2026-07-12T10:00:00Z"))

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "valid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--body-file", str(body_file), "--operator-invoked",
    ])
    assert rc == triage.EXIT_STALE
    assert not any(call[:4] == ["gh", "issue", "edit", "7"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


def test_duplicate_requires_an_open_canonical_issue(
    monkeypatch: Any, triage_root: Path
) -> None:
    comment_file = triage_root / "comment.md"
    comment_file.write_text("Duplicate of #8.", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout="[]")
        if argv[:4] == ["gh", "issue", "view", "8"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout=_snapshot(number=8, state="CLOSED"))
        return _result(argv, stdout=_snapshot())

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "duplicate",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--comment-file", str(comment_file),
        "--canonical-duplicate", "8", "--operator-invoked",
    ])
    assert rc == triage.EXIT_PROTECTED
    assert not any(call[:4] == ["gh", "issue", "comment", "7"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


def test_conflicting_verdict_marker_blocks_close(
    monkeypatch: Any, triage_root: Path
) -> None:
    comment_file = triage_root / "comment.md"
    comment_file.write_text("Verified as invalid.", encoding="utf-8")
    comment_reads = 0
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal comment_reads
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            comment_reads += 1
            body = "<!-- larch:triage-verdict:invalid -->\nConflicting evidence."
            return _result(argv, stdout="[]" if comment_reads == 1 else json.dumps([{"body": body}]))
        return _result(argv, stdout=_snapshot())

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "invalid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--comment-file", str(comment_file), "--operator-invoked",
    ])
    assert rc == triage.EXIT_POSTCONDITION
    assert not any(call[:4] == ["gh", "issue", "close", "7"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


def test_close_restores_title_and_verifies_not_planned(
    monkeypatch: Any, triage_root: Path
) -> None:
    comment_file = triage_root / "comment.md"
    comment_file.write_text("Verified as invalid.", encoding="utf-8")
    title = "[DONE] Bug report"
    state = "OPEN"
    state_reason = ""
    updated_at = "2026-07-12T10:00:00Z"
    comments: list[dict[str, str]] = []
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal title, state, state_reason, updated_at
        calls.append(argv)
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout=json.dumps(comments))
        if argv[:4] == ["gh", "issue", "comment", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            comments.append({"body": "<!-- larch:triage-verdict:invalid -->\nVerified as invalid."})
            updated_at = "2026-07-12T10:00:01Z"
            return _result(argv)
        if argv[:4] == ["gh", "issue", "edit", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            title = "Bug report"
            updated_at = "2026-07-12T10:00:02Z"
            return _result(argv)
        if argv[:4] == ["gh", "issue", "close", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            state = "CLOSED"
            state_reason = "NOT_PLANNED"
            updated_at = "2026-07-12T10:00:03Z"
            return _result(argv)
        return _result(argv, stdout=_snapshot(
            title=title, state=state, state_reason=state_reason,
            updated_at=updated_at, comments=comments,
        ))

    monkeypatch.setattr(triage.proc, "run", fake_run)
    rc = triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "invalid",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--comment-file", str(comment_file), "--operator-invoked",
    ])
    assert rc == 0
    assert any(call[:4] == ["gh", "issue", "close", "7"] and call[-2:] == ["--reason", "not planned"] for call in calls)  # lint-gh-argv-literal: ok fixture assertion


@pytest.mark.parametrize(
    ("verdict", "canonical"),
    [("already-fixed", None), ("duplicate", 8)],
)
def test_close_successfully_applies_already_fixed_and_duplicate_verdicts(
    monkeypatch: Any, capsys: Any, triage_root: Path, verdict: str, canonical: int | None
) -> None:
    comment_file = triage_root / "comment.md"
    comment_file.write_text("Verified outcome.", encoding="utf-8")
    updated_at = "2026-07-12T10:00:00Z"
    state = "OPEN"
    state_reason = ""
    comments: list[dict[str, str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        nonlocal updated_at, state, state_reason
        if argv[:3] == ["gh", "api", "/repos/owner/repo/issues/7/comments"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout=json.dumps(comments))
        if argv[:4] == ["gh", "issue", "view", "8"]:  # lint-gh-argv-literal: ok fixture assertion
            return _result(argv, stdout=_snapshot(number=8))
        if argv[:4] == ["gh", "issue", "comment", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            content = "Verified outcome."
            if verdict == "duplicate":
                content = "Duplicate of #8.\n\nVerified outcome."
            comments.append({"body": f"<!-- larch:triage-verdict:{verdict} -->\n{content}"})
            updated_at = "2026-07-12T10:00:01Z"
            return _result(argv)
        if argv[:4] == ["gh", "issue", "close", "7"]:  # lint-gh-argv-literal: ok fixture assertion
            state = "CLOSED"
            state_reason = "NOT_PLANNED"
            updated_at = "2026-07-12T10:00:02Z"
            return _result(argv)
        return _result(
            argv,
            stdout=_snapshot(
                state=state,
                state_reason=state_reason,
                updated_at=updated_at,
                comments=comments,
            ),
        )

    monkeypatch.setattr(triage.proc, "run", fake_run)
    argv = [
        "7", "--repo", "owner/repo", "--verdict", verdict,
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--comment-file", str(comment_file), "--operator-invoked",
    ]
    if canonical is not None:
        argv.extend(["--canonical-duplicate", str(canonical)])
    assert triage.apply_main(argv) == 0
    assert f"TRIAGE_VERDICT={verdict}" in capsys.readouterr().out


def test_inconclusive_verdict_makes_no_github_calls(monkeypatch: Any, triage_root: Path) -> None:
    calls: list[list[str]] = []
    monkeypatch.setattr(triage.proc, "run", lambda argv, **_: calls.append(argv))
    assert triage.apply_main([
        "7", "--repo", "owner/repo", "--verdict", "inconclusive",
        "--expected-updated-at", "2026-07-12T10:00:00Z", "--triage-root",
        str(triage_root), "--operator-invoked",
    ]) == 0
    assert not calls


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


def test_inspect_reports_an_unavailable_immutable_main_as_an_evidence_gap(
    monkeypatch: Any, capsys: Any, tmp_path: Path
) -> None:
    sha = "a" * 40

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[-3:] == ["remote", "get-url", "origin"]:
            return _result(argv, stdout="git@github.com:owner/repo.git\n")
        if "ls-remote" in argv:
            return _result(argv, stdout=f"{sha}\trefs/heads/main\n")
        return _result(argv, returncode=1, stderr="missing")

    monkeypatch.setattr(triage.proc, "run", fake_run)
    assert triage.inspect_main(["--repo-root", str(tmp_path), "--path", "src/app.py"]) == triage.EXIT_POSTCONDITION
    output = capsys.readouterr().out
    assert "EVIDENCE_STATUS=gap" in output
    assert "immutable main object is unavailable" in output


def test_inspect_marks_truncated_evidence(monkeypatch: Any, capsys: Any, tmp_path: Path) -> None:
    sha = "a" * 40

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[-3:] == ["remote", "get-url", "origin"]:
            return _result(argv, stdout="git@github.com:owner/repo.git\n")
        if "ls-remote" in argv:
            return _result(argv, stdout=f"{sha}\trefs/heads/main\n")
        if "cat-file" in argv:
            return _result(argv)
        if "show" in argv:
            return _result(argv, stdout="ABCDE")
        raise AssertionError(argv)

    monkeypatch.setattr(triage.proc, "run", fake_run)
    assert triage.inspect_main([
        "--repo-root", str(tmp_path), "--path", "src/app.py", "--max-bytes", "3",
    ]) == 0
    output = capsys.readouterr().out
    assert "EVIDENCE_TRUNCATED=true" in output
    assert "\nABC\n" in output
    assert "ABCDE" not in output


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


def test_codex_model_probe_uses_fixed_readonly_argv(monkeypatch: Any, capsys: Any) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "secret")

    def fake_run(argv: list[str], **kwargs: object) -> proc.CommandResult:
        assert argv == [
            "codex", "exec", "--sandbox", "read-only", "--model", "gpt-5",
            "Reply with OK only.",
        ]
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "OPENAI_API_KEY" not in env
        return _result(argv, stdout="OK\n")

    monkeypatch.setattr(triage.proc, "run", fake_run)
    assert triage.probe_main(["--name", "codex-model-readonly", "--arg", "gpt-5"]) == 0
    assert "PROBE_STATUS=completed" in capsys.readouterr().out
