#!/usr/bin/env python3
"""Render report-token cost-over-time PNGs from a small JSON contract."""

from __future__ import annotations

import json
import re
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


_LABEL_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,80}$")
_DATE_RE = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}$")


def _safe_name(label: str) -> str:
    if not _LABEL_RE.fullmatch(label):
        raise ValueError(f"unsafe series label: {label!r}")
    return label.lower().replace(" ", "-")


def _validate_series(skill: str, series: object) -> list[dict[str, object]]:
    expected = ["All runs"] if skill == "implement" else ["SIMPLE", "HARD"]
    if not isinstance(series, list):
        raise ValueError("plot input series must be a list")
    items = cast("list[object]", series)
    if len(items) != len(expected):
        raise ValueError(f"plot input for {skill} must contain {len(expected)} series")
    validated: list[dict[str, object]] = []
    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError("plot input series items must be objects")
        item_map = cast("dict[str, object]", item)
        label = item_map.get("label")
        if label != expected[index]:
            raise ValueError(f"plot input series label must be {expected[index]!r}")
        points = item_map.get("points")
        if not isinstance(points, list):
            raise ValueError("plot input series points must be lists")
        for point in cast("list[object]", points):
            if not isinstance(point, dict):
                raise ValueError("plot input points must be objects")
            point_map = cast("dict[str, object]", point)
            date = point_map.get("date")
            cost = point_map.get("cost")
            if not isinstance(date, str) or not _DATE_RE.fullmatch(date):
                raise ValueError("plot input point date must be YYYY-MM-DD")
            if isinstance(cost, bool) or not isinstance(cost, (int, float)):
                raise ValueError("plot input point cost must be numeric")
        validated.append(item_map)
    return validated


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: plot-cost-over-time.py <plot-input.json> <output-dir>", file=sys.stderr)
        return 2
    try:
        data = _load(Path(argv[1]))
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    out_dir = Path(argv[2])
    out_dir.mkdir(parents=True, exist_ok=True)
    skill = str(data.get("skill"))
    if data.get("version") != 1:
        print("plot input version must be 1", file=sys.stderr)
        return 2
    if skill not in ("design", "implement"):
        print("plot input skill must be design or implement", file=sys.stderr)
        return 2
    try:
        series = _validate_series(skill, data.get("series"))
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    written: list[str] = []
    for item in series:
        label = str(item["label"])
        try:
            name = _safe_name(label)
        except ValueError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        points = cast("list[dict[str, object]]", item["points"])
        dates: list[str] = []
        costs: list[float] = []
        for point in points:
            dates.append(str(point["date"]))
            costs.append(float(point["cost"]))
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(dates, costs, marker="o")
        ax.set_title(f"{skill} token cost over time — {label}")
        ax.set_ylabel("USD")
        ax.tick_params(axis="x", rotation=45)
        ax.grid(True, alpha=0.25)
        fig.tight_layout()
        path = (out_dir / f"larch-report-tokens-{name}.png").resolve()
        resolved_out = out_dir.resolve()
        if not (path == resolved_out or resolved_out in path.parents):
            print(f"unsafe output path for series label: {label!r}", file=sys.stderr)
            return 2
        fig.savefig(path)
        plt.close(fig)
        written.append(str(path))
    print(json.dumps(written))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
