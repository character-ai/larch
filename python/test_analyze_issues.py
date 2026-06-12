# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# pylint: skip-file
"""Smoke tests for analyze issue entrypoints."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest

import analyze_issues
import render_chart


def test_render_chart_smoke() -> None:
    assert "Cumulative growth chart" in render_chart.render_chart(["2026-01"], [("A", "Bug", [1])])


def test_analyze_fixture_runs(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([{"number": 1, "title": "Fix bug", "state": "OPEN", "createdAt": "2026-01-01T00:00:00Z", "body": "", "labels": []}]), encoding="utf-8")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "1"]) == 0
    assert "Bug fix" in capsys.readouterr().out


def test_analyze_rich_fixture_pins_categories_duplicates_and_reviewers(capsys) -> None:
    fixture = Path(__file__).with_name("analyze-issues-fixture.json")
    assert analyze_issues.analyze_main(["--json", str(fixture), "--top-k", "3"]) == 0
    out = capsys.readouterr().out
    assert "Bug fix: 3 (" in out
    assert "Documentation/contract drift: 2 (" in out
    assert "Other: 1 (" in out
    assert "Auto-spawned share: 1/10" in out
    assert "bug fix: crash in foo" in out
    assert "codex" in out
    assert "YES=2 NO=1" in out


def test_fetch_writes_private_output(monkeypatch, tmp_path: Path) -> None:
    def fake_run(argv, stdout, **_kwargs):
        stdout.write("[]\n")
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    output = tmp_path / "issues.json"
    assert analyze_issues.fetch_main(["--repo", "o/r", "--limit", "10", "--output", str(output)]) == 0
    assert output.stat().st_mode & 0o777 == 0o600


def test_load_issues_duplicate_first_wins_and_warns(tmp_path: Path, capsys) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([
        {"number": "7", "title": "first", "body": "a"},
        {"number": 7, "title": "second", "body": "b"},
    ]), encoding="utf-8")
    issues = analyze_issues.load_issues(str(fixture), lenient=True)
    assert [issue["title"] for issue in issues] == ["first"]
    assert "skipping duplicate parsed number 7" in capsys.readouterr().err


def test_load_issues_skip_threshold_aborts_unless_lenient(tmp_path: Path) -> None:
    fixture = tmp_path / "issues.json"
    fixture.write_text(json.dumps([
        {"number": 1, "title": "valid", "body": ""},
        "bad",
    ]), encoding="utf-8")
    with pytest.raises(SystemExit, match="pass --lenient"):
        analyze_issues.load_issues(str(fixture))
    assert len(analyze_issues.load_issues(str(fixture), lenient=True)) == 1


def test_run_main_forwards_lenient_to_analyzer(monkeypatch, tmp_path: Path) -> None:
    seen: dict[str, list[str]] = {}
    monkeypatch.setattr(analyze_issues, "_detect_repo", lambda: "o/r")
    monkeypatch.setenv("TMPDIR", str(tmp_path))
    monkeypatch.setattr(analyze_issues, "fetch_main", lambda _argv: 0)

    def fake_main(argv):
        seen["argv"] = list(argv)
        return 0

    monkeypatch.setattr(analyze_issues, "main", fake_main)
    assert analyze_issues.run_main(["--lenient"]) == 0
    assert "--lenient" in seen["argv"]
