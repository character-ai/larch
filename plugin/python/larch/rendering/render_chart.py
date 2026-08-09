# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false, reportUnknownParameterType=false, reportMissingParameterType=false, reportUnusedImport=false, reportUnusedFunction=false, reportPrivateUsage=false, reportUnusedVariable=false
# ruff: noqa: PERF401, PLR1714, UP006, UP035
# pylint: skip-file
"""Compatibility renderer for residual Python report helpers.

`analyze-issues render-chart` moved to Rust in #8092, and the remaining
`analyze-issues` verbs moved in #8183. `larch_core::report::growth_chart` owns
the live renderer and TSV grammar; this function remains only for Python
helpers that have not yet retired their in-process import.
"""

from __future__ import annotations

from typing import List, Sequence, Tuple


def render_chart(*, buckets: Sequence[str], rows: Sequence[Tuple[str, str, Sequence[int]]]) -> str:
    if not rows or not buckets:
        return "No growth data available."

    width = len(buckets)
    max_final = max((values[-1] if values else 0) for _, _, values in rows)
    max_final = max(max_final, 1)
    canvas: List[List[str]] = [["." for _ in range(width)] for _ in range(len(rows))]

    for key, _label, values in rows:
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
