"""Generic ASCII Gantt chart renderer."""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

DEFAULT_WIDTH = 56
SECONDS_PER_MINUTE = 60
TSV_COLUMN_COUNT = 3


@dataclass(frozen=True)
class GanttRow:
    label: str
    start_s: int
    end_s: int


def format_mss(seconds: int) -> str:
    """Format non-negative seconds as m:ss for chart axes and titles."""
    value = max(0, int(seconds))
    minutes = value // SECONDS_PER_MINUTE
    secs = value % SECONDS_PER_MINUTE
    return f"{minutes}:{secs:02d}"


def _round_half_up(value: float) -> int:
    return int(value + 0.5)


def _bar(*, start_s: int, end_s: int, window_start_s: int, span: int, width: int) -> str:
    rel_start = max(0, start_s - window_start_s)
    rel_end = max(0, end_s - window_start_s)
    rounded_start = min(width, max(0, _round_half_up(rel_start * width / span)))
    rounded_end = min(width, max(0, _round_half_up(rel_end * width / span)))
    start_col = min(width - 1, max(0, rounded_start))
    end_col = min(width, max(start_col + 1, rounded_end))
    return " " * start_col + "█" * (end_col - start_col) + " " * (width - end_col)


def _axis(*, label_width: int, width: int, span_label: str) -> str:
    track_start = label_width + 2
    track_end = track_start + width - 1
    chars = [" "] * (track_end + 1)
    left = "0:00"
    for idx, char in enumerate(left):
        pos = track_start + idx
        if pos < len(chars):
            chars[pos] = char
    right_start = max(track_start, track_end - len(span_label) + 1)
    for idx, char in enumerate(span_label):
        pos = right_start + idx
        if pos < len(chars):
            chars[pos] = char
    return "".join(chars).rstrip()


def render_gantt(
    *, window_start_s: int,
    window_end_s: int,
    rows: Sequence[GanttRow],
    width: int | None = None,
) -> str:
    """Render rows as a plain ASCII Gantt chart."""
    use_default_width = width is None
    normalized_width = DEFAULT_WIDTH if use_default_width else width
    width = max(1, int(normalized_width))
    span = max(1, int(window_end_s) - int(window_start_s))
    filtered: list[tuple[GanttRow, int, int, int]] = []
    for row in rows:
        clamped_start = max(int(window_start_s), int(row.start_s))
        clamped_end = min(int(window_end_s), int(row.end_s))
        if clamped_end <= clamped_start:
            continue
        filtered.append((row, clamped_start, clamped_end, clamped_end - clamped_start))
    if not filtered:
        return ""

    label_width = max(len(row.label) for row in rows)
    duration_width = max(len(f"{duration}s") for _, _, _, duration in filtered)
    if use_default_width:
        width = min(width, max(10, 90 - label_width - duration_width - 4))
    prefix = " " * (label_width + 1)
    lines = [_axis(label_width=label_width, width=width, span_label=format_mss(span))]
    lines.append(f"{prefix}┌{'─' * width}┐")
    for row, clamped_start, clamped_end, duration in filtered:
        track = _bar(start_s=clamped_start, end_s=clamped_end, window_start_s=int(window_start_s), span=span, width=width)
        duration_text = f"{duration}s".rjust(duration_width)
        lines.append(f"{row.label.ljust(label_width)} │{track}│ {duration_text}")
    lines.append(f"{prefix}└{'─' * width}┘")
    return "\n".join(lines)


def _read_rows(path: Path) -> list[GanttRow]:
    rows: list[GanttRow] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        raise ValueError(f"cannot read rows TSV: {exc}") from exc
    for lineno, line in enumerate(lines, start=1):
        if not line:
            continue
        parts = line.split("\t")
        if len(parts) != TSV_COLUMN_COUNT:
            raise ValueError(f"malformed row {lineno}: expected 3 tab-delimited columns")
        label, start_raw, end_raw = parts
        try:
            start_s = int(start_raw)
            end_s = int(end_raw)
        except ValueError as exc:
            raise ValueError(f"malformed row {lineno}: start_s and end_s must be integers") from exc
        rows.append(GanttRow(label, start_s, end_s))
    return rows


def gantt_render_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py gantt render")
    _ = parser.add_argument("--window-start-s", type=int, required=True)
    _ = parser.add_argument("--window-end-s", type=int, required=True)
    _ = parser.add_argument("--rows-tsv", required=True)
    _ = parser.add_argument("--width", type=int, default=None)
    args = parser.parse_args(argv)
    if args.width is not None and args.width < 1:
        print("ERROR: --width must be positive", file=sys.stderr)
        return 2
    try:
        rows = _read_rows(Path(args.rows_tsv))
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2
    chart = render_gantt(window_start_s=args.window_start_s, window_end_s=args.window_end_s, rows=rows, width=args.width)
    if chart:
        print(chart)
    return 0
