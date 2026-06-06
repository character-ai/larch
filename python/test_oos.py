"""Tests for oos.py."""

from __future__ import annotations

from pathlib import Path

import pytest  # noqa: TC002

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
    ndjson = tmp_path / "oos.ndjson"
    _ = ndjson.write_text("", encoding="utf-8")
    messages = "Inline-triage rule 1: fold docs\nInline-triage rule 2: fold bug\n"
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        oos_issues_ndjson=str(ndjson),
        commit_range_messages=messages,
    )
    assert result.ok


def test_disposition_passes_with_inline_triage_without_ndjson(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### OOS_1: Folded\n- **Description**: fixed inline\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        commit_range_messages="Inline-triage rule 1: folded into this branch\n",
    )
    assert result.ok
    assert result.inline_triage == 1


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
    ndjson = tmp_path / "oos.ndjson"
    _ = ndjson.write_text("", encoding="utf-8")
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        filed_urls_files=(str(filed),),
        oos_issues_ndjson=str(ndjson),
    )
    assert result.ok
    assert result.non_security_count == 1


def test_disposition_counts_strict_filed_url_fields(tmp_path: Path) -> None:
    accepted = tmp_path / "acc.md"
    _ = accepted.write_text(
        "### OOS_1: Design item\n- **Filed URL**: https://github.com/example/larch/issues/99\n",
        encoding="utf-8",
    )
    ndjson = tmp_path / "oos.ndjson"
    _ = ndjson.write_text("", encoding="utf-8")
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        filed_urls_strict_files=(str(accepted),),
        oos_issues_ndjson=str(ndjson),
    )
    assert result.ok
    assert result.filed_urls == 1


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


def test_rejected_section_stops_at_next_heading(tmp_path: Path) -> None:
    ndjson = tmp_path / "oos.ndjson"
    _ = ndjson.write_text(
        '{"body":"## Rejected\\n### OOS_1: x\\n## Later\\nOOS_99\\n"}\n',
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


def test_filed_urls_ignore_off_host(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GH_HOST", raising=False)
    accepted = tmp_path / "acc.md"
    _ = accepted.write_text(
        "### OOS_1: Widget\n- **Phase**: implement\n",
        encoding="utf-8",
    )
    filed = tmp_path / "filed.md"
    _ = filed.write_text(
        "Created https://evil.example/o/r/issues/99\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
        filed_urls_files=(str(filed),),
    )
    assert result.filed_urls == 0
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


def test_count_non_security_counts_legacy_tagged_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Legacy tagged block\n"
        "- **Description**: dropped before #3550.\n",
        encoding="utf-8",
    )
    assert oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_counts_legacy_trailing_tagged_headers(
    tmp_path: Path,
) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: Legacy tagged block [OUT_OF_SCOPE]\n"
        "- **Description**: tag after title matches awk parity.\n",
        encoding="utf-8",
    )
    assert oos.count_non_security((str(accepted),)) == 1


def test_count_non_security_ignores_bare_finding_headers(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: bare in-scope finding\n- **Concern**: stays in scope.\n",
        encoding="utf-8",
    )
    assert oos.count_non_security((str(accepted),)) == 0


def test_disposition_gap_for_legacy_header_blocks(tmp_path: Path) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Legacy tagged block\n"
        "- **Description**: no disposition coverage.\n",
        encoding="utf-8",
    )
    result = oos.disposition_ok(
        _NoopRunner(),  # type: ignore[arg-type]
        accepted_files=(str(accepted),),
    )
    assert not result.ok
    assert result.non_security_count >= 1


def test_count_non_security_excludes_security_tagged_legacy_header(
    tmp_path: Path,
) -> None:
    accepted = tmp_path / "accepted.md"
    _ = accepted.write_text(
        "### FINDING_1: [OUT_OF_SCOPE] Security item\n"
        "- **focus-area**: security\n",
        encoding="utf-8",
    )
    assert oos.count_non_security((str(accepted),)) == 0
