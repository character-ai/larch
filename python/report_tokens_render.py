"""Render /report-tokens markdown analysis."""

from __future__ import annotations

import json
import statistics
import tempfile
from pathlib import Path
from collections import defaultdict

import config
from report_tokens_models import DisplayRates, ReportSection, RunRecord, SectionPriority, Skill, display_rates

DATE_LEN = 10


def _money(value: float) -> str:
    return f"${value:.2f}"


def _date(value: str) -> str | None:
    return value[:DATE_LEN] if len(value) >= DATE_LEN else None


def _md_cell(value: object) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\\", "\\\\").replace("|", "\\|")
    return " ".join(text.splitlines()) or "unknown"


def _workflow_groups(skill: Skill, records: tuple[RunRecord, ...]) -> dict[str, list[RunRecord]]:
    groups: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        workflow = record.workflow if record.workflow in ("SIMPLE", "HARD") else "unknown"
        if skill == "design" and workflow == "unknown":
            continue
        key = "All runs" if skill == "implement" else workflow
        groups[key].append(record)
    return dict(groups)


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


def _aggregate(records: tuple[RunRecord, ...]) -> str:
    by_workflow: dict[str, list[RunRecord]] = defaultdict(list)
    for record in records:
        by_workflow[record.workflow if record.workflow in ("SIMPLE", "HARD") else "unknown"].append(record)
    lines = [
        "## Aggregate cost by workflow",
        "",
        "| Workflow | Runs | Total | Median | Mean | Max |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for workflow in sorted(by_workflow):
        costs = [record.total_cost for record in by_workflow[workflow]]
        lines.append(
            f"| {_md_cell(workflow)} | {len(costs)} | {_money(sum(costs))} | "
            f"{_money(statistics.median(costs))} | {_money(statistics.mean(costs))} | {_money(max(costs))} |",
        )
    return "\n".join(lines)


def _vendor_breakdown(records: tuple[RunRecord, ...]) -> str:
    lines = [
        "## Vendor breakdown",
        "",
        "| Vendor | Cost | Tokens |",
        "| --- | ---: | ---: |",
        f"| Claude | {_money(sum(record.claude_cost for record in records))} | {sum(record.claude.total for record in records):,} |",
        f"| Codex | {_money(sum(record.codex_cost for record in records))} | {sum(record.codex.total for record in records):,} |",
        f"| Cursor | {_money(sum(record.cursor_cost for record in records))} | {sum(record.cursor.total for record in records):,} |",
    ]
    return "\n".join(lines)


def _top_runs(records: tuple[RunRecord, ...]) -> str:
    lines = [
        "## Top runs by estimated cost",
        "",
        "| Issue | Workflow | Started | Total | Claude | Codex | Cursor |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: |",
    ]
    for record in sorted(records, key=lambda item: item.total_cost, reverse=True)[:10]:
        issue = f"[#{record.number}]({record.url})" if record.url else f"#{record.number}"
        pricing = "token-cost" if record.priced_by_token_cost else "fallback"
        lines.append(
            f"| {issue} | {_md_cell(record.workflow)} | {_md_cell(_date(record.started_at) or 'unknown')} | "
            f"{_money(record.total_cost)} ({pricing}) | {_money(record.claude_cost)} | {_money(record.codex_cost)} | {_money(record.cursor_cost)} |",
        )
    return "\n".join(lines)


def _phase_breakdown(records: tuple[RunRecord, ...]) -> str:
    by_phase: dict[tuple[str, str, str], dict[str, int]] = defaultdict(lambda: {"tokens": 0, "runs": 0})
    seen: set[tuple[int, str, str, str]] = set()
    for record in records:
        workflow = record.workflow if record.workflow in ("SIMPLE", "HARD") else "unknown"
        for row in record.phase_rows:
            key = (workflow, row.vendor, row.step)
            by_phase[key]["tokens"] += row.total
            seen.add((record.number, *key))
    for _number, workflow, vendor, step in seen:
        by_phase[(workflow, vendor, step)]["runs"] += 1
    lines = [
        "## Phase breakdown",
        "",
        "| Workflow | Vendor | Phase | Runs | Tokens |",
        "| --- | --- | --- | ---: | ---: |",
    ]
    for (workflow, vendor, step), values in sorted(by_phase.items(), key=lambda item: item[1]["tokens"], reverse=True)[:20]:
        lines.append(f"| {_md_cell(workflow)} | {_md_cell(vendor)} | {_md_cell(step)} | {values['runs']} | {values['tokens']:,} |")
    return "\n".join(lines)


def _trend_table(title: str, records: list[RunRecord], attr: str) -> str:
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


def _trends(skill: Skill, records: tuple[RunRecord, ...]) -> str:
    labels = (
        ("Total cost", "total_cost"),
        ("Claude cost", "claude_cost"),
        ("Codex cost", "codex_cost"),
        ("Cursor cost", "cursor_cost"),
    )
    groups = _workflow_groups(skill, records)
    lines = ["## Per-day cost trends", ""]
    for group_name in sorted(groups):
        if skill == "design":
            lines.extend([f"### {group_name}", ""])
        for label, attr in labels:
            table_title = label if skill == "implement" else f"{group_name} {label}"
            lines.append(_trend_table(table_title, groups[group_name], attr))
            lines.append("")
    return "\n".join(lines).rstrip()


def _suggestions(records: tuple[RunRecord, ...]) -> str:
    total_cache_read = sum(record.claude.cache_read + record.cursor.cache_read for record in records)
    return "\n".join([
        "## Cost-reduction suggestions",
        "",
        "- Review the highest-cost runs above before optimizing lower-cost phases.",
        f"- Cache-read tokens observed: {total_cache_read:,}; preserve prompt stability where cache hits are useful.",
        "- Treat dollar values as estimates; `scripts/token-cost.sh` remains the pricing authority used for headline totals.",
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


def _write_cache(path: Path, records: tuple[RunRecord, ...]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        for record in records:
            row = {
                "number": record.number,
                "title": record.title,
                "url": record.url,
                "workflow": record.workflow,
                "started_at": record.started_at,
                "closed_at": record.closed_at,
                "claude_cost": record.claude_cost,
                "codex_cost": record.codex_cost,
                "cursor_cost": record.cursor_cost,
                "total_cost": record.total_cost,
            }
            _ = handle.write(json.dumps(row, sort_keys=True) + "\n")
    _ = tmp.replace(path)


def render(
    skill: Skill,
    records: tuple[RunRecord, ...],
    *,
    rates_display: DisplayRates | None = None,
    actual_spend: float | None = None,
    include_actual_spend_in_issue: bool = False,
    temp_root: Path | None = None,
) -> tuple[str, list[ReportSection], Path]:
    rates = rates_display or display_rates()
    cache_path = _cache_path(temp_root)
    _write_cache(cache_path, records)
    summary = _summary(records, actual_spend=actual_spend)
    issue_summary = _summary(records, actual_spend=actual_spend if include_actual_spend_in_issue else None)
    sections = [
        ReportSection("summary", issue_summary, SectionPriority.SUMMARY),
        ReportSection("aggregate", _aggregate(records), SectionPriority.AGGREGATE),
        ReportSection("vendor", _vendor_breakdown(records), SectionPriority.BREAKDOWN),
        ReportSection("top", _top_runs(records), SectionPriority.BREAKDOWN),
        ReportSection("phase", _phase_breakdown(records), SectionPriority.BREAKDOWN),
        ReportSection("trends", _trends(skill, records), SectionPriority.TRENDS),
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
