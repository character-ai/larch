"""Subprocess-isolated plotting for /report-tokens."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
from collections import defaultdict
from typing import cast

from larch.core import config
from larch.core import redact
from larch.core.proc import Runner
from report_tokens_models import RunRecord, Skill, record_date, workflow_groups

def _env_flag_enabled(name: str) -> bool:
    value = os.environ.get(name, "").strip().lower()
    return value not in ("", "0", "false", "no")

def _series(*, skill: Skill, records: tuple[RunRecord, ...]) -> list[dict[str, object]]:
    output: list[dict[str, object]] = []
    groups = workflow_groups(_skill=skill, records=records)
    labels = ["All runs"]
    for label in labels:
        by_day: dict[str, float] = defaultdict(float)
        for record in groups.get(label, []):
            day = record_date(record)
            if day is None:
                continue
            by_day[day] += record.total_cost
        output.append({
            "label": label,
            "points": [{"date": day, "cost": round(by_day[day], 2)} for day in sorted(by_day)],
        })
    return output


def plot(
    runner: Runner,
    *,
    skill: Skill,
    records: tuple[RunRecord, ...],
    plot_parent_dir: Path,
    no_plot: bool = False,
    plugin_root: Path | None = None,
) -> list[Path]:
    if no_plot or _env_flag_enabled(config.ENV_LARCH_REPORT_TOKENS_NO_PLOT):
        return []
    root = plugin_root or Path(os.environ.get("CLAUDE_PLUGIN_ROOT", Path(__file__).resolve().parents[1]))
    script = root / "skills" / "report-tokens" / "scripts" / "plot-cost-over-time.py"
    plot_dir = Path(tempfile.mkdtemp(prefix="larch-report-tokens-plot.", dir=plot_parent_dir))
    mpl_dir = plot_dir / "mpl"
    mpl_dir.mkdir(parents=True, exist_ok=True)
    input_path = plot_dir / "plot-input.json"
    _ = input_path.write_text(json.dumps({"version": 1, "skill": skill, "series": _series(skill=skill, records=records)}, sort_keys=True), encoding="utf-8")
    env = dict(os.environ)
    env["MPLCONFIGDIR"] = str(mpl_dir)
    result = runner.run([sys.executable, str(script), str(input_path), str(plot_dir)], env=env)
    if result.returncode != 0:
        detail = redact.redact((result.stderr or result.stdout).strip()).strip()
        suffix = f": {detail[:160]}" if detail else ""
        print(f"No plots generated (plot child failed{suffix}).", file=sys.stderr)
        return []
    try:
        raw_paths = json.loads(result.stdout)
    except json.JSONDecodeError:
        print("No plots generated (plot child returned invalid JSON).", file=sys.stderr)
        return []
    if not isinstance(raw_paths, list):
        print("No plots generated (plot child returned non-list JSON).", file=sys.stderr)
        return []
    path_items = cast("list[object]", raw_paths)
    paths: list[Path] = []
    try:
        resolved_plot_dir = plot_dir.resolve(strict=True)
    except OSError:
        print("No plots generated (plot directory disappeared).", file=sys.stderr)
        return []
    for item in path_items:
        path = Path(str(item))
        try:
            resolved = path.resolve(strict=True)
        except OSError:
            print("No plots generated (plot child returned missing path).", file=sys.stderr)
            return []
        if not path.is_file() or not (resolved == resolved_plot_dir or resolved_plot_dir in resolved.parents):
            print("No plots generated (plot child returned path outside plot directory).", file=sys.stderr)
            return []
        paths.append(path)
    if sys.platform == "darwin" and not os.environ.get(config.ENV_LARCH_REPORT_TOKENS_NO_OPEN):
        for path in paths:
            _ = runner.run(["open", str(path)])
    return paths
