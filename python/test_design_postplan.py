"""Tests for /design postplan emit Python port."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path


def _write_fake_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import sys
args = sys.argv[1:]
if args[:2] == ["plan-review","emit"]:
    print("EMIT_PLAN_STATUS=ok")
    print("DIFF_LINES=12")
    raise SystemExit(0)
if args[:2] == ["plan","validate"]:
    print("VALIDATE_STATUS=defects-found")
    print("VALIDATE_DEFECT_COUNT=2")
    raise SystemExit(1)
if args[:2] == ["plan","check-size"]:
    print("PLAN_SIZE_STATUS=under-threshold")
    print("SIZE_TRIGGER_FIRED=false")
    print("DRIFT_TRIGGER_FIRED=false")
    print("PLAN_LINES=10")
    print("DIFF_LINES=12")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_postplan_with_plan_size_returns_pause_code(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / "run-params.json").write_text('{"partition_requested": false}\n', encoding="utf-8")
    _ = (design / ".pause-requested").write_text("", encoding="utf-8")
    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "postplan-emit", "--design-tmpdir", str(design), "--with-plan-size"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 11
    assert "POSTPLAN_EMIT_STATUS=paused" in result.stdout


def test_postplan_with_plan_size_returns_defect_code(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / "run-params.json").write_text('{"partition_requested": false}\n', encoding="utf-8")
    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "postplan-emit", "--design-tmpdir", str(design), "--with-plan-size"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 10
    result_env = (design / ".design-postplan-emit-result.env").read_text(encoding="utf-8")
    assert "VALIDATE_STATUS=defects-found" in result_env
