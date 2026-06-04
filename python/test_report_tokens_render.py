from __future__ import annotations

from pathlib import Path

from report_tokens_models import PhaseRow, RunRecord, VendorTotals
from report_tokens_render import render


def _record(workflow: str = "unknown") -> RunRecord:
    return RunRecord(
        number=7,
        title="Issue #7",
        url="https://example.invalid/7",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-02T00:00:00Z",
        workflow=workflow,
        claude=VendorTotals(total=10),
        codex=VendorTotals(total=20),
        cursor=VendorTotals(total=30),
        phase_rows=(),
        raw_report={},
        claude_cost=1,
        codex_cost=2,
        cursor_cost=3,
        total_cost=6,
    )


def test_render_implement_aggregate_and_absent_removed_sections(tmp_path: Path) -> None:
    body, sections, cache = render("implement", (_record(),), temp_root=tmp_path)
    assert "## Report Tokens Analysis" in body
    assert "### Total cost" in body
    assert "Reported vs estimated" not in body
    assert "Raw per-issue data" not in body
    assert cache.is_file()
    assert sections


def test_actual_spend_omitted_from_issue_by_default(tmp_path: Path) -> None:
    body, sections, _cache = render("design", (_record("SIMPLE"),), actual_spend=10, temp_root=tmp_path)
    assert "Actual-spend reconciliation" in body
    assert all("Actual-spend reconciliation" not in section.body for section in sections)


def test_render_design_split_and_phase_breakdown(tmp_path: Path) -> None:
    hard = _record("HARD")
    hard = RunRecord(
        hard.number,
        hard.title,
        hard.url,
        hard.started_at,
        hard.closed_at,
        hard.workflow,
        hard.claude,
        hard.codex,
        hard.cursor,
        (PhaseRow("claude", "Step 5", total=123),),
        hard.raw_report,
        hard.claude_cost,
        hard.codex_cost,
        hard.cursor_cost,
        hard.total_cost,
    )
    body, _sections, _cache = render("design", (_record("SIMPLE"), hard), temp_root=tmp_path)
    assert "### SIMPLE" in body
    assert "### HARD" in body
    assert "## Phase breakdown" in body
    assert "| HARD | claude | Step 5 | 1 | 123 |" in body


def test_render_implement_trends_have_no_workflow_subheads(tmp_path: Path) -> None:
    body, _sections, _cache = render("implement", (_record("SIMPLE"), _record("HARD")), temp_root=tmp_path)
    trends = body.split("## Per-day cost trends", 1)[1]
    assert "### SIMPLE" not in trends
    assert "### HARD" not in trends
