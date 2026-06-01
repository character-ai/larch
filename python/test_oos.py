"""Tests for oos.py."""

from __future__ import annotations

from pathlib import Path

import oos
from proc import CommandResult


class _NoopRunner:
    def run(self, *args: object, **kwargs: object) -> CommandResult:  # pylint: disable=unused-argument
        return CommandResult((), 0, "", "", 0.0)


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
