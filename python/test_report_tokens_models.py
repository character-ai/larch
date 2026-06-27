from __future__ import annotations

from dataclasses import fields

from larch.report.report_tokens_models import DisplayRates, ReportSection, RunRecord, SectionPriority, VendorTotals, safe_int


def test_display_rates_carries_codex_mini_fields() -> None:
    names = {f.name for f in fields(DisplayRates)}
    assert {"codex_mini_input", "codex_mini_cached_input", "codex_mini_output"} <= names


def test_dataclasses_and_helpers() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-02T00:00:00Z",
        workflow="",
        claude=VendorTotals(total=1),
        codex=VendorTotals(total=2),
        cursor=VendorTotals(total=3),
        phase_rows=(),
        raw_report={},
    )
    assert record.number == 1
    assert record.main_model == ""
    assert safe_int(value="42") == 42
    assert safe_int(value="1,234") == 1234
    assert safe_int(value="42.9") == 42
    value: object = True
    assert safe_int(value=value, default=9) == 9


def test_section_priority_banner_is_immutable_floor() -> None:
    section = ReportSection("banner", "body", SectionPriority.BANNER)
    assert int(section.priority) == 0
    assert SectionPriority.BANNER < SectionPriority.TRENDS
