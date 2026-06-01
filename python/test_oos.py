"""Tests for oos.py."""

from __future__ import annotations

from pathlib import Path

import oos
from proc import CommandResult


class _NoopRunner:
    def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
        return CommandResult((), 0, "", "", 0.0)


def test_disposition_skips_repo_unavailable() -> None:
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(),
        repo_unavailable=True,
    )
    assert result.ok
    assert result.skipped


def test_disposition_skips_fork() -> None:
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(),
        forked=True,
    )
    assert result.ok
    assert result.skipped


def test_disposition_passes_with_inline_triage(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.json"
    _ = accepted.write_text(
        '{"title": "x", "phase": "implement", "accepted": true}\n' * 2,
        encoding="utf-8",
    )
    messages = "Inline-triage rule 1: fold docs\nInline-triage rule 2: fold bug\n"
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        commit_range_messages=messages,
    )
    assert result.ok


def test_disposition_counts_markdown_oos_blocks(tmp_path: Path) -> None:
    accepted = tmp_path / "acc.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Description**: bug\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    filed = tmp_path / "filed.md"
    _ = filed.write_text(
        "Created https://github.com/example/larch/issues/99\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        filed_urls_files=(str(filed),),
    )
    assert result.ok
    assert result.non_security_count == 1


def test_disposition_fails_without_coverage(tmp_path: Path) -> None:
    accepted = tmp_path / "bad.md"
    _ = accepted.write_text(
        "### OOS_1: Orphan\n- **Description**: no disposition\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
    )
    assert not result.ok


def test_rejected_markers_ignore_tags_outside_section(tmp_path: Path) -> None:
    ndjson = tmp_path / "oos.ndjson"
    _ = ndjson.write_text(
        '{"body":"Mention OOS_99 in prose\\n## Rejected\\n### OOS_1: x\\n"}\n',
        encoding="utf-8",
    )
    accepted = tmp_path / "acc.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        oos_issues_ndjson=str(ndjson),
    )
    assert result.rejected_markers == 1
