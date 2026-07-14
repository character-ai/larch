"""Render the operator-facing complexity-baseline debt report."""

from __future__ import annotations

import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from larch.lint.lint_complexity_baseline import (
    BaselineError,
    Record,
    active_overrides,
    find_duplicate_keys,
    history_events,
    load_baseline,
    utc_today,
)

UNDER_14_DAYS = 14
THROUGH_90_DAYS = 90
RECENT_BUMP_DAYS = 30
MINIMUM_REPEAT_EVENTS = 2


def _parse_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(
        prog="cli.py lint complexity-debt", description=__doc__
    )
    _ = parser.add_argument("--report", action="store_true", help="Render the debt report.")
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[3]))
    try:
        parsed = parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None
    return parsed if parsed.report else None


def _age_bucket_counts(records: list[Record], today: date) -> tuple[int, int, int, int]:
    under_14 = 0
    through_90 = 0
    over_90 = 0
    legacy = 0
    for record in records:
        added_at = record["added_at"]
        if added_at == "legacy":
            legacy += 1
            continue
        age = (today - date.fromisoformat(added_at)).days
        if age < UNDER_14_DAYS:
            under_14 += 1
        elif age <= THROUGH_90_DAYS:
            through_90 += 1
        else:
            over_90 += 1
    return under_14, through_90, over_90, legacy


def _recent_repeat_lines(records: list[Record], today: date) -> list[str]:
    lines: list[str] = []
    cutoff = today - timedelta(days=RECENT_BUMP_DAYS)
    for (file_name, symbol), events in sorted(history_events(records).items()):
        recent = [event for event in events if event.event_date >= cutoff]
        if len(recent) < MINIMUM_REPEAT_EVENTS:
            continue
        details = "; ".join(
            f"{event.event_date.isoformat()} [{event.record['code']}] metric {event.metric}"
            for event in recent
        )
        lines.append(f"  {file_name}:{symbol}: {details}")
    return lines


def render_report(records: list[Record], *, today: date) -> str:
    """Render every debt section deterministically, including empty sections."""
    under_14, through_90, over_90, legacy = _age_bucket_counts(records, today)
    lines = ["Complexity debt report", f"Total entries: {len(records)}", "", "Age buckets:"]
    lines.extend(
        [
            f"  under 14 days: {under_14}",
            f"  14 through 90 days: {through_90}",
            f"  over 90 days: {over_90}",
            f"  legacy: {legacy}",
            "",
            "Top 10 by metric:",
        ]
    )
    top = sorted(
        records,
        key=lambda record: (-record["metric"], record["file"], record["code"], record["qualified_symbol"]),
    )[:10]
    if top:
        lines.extend(
            f"  {record['metric']} | {record['file']} | {record['code']} | {record['qualified_symbol']}"
            for record in top
        )
    else:
        lines.append("  (none)")
    lines.extend(["", "Symbols with at least two bumps in the last 30 days:"])
    recent = _recent_repeat_lines(records, today)
    lines.extend(recent or ["  (none)"])
    lines.extend(["", "Active operator overrides:"])
    overrides = active_overrides(records)
    lines.extend((f"  {line}" for line in overrides) if overrides else ["  (none)"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parsed = _parse_args(argv if argv is not None else sys.argv[1:])
    if parsed is None:
        print("lint-complexity-debt: --report is required", file=sys.stderr)
        return 2
    baseline_path = Path(parsed.root).resolve() / "python" / "complexity-baseline.json"
    try:
        records = load_baseline(baseline_path)
        duplicates = find_duplicate_keys(records)
        if duplicates:
            raise BaselineError("duplicate baseline complexity identities:\n" + "\n".join(duplicates))
    except BaselineError as exc:
        print(f"lint-complexity-debt: {exc}", file=sys.stderr)
        return 2
    print(render_report(records, today=utc_today()), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
