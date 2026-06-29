"""Tests for /implement Step 1 plan-log helper port."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path

from larch import cli


def test_plan_step1_log_registered_as_machine_stdout() -> None:
    assert cli._REGISTRY[("plan", "step1-log")] == ("larch.design.design_step_log", "step1_log_main")  # pyright: ignore[reportPrivateUsage]
    assert ("plan", "step1-log") in cli._MACHINE_STDOUT_KEYS  # pyright: ignore[reportPrivateUsage]


def _make_exec(path: Path, body: str) -> None:
    _ = path.write_text(body, encoding="utf-8")
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_step1_log_overrides_compose_and_log(tmp_path: Path) -> None:
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    work = tmp_path / "impl"
    work.mkdir()
    _ = (work / "session-env.sh").write_text("LARCH_CLAUDE_PLUGIN_ROOT=/repo\n", encoding="utf-8")
    _ = (work / "session-id").write_text("run-session\n", encoding="utf-8")
    _ = (work / "plan.txt").write_text("Plan\n", encoding="utf-8")
    compose_args = tmp_path / "compose.args"
    log_args = tmp_path / "log.args"
    compose = tmp_path / "compose.sh"
    log = tmp_path / "log.sh"
    _make_exec(
        compose,
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$RUN_STEP1_COMPOSE_ARGV_FILE\"\nprintf '## Goal\\nX\\n'\n",
    )
    _make_exec(
        log,
        "#!/usr/bin/env bash\nprintf '%s\\n' \"$@\" > \"$RUN_STEP1_LOG_ARGV_FILE\"\nprintf 'LOG_WRITTEN=true\\n'\n",
    )

    env = os.environ.copy()
    env["RUN_STEP1_COMPOSE_CMD"] = str(compose)
    env["RUN_STEP1_LARCH_LOG_SH"] = str(log)
    env["RUN_STEP1_COMPOSE_ARGV_FILE"] = str(compose_args)
    env["RUN_STEP1_LOG_ARGV_FILE"] = str(log_args)
    env["CLAUDE_PLUGIN_ROOT"] = str(tmp_path)
    result = subprocess.run(
        [sys.executable, str(cli_py), "plan", "step1-log", "--implement-tmpdir", str(work), "--goal-text", "Ship launcher"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "LOG_WRITTEN=true" in result.stdout
    assert "--plan-file" in compose_args.read_text(encoding="utf-8")
    assert "Ship launcher" in compose_args.read_text(encoding="utf-8")
    assert "--batch" in log_args.read_text(encoding="utf-8")
    assert "plan-goals-test" in log_args.read_text(encoding="utf-8")
    assert (work / "plan-goals-test.md").read_text(encoding="utf-8").startswith("## Goal")


def test_step1_log_requires_conventional_plan_file(tmp_path: Path) -> None:
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    work = tmp_path / "impl"
    work.mkdir()
    _ = (work / "session-env.sh").write_text("LARCH_CLAUDE_PLUGIN_ROOT=/repo\n", encoding="utf-8")
    _ = (work / "session-id").write_text("run-session\n", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(cli_py), "plan", "step1-log", "--implement-tmpdir", str(work), "--goal-text", "x"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 2
    assert "plan file not found at conventional path" in result.stderr
