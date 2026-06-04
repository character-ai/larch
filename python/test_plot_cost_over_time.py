from __future__ import annotations

import py_compile
import subprocess
import sys
import json
from pathlib import Path


def test_plot_script_py_compile() -> None:
    _ = py_compile.compile("../skills/report-tokens/scripts/plot-cost-over-time.py", doraise=True)


def test_plot_script_optional_smoke(tmp_path: Path) -> None:
    script = Path("../skills/report-tokens/scripts/plot-cost-over-time.py")
    payload = {"version": 1, "skill": "implement", "series": [{"label": "All runs", "points": [{"date": "2026-01-01", "cost": 1.0}]}]}
    input_path = tmp_path / "plot.json"
    _ = input_path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, str(script), str(input_path), str(tmp_path)], capture_output=True, text=True, check=False)
    if result.returncode == 3:
        return
    assert result.returncode == 0
    assert json.loads(result.stdout)


def test_plot_script_rejects_unsafe_label(tmp_path: Path) -> None:
    script = Path("../skills/report-tokens/scripts/plot-cost-over-time.py")
    payload = {"version": 1, "skill": "implement", "series": [{"label": "../escape", "points": [{"date": "2026-01-01", "cost": 1.0}]}]}
    input_path = tmp_path / "plot.json"
    _ = input_path.write_text(json.dumps(payload), encoding="utf-8")
    result = subprocess.run([sys.executable, str(script), str(input_path), str(tmp_path)], capture_output=True, text=True, check=False)
    assert result.returncode == 2
    assert "unsafe series label" in result.stderr
