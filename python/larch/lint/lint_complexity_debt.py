"""Render the operator-facing complexity-baseline debt report."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
import json
from pathlib import Path
import sys
from typing import cast

from larch.lint.engine import (
    ComplexityBaselineRow,
    ScanError,
    complexity_history_events,
    load_complexity_baseline,
    parse_complexity_baseline,
    parse_complexity_debt_argv,
)

UNDER_14_DAYS = 14
THROUGH_90_DAYS = 90
RECENT_BUMP_DAYS = 30
MINIMUM_REPEAT_EVENTS = 2


def _typed_records(
    records: Sequence[ComplexityBaselineRow | Mapping[str, object]], *, today: date
) -> list[ComplexityBaselineRow]:
    """Accept legacy mapping fixtures while runtime callers use typed rows."""
    if all(isinstance(record, ComplexityBaselineRow) for record in records):
        return list(cast("Sequence[ComplexityBaselineRow]", records))
    return parse_complexity_baseline(
        json.dumps(list(records)), source="complexity debt records", today=today
    )


def _age_bucket_counts(
    records: Sequence[ComplexityBaselineRow], today: date
) -> tuple[int, int, int, int]:
    under_14 = through_90 = over_90 = legacy = 0
    for record in records:
        if record.added_at == "legacy":
            legacy += 1
            continue
        age = (today - date.fromisoformat(record.added_at)).days
        if age < UNDER_14_DAYS:
            under_14 += 1
        elif age <= THROUGH_90_DAYS:
            through_90 += 1
        else:
            over_90 += 1
    return under_14, through_90, over_90, legacy


def _recent_repeat_lines(
    records: Sequence[ComplexityBaselineRow], today: date
) -> list[str]:
    """Render the established detail-rich repeat-bump diagnostics."""
    cutoff = today - timedelta(days=RECENT_BUMP_DAYS)
    lines: list[str] = []
    for (file_name, symbol), events in sorted(complexity_history_events(records).items()):
        recent = [event for event in events if event.event_date >= cutoff]
        if len(recent) < MINIMUM_REPEAT_EVENTS:
            continue
        details = "; ".join(
            f"{event.event_date.isoformat()} [{event.record.code}] metric {event.metric}"
            for event in recent
        )
        lines.append(f"  {file_name}:{symbol}: {details}")
    return lines


def _active_overrides(records: Sequence[ComplexityBaselineRow]) -> list[str]:
    return [
        f"{record.file}:{record.qualified_symbol} [{record.code}] "
        f"issue #{record.operator_override.issue}: {record.operator_override.reason}"
        for record in sorted(records, key=lambda row: row.identity)
        if record.operator_override is not None
    ]


def render_report(
    records: Sequence[ComplexityBaselineRow | Mapping[str, object]], *, today: date
) -> str:
    """Render every debt section deterministically, including empty sections."""
    typed_records = _typed_records(records, today=today)
    under_14, through_90, over_90, legacy = _age_bucket_counts(typed_records, today)
    lines = ["Complexity debt report", f"Total entries: {len(typed_records)}", "", "Age buckets:"]
    lines.extend([
        f"  under 14 days: {under_14}",
        f"  14 through 90 days: {through_90}",
        f"  over 90 days: {over_90}",
        f"  legacy: {legacy}",
        "",
        "Top 10 by metric:",
    ])
    top = sorted(typed_records, key=lambda row: (-row.metric, *row.identity))[:10]
    if top:
        lines.extend(f"  {row.metric} | {row.file} | {row.code} | {row.qualified_symbol}" for row in top)
    else:
        lines.append("  (none)")
    lines.extend(["", "Symbols with at least two bumps in the last 30 days:"])
    lines.extend(_recent_repeat_lines(typed_records, today) or ["  (none)"])
    lines.extend(["", "Active operator overrides:"])
    overrides = _active_overrides(typed_records)
    if overrides:
        lines.extend(f"  {line}" for line in overrides)
    else:
        lines.append("  (none)")
    return "\n".join(lines) + "\n"


def _utc_today() -> date:
    return datetime.now(UTC).date()


def main(argv: list[str] | None = None) -> int:
    """Load the typed engine baseline and render its debt report."""
    parsed = parse_complexity_debt_argv(
        argv if argv is not None else sys.argv[1:], default_root=Path(__file__).resolve().parents[3]
    )
    if parsed is None:
        print("lint-complexity-debt: --report is required", file=sys.stderr)
        return 2
    baseline_path = parsed.root / "python" / "complexity-baseline.json"
    try:
        records = load_complexity_baseline(baseline_path, root=parsed.root, today=_utc_today())
    except ScanError as exc:
        print(f"lint-complexity-debt: {exc}", file=sys.stderr)
        return 2
    print(render_report(records, today=_utc_today()), end="")
    return 0
