"""Tests for /design postplan emit Python port."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from larch.calibration import difficulty
from larch.design import design_postplan, design_step5c


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
    assert "STEP2B5_NEXT_ACTION=under-threshold" in result_env


def test_postplan_with_plan_size_writes_design_difficulty_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    _postplan_fixture(design, partition_requested=False)
    _ = (design / "plan.txt").write_text("## Plan\nbody\n\ndifficulty: MODERATE\ndiff_lines: 1\n", encoding="utf-8")
    _patch_postplan_cli(
        monkeypatch,
        tmp_path,
        check_size_rc=0,
        check_size_stdout="PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=false\nPLAN_LINES=10\nDIFF_LINES=12\n",
    )

    rc = design_postplan.postplan_emit_main(["--design-tmpdir", str(design), "--with-plan-size"])

    assert rc == 0
    raw = json.loads((design / difficulty.DESIGN_RAW_RATING_BASENAME).read_text(encoding="utf-8"))
    assert raw["predicted_tier"] == difficulty.MODERATE
    assert raw["confidence"] == "medium"


def _completed(args: Sequence[str], *, rc: int = 0, stdout: str = "", stderr: str = "") -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(args=list(args), returncode=rc, stdout=stdout, stderr=stderr)


def _postplan_fixture(design: Path, *, partition_requested: bool) -> None:
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    partition = "true" if partition_requested else "false"
    _ = (design / "run-params.json").write_text(f'{{"partition_requested": {partition}}}\n', encoding="utf-8")


def _patch_postplan_cli(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    *,
    check_size_rc: int,
    check_size_stdout: str,
    check_size_stderr: str = "",
) -> None:
    plugin_root = tmp_path / "plugin"
    plugin_root.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin_root))

    def fake_run_cli(_root: Path, *args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
        del env
        if args[:2] == ("plan-review", "json-get-bool"):
            path = Path(args[args.index("--path") + 1])
            value = "true" if '"partition_requested": true' in path.read_text(encoding="utf-8") else "false"
            return _completed(args, stdout=value + "\n")
        if args[:2] == ("plan-review", "emit"):
            return _completed(args, stdout="EMIT_PLAN_STATUS=ok\nDIFF_LINES=12\n")
        if args[:2] == ("plan", "validate"):
            return _completed(args, stdout="VALIDATE_STATUS=ok\nVALIDATE_DEFECT_COUNT=0\nVALIDATE_SKIPPED_COUNT=0\nVALIDATE_UNSAFE_TOKEN_COUNT=0\n")
        if args[:2] == ("plan", "check-size"):
            return _completed(args, rc=check_size_rc, stdout=check_size_stdout, stderr=check_size_stderr)
        if args[:2] == ("plan-review", "drift-baseline"):
            return _completed(args)
        if args[:2] == ("run-log", "append-failure"):
            return _completed(args)
        return _completed(args)

    monkeypatch.setattr(design_postplan, "_run_cli", fake_run_cli)


@pytest.mark.parametrize(
    ("partition_requested", "check_size_stdout", "expected_rc", "expected_action"),
    [
        (True, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=true\nDRIFT_TRIGGER_FIRED=true\nPLAN_LINES=10\n", 12, "hard-trigger"),
        (True, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=false\nPLAN_LINES=10\n", 13, "partition-split"),
        (False, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=true\nPLAN_LINES=10\n", 0, "drift-advisory"),
        (False, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=false\nPLAN_LINES=10\n", 0, "under-threshold"),
    ],
)
def test_postplan_with_plan_size_writes_step2b5_action_for_triggers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    partition_requested: bool,
    check_size_stdout: str,
    expected_rc: int,
    expected_action: str,
) -> None:
    design = tmp_path / "design"
    _postplan_fixture(design, partition_requested=partition_requested)
    _patch_postplan_cli(monkeypatch, tmp_path, check_size_rc=0, check_size_stdout=check_size_stdout)

    rc = design_postplan.postplan_emit_main(["--design-tmpdir", str(design), "--with-plan-size"])

    assert rc == expected_rc
    result_env = (design / ".design-postplan-emit-result.env").read_text(encoding="utf-8")
    assert f"STEP2B5_NEXT_ACTION={expected_action}" in result_env


def test_postplan_with_plan_size_preserves_rc2_warning(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    design = tmp_path / "design"
    _postplan_fixture(design, partition_requested=False)
    _patch_postplan_cli(
        monkeypatch,
        tmp_path,
        check_size_rc=2,
        check_size_stdout="PLAN_SIZE_STATUS=missing-diff-lines\n",
    )

    rc = design_postplan.postplan_emit_main(["--design-tmpdir", str(design), "--with-plan-size"])

    assert rc == 2
    result_env = (design / ".design-postplan-emit-result.env").read_text(encoding="utf-8")
    assert "STEP2B5_NEXT_ACTION=rc2-warning" in result_env
    assert "STEP2B5_EXIT_RC=2" in result_env
    assert (design / "check-plan-size.validation.log").read_text(encoding="utf-8") == "PLAN_SIZE_STATUS=missing-diff-lines\n"


def _kv_value(text: str, key: str) -> str:
    prefix = key + "="
    for line in text.splitlines():
        if line.startswith(prefix):
            return line[len(prefix) :]
    return ""


@pytest.mark.parametrize(
    ("partition_requested", "check_size_rc", "check_size_stdout"),
    [
        (True, 0, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=true\nDRIFT_TRIGGER_FIRED=true\nPLAN_LINES=10\n"),
        (True, 0, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=true\nPLAN_LINES=10\n"),
        (False, 0, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=true\nPLAN_LINES=10\n"),
        (False, 0, "PLAN_SIZE_STATUS=ok\nSIZE_TRIGGER_FIRED=false\nDRIFT_TRIGGER_FIRED=false\nPLAN_LINES=10\n"),
        (False, 2, "PLAN_SIZE_STATUS=missing-diff-lines\n"),
        (False, 7, "PLAN_SIZE_STATUS=failed\n"),
    ],
)
def test_step2b5_and_postplan_emit_action_parity(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    partition_requested: bool,
    check_size_rc: int,
    check_size_stdout: str,
) -> None:
    design_direct = tmp_path / "direct"
    _postplan_fixture(design_direct, partition_requested=partition_requested)
    monkeypatch.setenv("DESIGN_TMPDIR", str(design_direct))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(tmp_path / "plugin-direct"))

    def fake_check(_argv: list[str]) -> int:
        print(check_size_stdout, end="")
        return check_size_rc

    monkeypatch.setattr(design_step5c.plan_quality, "check_plan_size_main", fake_check)
    monkeypatch.setattr(design_step5c, "_step2b5_self_log", lambda **_kw: None)  # type: ignore[arg-type]
    direct_rc = design_step5c.step2b5_main([])
    direct_stdout = capsys.readouterr().out

    design_postplan_dir = tmp_path / "postplan"
    _postplan_fixture(design_postplan_dir, partition_requested=partition_requested)
    _patch_postplan_cli(monkeypatch, tmp_path, check_size_rc=check_size_rc, check_size_stdout=check_size_stdout)
    postplan_rc = design_postplan.postplan_emit_main(["--design-tmpdir", str(design_postplan_dir), "--with-plan-size"])
    result_env = (design_postplan_dir / ".design-postplan-emit-result.env").read_text(encoding="utf-8")

    assert _kv_value(direct_stdout, "STEP2B5_NEXT_ACTION") == _kv_value(result_env, "STEP2B5_NEXT_ACTION")
    assert direct_rc == int(_kv_value(result_env, "STEP2B5_EXIT_RC"))
    if check_size_rc != 0:
        assert postplan_rc == direct_rc


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
        print("LARCH_REQUIRE_PLAN_DIFFICULTY=" + os.environ.get("LARCH_REQUIRE_PLAN_DIFFICULTY", ""), file=fh)
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
    assert recorded["LARCH_REQUIRE_PLAN_DIFFICULTY"] == "1"
