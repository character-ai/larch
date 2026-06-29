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
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
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
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
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


def _write_check_size_failure_cli(path: Path, calls_file: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    calls_path_repr = repr(str(calls_file))
    _ = path.write_text(
        f"""#!/usr/bin/env python3
import sys
args = sys.argv[1:]
if args[:2] == ["plan-review", "emit"]:
    print("EMIT_PLAN_STATUS=ok")
    print("DIFF_LINES=12")
    raise SystemExit(0)
if args[:2] == ["plan", "validate"]:
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    raise SystemExit(0)
if args[:2] == ["plan", "check-size"]:
    print("PLAN_SIZE_STATUS=failed", file=sys.stderr)
    raise SystemExit(1)
if args[:2] == ["run-log", "append-failure"]:
    site = args[args.index("--site") + 1] if "--site" in args else ""
    with open({calls_path_repr}, "a", encoding="utf-8") as fh:
        fh.write("append-failure site=" + site + "\\n")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_postplan_check_size_failure_self_logs(tmp_path: Path) -> None:
    """When --with-plan-size and check-size fails, append-failure is called."""
    plugin_root = tmp_path / "plugin"
    calls_file = tmp_path / "calls.log"
    _write_check_size_failure_cli(plugin_root / "python" / "cli.py", calls_file)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / "run-params.json").write_text('{"partition_requested": false}\n', encoding="utf-8")
    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "postplan-emit", "--design-tmpdir", str(design), "--with-plan-size"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 1
    assert calls_file.exists(), "append-failure was never called"
    # Regression (#5219): postplan check-size failures self-log against the
    # actual step (design Step 2b), not the hardcoded "design Step 2b.5".
    calls = calls_file.read_text(encoding="utf-8")
    assert "append-failure site=design Step 2b\n" in calls
    assert "design Step 2b.5" not in calls


def _write_recording_cli(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        """#!/usr/bin/env python3
import os
import sys
args = sys.argv[1:]
if args[:2] == ["plan-review", "emit"]:
    print("EMIT_PLAN_STATUS=ok")
    print("DIFF_LINES=12")
    raise SystemExit(0)
if args[:2] == ["plan", "validate"]:
    repo_root = ""
    for i, a in enumerate(args):
        if a == "--repo-root" and i + 1 < len(args):
            repo_root = args[i + 1]
    with open(os.environ["RECORD_FILE"], "w", encoding="utf-8") as fh:
        print("REPO_ROOT=" + repo_root, file=fh)
        print("CLAUDE_PLUGIN_ROOT=" + os.environ.get("CLAUDE_PLUGIN_ROOT", ""), file=fh)
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_postplan_passes_consumer_repo_root_and_preserves_plugin_root(tmp_path: Path) -> None:
    # cli.py lives in the plugin cache; the plan is validated from a separate
    # consumer git repo. The validator must receive the consumer repo as
    # --repo-root while CLAUDE_PLUGIN_ROOT stays pinned to the cache (#4490).
    plugin_root = tmp_path / "plugin"
    _write_recording_cli(plugin_root / "python" / "cli.py")
    recorder = tmp_path / "validate-invocation.env"

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _ = subprocess.run(["git", "init", "-q", str(consumer)], check=True)
    design = consumer / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / "run-params.json").write_text('{"partition_requested": false}\n', encoding="utf-8")

    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["RECORD_FILE"] = str(recorder)
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "postplan-emit", "--design-tmpdir", str(design)],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(consumer),
    )
    assert result.returncode == 0, result.stderr
    recorded = dict(
        line.split("=", 1) for line in recorder.read_text(encoding="utf-8").splitlines() if "=" in line
    )
    assert Path(recorded["REPO_ROOT"]).resolve() == consumer.resolve()
    assert Path(recorded["CLAUDE_PLUGIN_ROOT"]).resolve() == plugin_root.resolve()
