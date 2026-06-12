# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: E702, F401
# pylint: skip-file
"""Representative tests for audit run helpers."""

from __future__ import annotations

import json
from pathlib import Path

import audit_runs
from proc import CommandResult


def test_title_contiguous(capsys):
    assert audit_runs.title_main(["--skill", "implement", "--pr-list", "3,1,2", "--timestamp", "T"]) == 0
    assert capsys.readouterr().out.strip() == "TITLE=[Implement Run Logs Audit T Report] PRs #1-#3"


def test_scan_run_rejects_skill_root(tmp_path: Path, capsys):
    root = Path("larch-logs/implement")
    root.mkdir(parents=True, exist_ok=True)
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\ncache-freshness\tfile\n", encoding="utf-8")
    try:
        assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(root),"--pr","1","--scans-tsv",str(scans)]) == 1
        row = json.loads(capsys.readouterr().out)
        assert row["scan"] == "run-dir-invalid"
    finally:
        # Leave committed log dirs untouched; remove only if empty from this test.
        try:
            root.rmdir(); root.parent.rmdir()
        except OSError:
            pass


def test_oos_silent_drop_no_git_fallback(tmp_path: Path, capsys):
    run = tmp_path / "run"
    run.mkdir()
    (run / "oos-accepted-main-agent.md").write_text("### OOS_1: thing\n- **Focus area**: correctness\n", encoding="utf-8")
    scans = tmp_path / "scans.tsv"
    scans.write_text("name\ttype\noos-silent-drop\tfile\n", encoding="utf-8")
    assert audit_runs.scan_run_main(["--skill","implement","--run-dir",str(run),"--pr","7","--scans-tsv",str(scans)]) == 0
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    row = next(r for r in rows if r["scan"] == "oos-silent-drop")
    assert row["result"] == "fail"
    assert row["inline_triage_hits"] == 0


def test_compute_counters_legacy_alias(tmp_path: Path, capsys):
    d = tmp_path / "scans"; d.mkdir()
    (d / "scan-results-1.ndjson").write_text('{"scan":"ns-retry-sidecars","result":"skip"}\n', encoding="utf-8")
    prior = tmp_path / "prior.md"
    prior.write_text("---\nns_retries_cursor_specialist_launches: 4\n---\n", encoding="utf-8")
    assert audit_runs.compute_counters_main(["--scan-results-dir", str(d), "--prior-frontmatter", str(prior)]) == 0
    out = dict(line.split("=",1) for line in capsys.readouterr().out.splitlines())
    assert out["NS_RETRIES_CURSOR_SPECIALIST"] == "4"
    assert out["NS_RETRIES_SKIPPED_RUNS"] == "1"
