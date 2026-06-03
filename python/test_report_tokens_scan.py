from __future__ import annotations

# pylint: disable=unused-argument

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pytest

from proc import CommandResult
from report_tokens_scan import scan


def _calls() -> list[list[str]]:
    return []


@dataclass
class Runner:
    root: Path
    calls: list[list[str]] = field(default_factory=_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        self.calls.append(list(argv))
        if list(argv)[:2] == ["git", "rev-parse"]:
            return CommandResult(tuple(argv), 0, str(self.root), "", 0.01)
        return CommandResult(tuple(argv), 1, "", "gh transient failure", 0.01)


def _write_run(base: Path, *, skill: str, good_tokens: bool = True) -> None:
    run = base / "larch-logs" / skill / "run1"
    run.mkdir(parents=True)
    _ = (run / "manifest.json").write_text(json.dumps({"issue_number": 1, "started_at": "2026-01-01T00:00:00Z", "updated_at": "2026-01-02T00:00:00Z"}), encoding="utf-8")
    token_name = "token-report-final.json" if skill == "design" else "token-report.json"
    report: dict[str, object] = {"claude": {"totals": {"total": 10}}, "BUCKETS_claude": {"input": 10}}
    if not good_tokens:
        report: dict[str, object] = {"claude": {"totals": {}}}
    _ = (run / token_name).write_text(json.dumps(report), encoding="utf-8")
    _ = (run / "run-params.json").write_text(json.dumps({"design_classification": "SIMPLE"}), encoding="utf-8")


def test_scan_per_skill_basename_and_workflow(tmp_path: Path) -> None:
    _write_run(tmp_path, skill="design")
    result = scan(Runner(tmp_path), skill="design", repo_override="o/r")
    assert len(result.records) == 1
    assert result.records[0].workflow == "SIMPLE"
    assert result.records[0].url == "https://github.com/o/r/issues/1"


def test_scan_warns_missing_slug_and_skips_incomplete(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write_run(tmp_path, skill="implement", good_tokens=False)
    result = scan(Runner(tmp_path), skill="implement")
    assert result.repo_slug is None
    assert not result.records
    captured = capsys.readouterr()
    assert "could not resolve GitHub repo" in captured.err
    assert "lacks vendor totals" in captured.err
