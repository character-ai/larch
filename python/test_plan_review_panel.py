from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "python" / "cli.py"


def run_cli(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(ROOT)
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_panel_dispatch_usage_failure() -> None:
    proc = run_cli("plan-review", "panel-dispatch")
    assert proc.returncode == 2
    assert proc.stderr


def test_voter_dispatch_usage_failure() -> None:
    proc = run_cli("plan-review", "voter-dispatch")
    assert proc.returncode == 2
    assert proc.stderr


def test_plan_review_cli_registry_contains_panel_verbs() -> None:
    proc = run_cli("--help")
    assert proc.returncode == 0
    assert "plan-review panel-dispatch" in proc.stdout
    assert "plan-review voter-dispatch" in proc.stdout
