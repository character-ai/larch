from __future__ import annotations

from pathlib import Path

from larch.report.report_tokens_models import PhaseRow, RunRecord, VendorTotals
from larch.report.report_tokens_render import render, title_for_skill


def _without_rates_section(body: str) -> str:
    before, marker, after = body.partition("\n\n## Rates used for display/fallback\n\n")
    if not marker:
        return body
    _rates, cache_marker, cache = after.partition("\n\nCache JSON:")
    return before + cache_marker + cache


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
        claude_sub=VendorTotals(total=40),
        claude_sub_cost=4,
    )


def test_render_implement_aggregate_and_absent_removed_sections(tmp_path: Path) -> None:
    body, sections, cache = render(skill="implement", records=(_record(),), temp_root=tmp_path)
    assert "## Report Tokens Analysis" in body
    assert "### Total cost" in body
    assert "Reported vs estimated" not in body
    assert "Raw per-issue data" not in body
    assert cache.is_file()
    assert '"pricing_source": "python-blended-fallback"' in cache.read_text(encoding="utf-8")
    assert sections


def test_render_implement_golden_markdown(tmp_path: Path) -> None:
    record = _record()
    record = RunRecord(
        record.number,
        record.title,
        record.url,
        record.started_at,
        record.closed_at,
        record.workflow,
        record.claude,
        record.codex,
        record.cursor,
        record.phase_rows,
        record.raw_report,
        record.claude_cost,
        record.codex_cost,
        record.cursor_cost,
        record.total_cost,
        priced_by_token_cost=True,
        claude_sub=record.claude_sub,
        claude_sub_cost=record.claude_sub_cost,
    )
    body, _sections, cache = render(skill="implement", records=(record,), temp_root=tmp_path)
    normalized = _without_rates_section(body).replace(f"Cache JSON: {cache}", "Cache JSON: <CACHE>")
    expected = Path("fixtures/report_tokens_implement_golden.md").read_text(encoding="utf-8").rstrip("\n")
    assert normalized == expected


def test_render_design_golden_markdown(tmp_path: Path) -> None:
    simple = _record()
    hard = _record()
    simple = RunRecord(
        7,
        "Issue 1",
        "https://example.invalid/1",
        simple.started_at,
        simple.closed_at,
        simple.workflow,
        simple.claude,
        simple.codex,
        simple.cursor,
        simple.phase_rows,
        simple.raw_report,
        simple.claude_cost,
        simple.codex_cost,
        simple.cursor_cost,
        simple.total_cost,
        priced_by_token_cost=True,
        claude_sub=simple.claude_sub,
        claude_sub_cost=simple.claude_sub_cost,
    )
    hard = RunRecord(
        8,
        "Issue 2",
        "https://example.invalid/2",
        hard.started_at,
        hard.closed_at,
        hard.workflow,
        hard.claude,
        hard.codex,
        hard.cursor,
        hard.phase_rows,
        hard.raw_report,
        hard.claude_cost,
        hard.codex_cost,
        hard.cursor_cost,
        7,
        priced_by_token_cost=True,
        claude_sub=hard.claude_sub,
        claude_sub_cost=hard.claude_sub_cost,
    )
    body, _sections, cache = render(skill="design", records=(simple, hard), temp_root=tmp_path)
    normalized = _without_rates_section(body).replace(f"Cache JSON: {cache}", "Cache JSON: <CACHE>")
    expected = Path("fixtures/report_tokens_design_golden.md").read_text(encoding="utf-8").rstrip("\n")
    assert normalized == expected


def test_actual_spend_omitted_from_issue_by_default(tmp_path: Path) -> None:
    body, sections, _cache = render(skill="design", records=(_record(),), actual_spend=10, temp_root=tmp_path)
    assert "Actual-spend reconciliation" in body
    assert all("Actual-spend reconciliation" not in section.body for section in sections)


def test_actual_spend_can_be_included_in_issue_sections(tmp_path: Path) -> None:
    _body, sections, _cache = render(skill="design", records=(_record(),), actual_spend=10, include_actual_spend_in_issue=True, temp_root=tmp_path)
    assert "Actual-spend reconciliation" in sections[0].body


def test_render_design_split_and_phase_breakdown(tmp_path: Path) -> None:
    hard = _record()
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
    body, _sections, _cache = render(skill="design", records=(_record(), hard), temp_root=tmp_path)
    assert "## Phase breakdown" in body
    assert "## Phase breakdown" in body
    assert "| claude | Step 5 | 1 | 123 |" in body


def test_markdown_table_cells_escape_log_derived_metacharacters(tmp_path: Path) -> None:
    record = _record()
    record = RunRecord(
        record.number,
        record.title,
        record.url,
        record.started_at,
        record.closed_at,
        record.workflow,
        record.claude,
        record.codex,
        record.cursor,
        (PhaseRow("claude", "Phase | one\nspoof", total=123),),
        record.raw_report,
        record.claude_cost,
        record.codex_cost,
        record.cursor_cost,
        record.total_cost,
    )
    body, _sections, _cache = render(skill="implement", records=(record,), temp_root=tmp_path)
    assert "Phase \\| one spoof" in body
    assert "Phase \\| one spoof" in body
    _ = render(skill="design", records=(record,), temp_root=tmp_path)


def test_fallback_pricing_is_marked(tmp_path: Path) -> None:
    body, sections, _cache = render(skill="implement", records=(_record(),), temp_root=tmp_path)
    assert "Pricing fallback used for 1 runs" in body
    assert "fallback" in sections[0].body


def test_render_implement_trends_have_no_workflow_subheads(tmp_path: Path) -> None:
    body, _sections, _cache = render(skill="implement", records=(_record(), _record()), temp_root=tmp_path)
    _trends = body.split("## Per-day cost trends", 1)[1]


def test_trends_note_missing_started_at(tmp_path: Path) -> None:
    record = RunRecord(
        number=7,
        title="Issue #7",
        url="https://example.invalid/7",
        started_at="",
        closed_at="2026-01-02T00:00:00Z",
        workflow="",
        claude=VendorTotals(total=10),
        codex=VendorTotals(),
        cursor=VendorTotals(),
        phase_rows=(),
        raw_report={},
        total_cost=1,
    )
    body, _sections, _cache = render(skill="implement", records=(record,), temp_root=tmp_path)
    assert "runs lacked a parseable started_at date" in body


def test_render_implement_cache_omits_workflow(tmp_path: Path) -> None:
    _body, _sections, cache = render(skill="implement", records=(_record(),), temp_root=tmp_path)
    rows = cache.read_text(encoding="utf-8").splitlines()
    assert rows
    assert all('"workflow"' not in row for row in rows)


def test_render_design_cache_retains_workflow(tmp_path: Path) -> None:
    _body, _sections, cache = render(skill="design", records=(_record(), _record()), temp_root=tmp_path)
    _ = cache.read_text(encoding="utf-8")


def test_title_for_skill_prefixes() -> None:
    assert title_for_skill("design", timestamp="2026-01-01 00:00 UTC").startswith("[Design Analysis Report]")
    assert title_for_skill("implement", timestamp="2026-01-01 00:00 UTC").startswith("[Implement Analysis Report]")
