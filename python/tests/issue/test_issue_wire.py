"""Tests for issue_wire.py parity surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING

from larch.git import gh
from larch.issue import issue_wire
from larch.core import retry
from larch.core.proc import CommandResult

if TYPE_CHECKING:
    import pytest


def test_emit_untrusted_content_block_matches_file_block_redaction(
    tmp_path: Path,
) -> None:
    raw = "<tag> sk-" + "A" * 24 + " & text"
    file_path = tmp_path / "raw.txt"
    _ = file_path.write_text(raw, encoding="utf-8")
    assert issue_wire.emit_untrusted_content_block(
        tag="sample", text=raw
    ) == issue_wire.emit_untrusted_file_block(tag="sample", path=file_path)
    out = issue_wire.emit_untrusted_content_block(tag="sample", text=raw)
    assert "&lt;tag&gt;" in out
    assert "&lt;REDACTED-TOKEN&gt;" in out


def _empty_str_list() -> list[str]:
    return []


def _empty_call_list() -> list[list[str]]:
    return []


@dataclass
class IssueRunner:
    body: str
    title: str = "Regular issue"
    edit_bodies: list[str] = field(default_factory=_empty_str_list)
    calls: list[list[str]] = field(default_factory=_empty_call_list)
    edit_failures: int = 0
    persist_edits: bool = True
    updated_at: str = "2026-07-19T00:00:00Z"

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
        args = list(argv)
        self.calls.append(args)
        if args[:4] == [
            "gh",
            "issue",
            "view",
            "9",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            labels: list[object] = []
            payload: dict[str, object] = {
                "title": self.title,
                "body": self.body,
                "labels": labels,
                "state": "OPEN",
                "updatedAt": self.updated_at,
            }
            return CommandResult(
                tuple(args), 0, __import__("json").dumps(payload), "", 0.01
            )
        if args[:4] == [
            "gh",
            "issue",
            "edit",
            "9",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            body_file = args[args.index("--body-file") + 1]
            edited = Path(body_file).read_text(encoding="utf-8")
            self.edit_bodies.append(edited)
            if self.edit_failures:
                self.edit_failures -= 1
                return CommandResult(tuple(args), 1, "", "Could not resolve host", 0.01)
            if self.persist_edits:
                self.body = edited
                self.updated_at = "2026-07-19T00:00:01Z"
            return CommandResult(tuple(args), 0, "", "", 0.01)
        if args[:3] == [
            "gh",
            "repo",
            "view",
        ]:  # lint-gh-argv-literal: ok fixture assertion
            return CommandResult(tuple(args), 0, "owner/repo\n", "", 0.01)
        raise AssertionError(f"unexpected call: {args}")


def test_title_eligibility_and_insert_signal_marker() -> None:
    assert (
        issue_wire.title_lifecycle_reject_marker("  [implementing] x")
        == "[IMPLEMENTING]"
    )
    assert issue_wire.title_lifecycle_reject_marker("[STALLED] x") is None
    assert issue_wire.title_lifecycle_reject_marker("[Debating] x") == "[DEBATING]"
    assert issue_wire.title_lifecycle_reject_marker("  [dEbAtEd] x") == "[DEBATED]"
    assert (
        issue_wire.insert_signal_marker(
            title="[DESIGNED] My feature", marker="FALSE-POSITIVE"
        )
        == "[DESIGNED] [FALSE-POSITIVE] My feature"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DESIGNED] [FALSE-POSITIVE] My feature", marker="FALSE-POSITIVE"
        )
        == "[DESIGNED] [FALSE-POSITIVE] My feature"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DEBATING] Open question", marker="NEEDS-INPUT"
        )
        == "[DEBATING] [NEEDS-INPUT] Open question"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[Debated] Mixed case", marker="FALSE-POSITIVE"
        )
        == "[Debated] [FALSE-POSITIVE] Mixed case"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[Debated] [FALSE-POSITIVE] Mixed case",
            marker="FALSE-POSITIVE",
        )
        == "[Debated] [FALSE-POSITIVE] Mixed case"
    )
    assert (
        issue_wire.insert_signal_marker(
            title="[DEBATED] [NEEDS-INPUT] Ordered",
            marker="FALSE-POSITIVE",
        )
        == "[DEBATED] [FALSE-POSITIVE] [NEEDS-INPUT] Ordered"
    )


def test_untrusted_helpers(tmp_path: Path) -> None:
    token = "sk-" + "B" * 24
    redacted = issue_wire.redact_untrusted_stream(f"<{token}&>")
    assert "&lt;" in redacted
    assert "&amp;" in redacted
    assert token not in redacted
    file = tmp_path / "payload.txt"
    _ = file.write_text("<x>", encoding="utf-8")
    assert (
        issue_wire.emit_untrusted_file_block(tag="tag", path=file)
        == '<tag encoding="literal-redacted">\n&lt;x&gt;\n\n</tag>\n\n'
    )


def test_gh_issue_view_body_and_edit_retry(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = IssueRunner("body", edit_failures=2)

    def retry_no_sleep(
        fn: Callable[[], tuple[CommandResult, int, str]],
    ) -> retry.RetryResult[CommandResult]:
        return retry.with_transient_retry(fn, sleeper=lambda _seconds: None)

    _ = monkeypatch.setattr(gh, "with_transient_retry", retry_no_sleep)
    body = gh.issue_view_body(runner, "9", repo="owner/repo")
    assert body == "body"
    result = gh.issue_edit_body_with_retry(runner, "9", "redacted", repo="owner/repo")
    assert result.returncode == 0
    edit_calls = [
        call for call in runner.calls if call[:3] == ["gh", "issue", "edit"]
    ]  # lint-gh-argv-literal: ok fixture assertion
    assert len(edit_calls) == 3
    assert runner.edit_bodies[-1] == "redacted"
