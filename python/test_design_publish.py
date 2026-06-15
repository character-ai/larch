"""Tests for /design publish port."""

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
if args[:2] == ["plan","validate"]:
    print("VALIDATE_STATUS=ok")
    print("VALIDATE_DEFECT_COUNT=0")
    print("VALIDATE_SKIPPED_COUNT=0")
    print("VALIDATE_UNSAFE_TOKEN_COUNT=0")
    print("VALIDATE_LOG_FILE=/tmp/validate.log")
    raise SystemExit(0)
if args[:2] == ["redact","secrets"]:
    sys.stdout.write(sys.stdin.read())
    raise SystemExit(0)
if args[:2] == ["named-block","write"]:
    raise SystemExit(0)
if args[:2] == ["tracking-issue","rename"]:
    print("RENAMED=true")
    print("NEW_TITLE=[DESIGNED] Example")
    raise SystemExit(0)
if args[:3] == ["design","log-publish","--design-tmpdir"] or args[:2] == ["design","log-publish"]:
    print("PUBLISH_OK=true")
    print("PR_NUMBER=99")
    print("PR_URL=https://github.com/owner/repo/pull/99")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def test_publish_requires_composed_plan(tmp_path: Path) -> None:
    cli_py = Path(__file__).with_name("cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "PLAN_WRITE_OK=false" in result.stdout
    assert "VALIDATE_STATUS=defects-found" in result.stdout


def test_publish_success_writes_result_env(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n", encoding="utf-8")
    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
            "--repo",
            "owner/repo",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PLAN_WRITE_OK=true" in result.stdout
    assert "PUBLISH_OK=true" in result.stdout
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    assert "review_status:" not in composed.split("diff_lines:")[0]
    result_env = (design / ".design-publish-result.env").read_text(encoding="utf-8")
    assert "PR_NUMBER=99" in result_env


def test_publish_refuses_cap_hit_without_step3_sentinel(tmp_path: Path) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=cap-hit\nLOOP_STATUS=cap-reached\nROUNDS_COMPLETED=5\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).with_name("cli.py")
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "cap-hit without .completed/step-3" in result.stdout


def test_publish_refuses_complete_without_step3_sentinel(tmp_path: Path) -> None:
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text("# plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\nROUNDS_COMPLETED=3\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).with_name("cli.py")
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 4
    assert "complete without .completed/step-3" in result.stdout


def test_publish_splices_provenance_above_diff_lines(tmp_path: Path) -> None:
    plugin_root = tmp_path / "plugin"
    _write_fake_cli(plugin_root / "python" / "cli.py")
    design = tmp_path / "design"
    (design / ".completed").mkdir(parents=True)
    _ = (design / ".completed" / "step-5b").write_text("", encoding="utf-8")
    _ = (design / ".completed" / "step-3").write_text("", encoding="utf-8")
    _ = (design / "composed-plan.md").write_text(
        "## Plan\nbody\n\ndiff_lines: 3\n",
        encoding="utf-8",
    )
    _ = (design / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nROUNDS_COMPLETED=2\n",
        encoding="utf-8",
    )
    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [
            sys.executable,
            str(cli_py),
            "design",
            "publish",
            "--design-tmpdir",
            str(design),
            "--issue",
            "9",
            "--session-id",
            "RUN1",
            "--claude-pid",
            "11",
        ],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0, result.stderr
    composed = (design / "composed-plan.md").read_text(encoding="utf-8")
    lines = composed.splitlines()
    diff_idx = next(i for i, line in enumerate(lines) if line.startswith("diff_lines:"))
    assert lines[diff_idx - 2] == "review_status: complete"
    assert lines[diff_idx - 1] == "rounds_completed: 2"
    assert lines[0] == "## Plan"
