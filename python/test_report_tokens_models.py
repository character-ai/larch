from __future__ import annotations

from report_tokens_models import ReportSection, RunRecord, SectionPriority, VendorTotals, env_rate, safe_int


def test_dataclasses_and_helpers() -> None:
    record = RunRecord(
        number=1,
        title="t",
        url="u",
        started_at="2026-01-01T00:00:00Z",
        closed_at="2026-01-02T00:00:00Z",
        workflow="SIMPLE",
        claude=VendorTotals(total=1),
        codex=VendorTotals(total=2),
        cursor=VendorTotals(total=3),
        phase_rows=(),
        raw_report={},
    )
    assert record.number == 1
    assert safe_int("42") == 42
    assert safe_int("1,234") == 1234
    assert safe_int("42.9") == 42
    value: object = True
    assert safe_int(value, 9) == 9


def test_env_rate_alias_precedence() -> None:
    env = {"OLD": "1.5", "NEW": "2.5"}
    assert env_rate(("NEW", "OLD"), 0.1, environ=env) == 2.5
    assert env_rate(("BAD", "OLD"), 0.1, environ={"BAD": "no", "OLD": "3"}) == 3.0


def test_section_priority_banner_is_immutable_floor() -> None:
    section = ReportSection("banner", "body", SectionPriority.BANNER)
    assert int(section.priority) == 0
    assert SectionPriority.BANNER < SectionPriority.TRENDS
