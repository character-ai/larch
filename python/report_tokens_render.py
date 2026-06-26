"""Render /report-tokens markdown analysis."""

from __future__ import annotations

import json
import statistics
import tempfile
from pathlib import Path
from collections import defaultdict

from larch.core import config
from report_tokens_cost import DisplayRates, aggregate_vendor_tokens, display_rates
from report_tokens_models import ReportSection, RunRecord, SectionPriority, Skill, workflow_groups

DATE_LEN = 10


def _money(value: float) -> str:
    return f"${value:.2f}"


def _date(value: str) -> str | None:
    return value[:DATE_LEN] if len(value) >= DATE_LEN else None


def _md_cell(value: object) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    text = text.replace("[", "\\[").replace("]", "\\]")
    return " ".join(text.splitlines()) or "unknown"


def _summary(records: tuple[RunRecord, ...], *, actual_spend: float | None) -> str:
    total = sum(record.total_cost for record in records)
    lines = [
        "## Report Tokens Analysis",
        "",
        f"Analyzed {len(records)} parseable runs.",
        f"Tracked total estimated cost: {_money(total)}.",
    ]
    fallback_count = sum(1 for record in records if not record.priced_by_token_cost)
    if fallback_count:
        lines.append(f"Pricing fallback used for {fallback_count} runs; blended rates are marked with `fallback` in tables.")
    if actual_spend is not None:
        delta = actual_spend - total
        pct = (delta / total * 100) if total else 0.0
        lines.append(f"Actual-spend reconciliation: tracked={_money(total)} actual={_money(actual_spend)} delta={pct:.1f}%")
    return "\n".join(lines)


def _aggregate(*, skill: Skill, records: tuple[RunRecord, ...]) -> str:
    if skill == "implement":
        costs = [record.total_cost for record in records]
        lines = [
            "## Aggregate cost",
            "",
            "| Label | Runs | Total | Median | Mean | Max |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
        if costs:
            lines.append(f"| All runs | {len(costs)} | {_money(sum(costs))} | {_money(statistics.median(costs))} | {_money(statistics.mean(costs))} | {_money(max(costs))} |")
        return "\n".join(lines)
    costs = [record.total_cost for record in records]
    lines = [
        "## Aggregate cost",
        "",
        "| Runs | Total | Median | Mean | Max |",
        "| ---: | ---: | ---: | ---: | ---: |",
    ]
    if costs:
        lines.append(
            f"| {len(costs)} | {_money(sum(costs))} | "
            f"{_money(statistics.median(costs))} | {_money(statistics.mean(costs))} | {_money(max(costs))} |",
        )
    return "\n".join(lines)

def _vendor_breakdown(records: tuple[RunRecord, ...]) -> str:
    lines = [
        "## Vendor breakdown",
        "",
        "| Vendor | Cost | Tokens |",
        "| --- | ---: | ---: |",
        f"| Claude | {_money(sum(record.claude_cost for record in records))} | {sum(aggregate_vendor_tokens(record=record, vendor='claude') for record in records):,} |",
        f"| Codex | {_money(sum(record.codex_cost for record in records))} | {sum(aggregate_vendor_tokens(record=record, vendor='codex') for record in records):,} |",
        f"| Cursor | {_money(sum(record.cursor_cost for record in records))} | {sum(aggregate_vendor_tokens(record=record, vendor='cursor') for record in records):,} |",
        f"| Claude (subprocess) | {_money(sum(record.claude_sub_cost for record in records))} | {sum(aggregate_vendor_tokens(record=record, vendor='claude_sub') for record in records):,} |",
    ]
    return "\n".join(lines)


def _top_runs(*, skill: Skill, records: tuple[RunRecord, ...]) -> str:
    if skill == "implement":
        lines = [
            "## Top runs by estimated cost",
            "",
            "| Issue | Started | Total | Claude | Codex | Cursor | Claude (sub) |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    else:
        lines = [
            "## Top runs by estimated cost",
            "",
            "| Issue | Started | Total | Claude | Codex | Cursor | Claude (sub) |",
            "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    for record in sorted(records, key=lambda item: item.total_cost, reverse=True)[:10]:
        issue = f"[#{record.number}]({record.url})" if record.url else f"#{record.number}"
        pricing = "python-pricing" if record.priced_by_token_cost else "fallback"
        lines.append(
            f"| {issue} | {_md_cell(_date(record.started_at) or 'unknown')} | "
            f"{_money(record.total_cost)} ({pricing}) | {_money(record.claude_cost)} | {_money(record.codex_cost)} | {_money(record.cursor_cost)} | {_money(record.claude_sub_cost)} |",
        )
    return "\n".join(lines)


def _phase_breakdown(*, skill: Skill, records: tuple[RunRecord, ...]) -> str:
    if skill == "implement":
        by_phase_impl: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"tokens": 0, "runs": 0})
        seen_impl: set[tuple[int, str, str]] = set()
        for record in records:
            for row in record.phase_rows:
                key = (row.vendor, row.step)
                by_phase_impl[key]["tokens"] += row.total
                seen_impl.add((record.number, *key))
        for _number, vendor, step in seen_impl:
            by_phase_impl[(vendor, step)]["runs"] += 1
        lines = [
            "## Phase breakdown",
            "",
            "| Vendor | Phase | Runs | Tokens |",
            "| --- | --- | ---: | ---: |",
        ]
        for (vendor, step), values in sorted(by_phase_impl.items(), key=lambda item: item[1]["tokens"], reverse=True)[:20]:
            lines.append(f"| {_md_cell(vendor)} | {_md_cell(step)} | {values['runs']} | {values['tokens']:,} |")
        return "\n".join(lines)
    by_phase: dict[tuple[str, str], dict[str, int]] = defaultdict(lambda: {"tokens": 0, "runs": 0})
    seen: set[tuple[int, str, str]] = set()
    for record in records:
        for row in record.phase_rows:
            key = (row.vendor, row.step)
            by_phase[key]["tokens"] += row.total
            seen.add((record.number, *key))
    for _number, vendor, step in seen:
        by_phase[(vendor, step)]["runs"] += 1
    lines = [
        "## Phase breakdown",
        "",
        "| Vendor | Phase | Runs | Tokens |",
        "| --- | --- | ---: | ---: |",
    ]
    for (vendor, step), values in sorted(by_phase.items(), key=lambda item: item[1]["tokens"], reverse=True)[:20]:
        lines.append(f"| {_md_cell(vendor)} | {_md_cell(step)} | {values['runs']} | {values['tokens']:,} |")
    return "\n".join(lines)

def _trend_table(*, title: str, records: list[RunRecord], attr: str) -> str:
    by_day: dict[str, float] = defaultdict(float)
    missing = 0
    for record in records:
        day = _date(record.started_at)
        if day is None:
            missing += 1
            continue
        by_day[day] += float(getattr(record, attr))
    lines = [
        f"### {title}",
        "",
        "| Date | Cost |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {day} | {_money(by_day[day])} |" for day in sorted(by_day))
    if missing:
        lines.append(f"\n_{missing} runs lacked a parseable started_at date._")
    return "\n".join(lines)


def _trends(*, skill: Skill, records: tuple[RunRecord, ...]) -> str:
    labels = (
        ("Total cost", "total_cost"),
        ("Claude cost", "claude_cost"),
        ("Codex cost", "codex_cost"),
        ("Cursor cost", "cursor_cost"),
        ("Claude (subprocess) cost", "claude_sub_cost"),
    )
    groups: dict[str, list[RunRecord]] = workflow_groups(_skill=skill, records=records)
    lines = ["## Per-day cost trends", ""]
    for group_name in sorted(groups):
        for label, attr in labels:
            lines.append(_trend_table(title=label, records=groups[group_name], attr=attr))
            lines.append("")
    return "\n".join(lines).rstrip()


def _suggestions(records: tuple[RunRecord, ...]) -> str:
    total_cache_read = sum(record.claude.cache_read + record.cursor.cache_read for record in records)
    if any(not record.priced_by_token_cost for record in records):
        pricing_line = "- Treat dollar values as estimates; rows marked `fallback` used blended display rates because `python/report_tokens_cost.py` used blended fallback pricing."
    else:
        pricing_line = "- Treat dollar values as estimates; `python/report_tokens_cost.py` remains the pricing authority used for headline totals."
    return "\n".join([
        "## Cost-reduction suggestions",
        "",
        "- Review the highest-cost runs above before optimizing lower-cost phases.",
        f"- Cache-read tokens observed: {total_cache_read:,}; preserve prompt stability where cache hits are useful.",
        pricing_line,
    ])


def _rates_text(rates: DisplayRates) -> str:
    return "\n".join([
        "## Rates used for display/fallback",
        "",
        f"Claude: input {rates.claude_input}/M, cache read {rates.claude_cache_read}/M, output {rates.claude_output}/M.",
        f"Codex: input {rates.codex_input}/M, cached input {rates.codex_cached_input}/M, output {rates.codex_output}/M.",
        f"Cursor: input {rates.cursor_input}/M, cache read {rates.cursor_cache_read}/M, output {rates.cursor_output}/M.",
    ])


def _cache_path(temp_root: Path | None) -> Path:
    root = temp_root or Path(tempfile.mkdtemp(prefix="larch-report-tokens."))
    root.mkdir(parents=True, exist_ok=True)
    return root / "report-cache.ndjson"


def _write_cache(*, path: Path, _skill: Skill, records: tuple[RunRecord, ...]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for record in records:
            row = {
                "number": record.number,
                "title": record.title,
                "url": record.url,
                "started_at": record.started_at,
                "closed_at": record.closed_at,
                "claude_cost": record.claude_cost,
                "codex_cost": record.codex_cost,
                "cursor_cost": record.cursor_cost,
                "claude_sub_cost": record.claude_sub_cost,
                "total_cost": record.total_cost,
                "pricing_source": "python-pricing" if record.priced_by_token_cost else "python-blended-fallback",
            }
            _ = handle.write(json.dumps(row, sort_keys=True) + "\n")
    _ = tmp.replace(path)


def render(
    *, skill: Skill,
    records: tuple[RunRecord, ...],
    rates_display: DisplayRates | None = None,
    actual_spend: float | None = None,
    include_actual_spend_in_issue: bool = False,
    temp_root: Path | None = None,
) -> tuple[str, list[ReportSection], Path]:
    rates = rates_display or display_rates()
    cache_path = _cache_path(temp_root)
    _write_cache(path=cache_path, _skill=skill, records=records)
    summary = _summary(records, actual_spend=actual_spend)
    issue_summary = _summary(records, actual_spend=actual_spend if include_actual_spend_in_issue else None)
    sections = [
        ReportSection("summary", issue_summary, SectionPriority.SUMMARY),
        ReportSection("aggregate", _aggregate(skill=skill, records=records), SectionPriority.AGGREGATE),
        ReportSection("vendor", _vendor_breakdown(records), SectionPriority.BREAKDOWN),
        ReportSection("top", _top_runs(skill=skill, records=records), SectionPriority.BREAKDOWN),
        ReportSection("phase", _phase_breakdown(skill=skill, records=records), SectionPriority.BREAKDOWN),
        ReportSection("trends", _trends(skill=skill, records=records), SectionPriority.TRENDS),
        ReportSection("suggestions", _suggestions(records), SectionPriority.SUGGESTIONS),
        ReportSection("rates", _rates_text(rates), SectionPriority.CACHE),
    ]
    body = "\n\n".join([section.body for section in sections])
    if actual_spend is not None and not include_actual_spend_in_issue:
        body = "\n\n".join([summary, *[section.body for section in sections[1:]]])
    body = f"{body}\n\nCache JSON: {cache_path}"
    return body, sections, cache_path


def title_for_skill(skill: Skill, *, timestamp: str) -> str:
    template = config.REPORT_TOKENS_TITLE_BY_SKILL[skill]
    return template.format(timestamp=timestamp)
