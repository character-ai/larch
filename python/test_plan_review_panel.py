from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from test_support import run_cli


def _stdout_key_order(stdout: str) -> list[str]:
    keys: list[str] = []
    for line in stdout.splitlines():
        if "=" not in line:
            continue
        key = line.split("=", 1)[0]
        if key != "WARN":
            keys.append(key)
    return keys


def _write_waterfall_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "waterfall-stub.sh"
    _ = stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
slots=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --slots-file) slots="${2:?}"; shift 2 ;;
    --plan-file|--feature-file) shift 2 ;;
    --codex-present|--cursor-present|--mode|--timeout|--require-first-line-pattern|--no-fallback) shift 2 ;;
    *) shift 1 ;;
  esac
done
[[ -n "$slots" ]] || exit 2
n=$(grep -c . "$slots" || echo 0)
printf 'DISPATCH_OK=true\\n'
printf 'FALLBACK_COUNT=0\\n'
printf 'PHASE2_RELAUNCH_COUNT=0\\n'
printf 'COMBINED_FALLBACK_COUNT=0\\n'
printf 'STATIC_DISPATCH_OK=true\\n'
printf 'DYNAMIC_DISPATCH_OK=true\\n'
_outpath="$(dirname "${WATERFALL_STUB_LOG:?}")/a.txt"
: >"$_outpath"
if [[ -n "${WATERFALL_STUB_PATHS_OUT:-}" ]]; then
  : >"${WATERFALL_STUB_PATHS_OUT}"
  _i=0
  while IFS= read -r _row || [[ -n "$_row" ]]; do
    [[ -n "$_row" ]] || continue
    _i=$((_i + 1))
    ((_i <= n)) && printf '%s\\n' "$_outpath" >>"${WATERFALL_STUB_PATHS_OUT}"
  done <"$slots"
fi
printf 'ALL_OUTPUT_FILES=%s\\n' "$_outpath"
printf 'ALL_OUTPUT_TOOLS=cursor\\n'
printf 'ALL_OUTPUT_FILES_PATH=%s\\n' "${WATERFALL_STUB_PATHS_OUT:-$_outpath}"
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def _write_python3_agent_stub(tmp_path: Path) -> Path:
    stub_dir = tmp_path / "python3-stub-bin"
    stub_dir.mkdir()
    stub = stub_dir / "python3"
    _ = stub.write_text(
        f"""#!{sys.executable}
import os
import sys
from pathlib import Path

real_python = os.environ["PLAN_REVIEW_PANEL_REAL_PYTHON"]
args = sys.argv[1:]
if len(args) >= 3 and args[1:3] == ["agent", "launch-claude-review"]:
    output = ""
    idx = 3
    while idx < len(args):
        if args[idx] in ("--output", "--output-file") and idx + 1 < len(args):
            output = args[idx + 1]
            idx += 2
        elif args[idx] in (
            "--prompt-file",
            "--mode",
            "--role",
            "--read-tools-add-dir",
            "--timeout",
            "--timing-task-kind",
        ):
            idx += 2
        else:
            idx += 1
    if not output:
        raise SystemExit(2)
    Path(output).write_text(
        "FINDING_1: YES CORRECTNESS=true SEVERITY=minor QUALITY=good UNCERTAIN=false\\n",
        encoding="utf-8",
    )
    Path(output + ".done").write_text("0\\n", encoding="utf-8")
    raise SystemExit(0)
os.execv(real_python, [real_python, *args])
""",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub_dir


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


def test_panel_dispatch_static_slot_matrix(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps({"archetypes": []}),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DYNAMIC_SLOT_COUNT=0" in proc.stdout
    assert "PANEL_PATHS_FILE=" in proc.stdout
    manifest_lines = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8").splitlines()
    assert len([line for line in manifest_lines if line.strip()]) == 8


def test_panel_dispatch_dynamic_scout_rows(tmp_path: Path) -> None:
    design = tmp_path / "design-dynamic"
    design.mkdir()
    _ = (design / "plan.txt").write_text("Plan body.\n", encoding="utf-8")
    _ = (design / "feature-description.txt").write_text("feat\n", encoding="utf-8")
    _ = (design / "scout-plan-manifest.json").write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "alpha",
                        "focus_area": "correctness",
                        "weight": 2,
                        "rationale": "r1",
                        "prompt_body": "Check contracts.",
                    },
                    {
                        "name": "beta",
                        "focus_area": "architecture",
                        "weight": 2,
                        "rationale": "r2",
                        "prompt_body": "Check layering.",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    log = design / "wf.log"
    _ = log.write_text("", encoding="utf-8")
    stub = _write_waterfall_stub(tmp_path)
    proc = run_cli(
        "plan-review",
        "panel-dispatch",
        "--design-tmpdir",
        str(design),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        "--plan-file",
        str(design / "plan.txt"),
        "--feature-file",
        str(design / "feature-description.txt"),
        "--timeout",
        "60",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_PLAN_REVIEW_WATERFALL_SH": str(stub),
            "WATERFALL_STUB_LOG": str(log),
            "WATERFALL_STUB_PATHS_OUT": str(design / "paths.out"),
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "DYNAMIC_SLOT_COUNT=4" in proc.stdout
    manifest_lines = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8").splitlines()
    assert len([line for line in manifest_lines if line.strip()]) == 12
    manifest_text = (design / "plan-review-slots.ndjson").read_text(encoding="utf-8")
    assert "dyn-cursor-plan-alpha" in manifest_text
    assert "dyn-codex-plan-beta" in manifest_text


def test_voter_dispatch_absent_externals_falls_back_to_claude(tmp_path: Path) -> None:
    design = tmp_path / "absent"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "voter-dispatch",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "PATH": f"{_write_python3_agent_stub(tmp_path)}:{os.environ.get('PATH', '')}",
            "PLAN_REVIEW_PANEL_REAL_PYTHON": sys.executable,
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    assert "VOTER_1_STATUS=launched" in proc.stdout
    assert "VOTER_1_TOOL=claude" in proc.stdout
    assert "VOTER_2_STATUS=failed" in proc.stdout
    assert "VOTER_3_STATUS=failed" in proc.stdout
    assert "DISPATCH_OK=true" in proc.stdout
    assert "VOTER_PATHS_FILE=" in proc.stdout


def test_voter_dispatch_stdout_key_order(tmp_path: Path) -> None:
    design = tmp_path / "healthy"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text("### FINDING_1: test\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "voter-dispatch",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        "--codex-available",
        "false",
        "--cursor-available",
        "false",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "PATH": f"{_write_python3_agent_stub(tmp_path)}:{os.environ.get('PATH', '')}",
            "PLAN_REVIEW_PANEL_REAL_PYTHON": sys.executable,
        },
    )
    assert proc.returncode == 0, proc.stderr + proc.stdout
    expected = [
        "DEGRADED_PANEL_WARNING",
        "VOTER_1_PATH",
        "VOTER_1_TOOL",
        "VOTER_1_STATUS",
        "VOTER_1_PARSE_RATE_STATUS",
        "VOTER_2_PATH",
        "VOTER_3_PATH",
        "VOTER_PATHS_FILE",
        "VOTER_2_TOOL",
        "VOTER_3_TOOL",
        "VOTER_2_STATUS",
        "VOTER_3_STATUS",
        "VOTER_2_PARSE_RATE_STATUS",
        "VOTER_3_PARSE_RATE_STATUS",
        "DISPATCH_OK",
    ]
    assert _stdout_key_order(proc.stdout) == expected
