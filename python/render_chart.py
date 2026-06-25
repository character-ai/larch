# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: PERF401, PLR1714, PLR2004, PTH123, UP006, UP015, UP035
# pylint: skip-file
"""Render a compact ASCII cumulative-growth chart from TSV input."""

from __future__ import annotations

import argparse
import sys
from typing import Iterable, List, Sequence, Tuple


def parse_tsv(text: str) -> Tuple[List[str], List[Tuple[str, str, List[int]]]]:
    lines = [line.rstrip("\n") for line in text.splitlines() if line.strip()]
    if not lines:
        return [], []
    header = lines[0].split("\t")
    buckets = header[2:]
    rows = []
    for line in lines[1:]:
        parts = line.split("\t")
        if len(parts) < 3:
            continue
        key, label = parts[0], parts[1]
        values = [int(value or "0") for value in parts[2:]]
        rows.append((key, label, values))
    return buckets, rows


def render_chart(*, buckets: Sequence[str], rows: Sequence[Tuple[str, str, Sequence[int]]]) -> str:
    if not rows or not buckets:
        return "No growth data available."

    width = len(buckets)
    max_final = max((values[-1] if values else 0) for _, _, values in rows)
    max_final = max(max_final, 1)
    canvas = [["." for _ in range(width)] for _ in range(len(rows))]

    for _row_index, (key, _label, values) in enumerate(rows):
        for col_index, value in enumerate(values[:width]):
            if value <= 0:
                continue
            scaled = max(0, min(len(rows) - 1, round((value / max_final) * (len(rows) - 1))))
            target = len(rows) - 1 - scaled
            existing = canvas[target][col_index]
            canvas[target][col_index] = key if existing == "." or existing == key else "*"

    output = ["Cumulative growth chart"]
    output.append(f"Buckets: {buckets[0]} -> {buckets[-1]} ({len(buckets)} buckets)")
    for line in canvas:
        output.append("".join(line))
    output.append("Legend:")
    for key, label, values in rows:
        final = values[-1] if values else 0
        output.append(f"  {key}: {label} ({final})")
    return "\n".join(output)


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", nargs="?")
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.path:
        with open(args.path, "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        text = sys.stdin.read()
    buckets, rows = parse_tsv(text)
    print(render_chart(buckets=buckets, rows=rows))
    return 0




def render_chart_main(argv: Iterable[str] | None = None) -> int:
    return main(argv)
