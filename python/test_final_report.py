"""Tests for final_report.py extraction surface."""

# pyright: reportUnusedCallResult=false, reportPrivateUsage=false, reportUnknownMemberType=false, reportUnknownLambdaType=false


from __future__ import annotations

import json
from pathlib import Path

import final_report


def _write_minimal_state(tmp_path: Path) -> None:
    (tmp_path / "parent-issue.md").write_text("ISSUE_NUMBER=0\nRUN_ID=run1\n", encoding="utf-8")
    (tmp_path / "session-env.sh").write_text("REPO=o/r\nMODE=N/A\n", encoding="utf-8")
    (tmp_path / "ship-pr-state.sh").write_text("PR_NUMBER=1\nPR_URL=https://github.com/o/r/pull/1\n", encoding="utf-8")
    (tmp_path / "finalize-state.sh").write_text("", encoding="utf-8")
    (tmp_path / "run-flags.sh").write_text("EMERGENCY_REQUESTED=false\n", encoding="utf-8")


def test_write_final_report_module_renders_summary(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    _write_minimal_state(tmp_path)

    def fake_token_fields(implement_tmpdir: Path, run_id: str) -> dict[str, object]:
        _ = (implement_tmpdir, run_id)
        return {"cost_unavailable": True}

    monkeypatch.setattr(final_report, "_final_report_token_fields", fake_token_fields)
    rc, url, err = final_report.write_final_report(tmp_path, comment_only=True)
    assert (rc, url, err) == (0, "", "")
    assert "## /implement run run1" in (tmp_path / "summary-final.md").read_text(encoding="utf-8")


def test_step18b_reports_write_failure(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(final_report, "write_final_report", lambda _tmpdir: (7, "", "boom"))
    emit, rc, _present, _snapshot = final_report.step18b_final_report(tmp_path)
    assert emit is False
    assert rc == 7


def test_refresh_issue_counts_counts_ndjson_urls_separately(tmp_path: Path) -> None:
    run_dir = tmp_path / "larch-logs" / "implement" / "run1"
    run_dir.mkdir(parents=True)
    (run_dir / "execution-issues.ndjson").write_text(
        json.dumps({"category": "Warnings", "body": "- warn\n"}) + "\n",
        encoding="utf-8",
    )
    assert final_report._refresh_issue_counts(tmp_path, "run1") == (0, 1)
