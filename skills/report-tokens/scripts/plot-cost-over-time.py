#!/usr/bin/env python3
"""Render report-token cost-over-time PNGs from a small JSON contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import cast

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except Exception as exc:  # pragma: no cover - depends on optional dependency
    print(f"matplotlib unavailable: {exc}", file=sys.stderr)
    raise SystemExit(3) from exc


def _load(path: Path) -> dict[str, object]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("plot input must be a JSON object")
    return cast("dict[str, object]", data)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: plot-cost-over-time.py <plot-input.json> <output-dir>", file=sys.stderr)
        return 2
    data = _load(Path(argv[1]))
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    skill = str(data.get("skill"))
    series = data.get("series")
    if not isinstance(series, list):
        print("plot input series must be a list", file=sys.stderr)
        return 2
    written: list[str] = []
    for item in series:
        if not isinstance(item, dict):
            continue
        label = str(item.get("label") or "series")
        points = item.get("points")
        if not isinstance(points, list):
            continue
        dates: list[str] = []
        costs: list[float] = []
        for point in points:
            if not isinstance(point, dict):
                continue
            dates.append(str(point.get("date") or ""))
            costs.append(float(point.get("cost") or 0.0))
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dates, costs, marker="o")
        ax.set_title(f"{skill} token cost over time — {label}")
        ax.set_ylabel("USD")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        name = label.lower().replace(" ", "-")
        path = (out_dir / f"larch-report-tokens-{name}.png").resolve()
        fig.savefig(path)
        plt.close(fig)
        written.append(str(path))
    print(json.dumps(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
