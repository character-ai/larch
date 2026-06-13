# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false, reportArgumentType=false
from __future__ import annotations
# ruff: noqa: UP022

import os
import subprocess
import sys
from pathlib import Path

import plan_quality

CLI = Path(__file__).with_name("cli.py")


def run_cli(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd, text=True, capture_output=True, env=merged, check=False)


def test_parse_plan_commands_fenced_invocation_and_allowlist(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    plan = """## Plan
### NEW: skills/demo/scripts/new-helper.sh
### UPDATED: skills/demo/scripts/existing.sh
- Adds flag: `--new-flag`
```bash
env LARCH_DRY_RUN=1 ./skills/demo/scripts/existing.sh --known value --new-flag=ok \\
  --another next && bash scripts/tool.sh --flag
cat <<'EOF'
ignored --not-a-command
EOF
```
diff_lines: 1
"""
    rows = plan_quality.parse_plan_commands(plan, repo, repo)
    tsv = plan_quality.render_plan_command_tsv(rows)
    assert "new_script\t2\tskills/demo/scripts/new-helper.sh" in tsv
    assert "updated_flag\t4\tskills/demo/scripts/existing.sh\tnew-flag" in tsv
    assert "invocation\t6\t./skills/demo/scripts/existing.sh\tknown\tvalue" in tsv
    assert "invocation\t6\tscripts/tool.sh\tflag" in tsv
    assert "not-a-command" not in tsv


def test_parse_plan_commands_notes_for_unsafe_shell_forms(tmp_path: Path) -> None:
    plan = """```sh
scripts/a.sh --x $(date)
scripts/b.sh --x <(cat y)
eval scripts/c.sh
sh -c 'scripts/d.sh --x y'
```
"""
    notes = [row.note for row in plan_quality.parse_plan_commands(plan, tmp_path, tmp_path) if row.row_type == "parse_note"]
    assert notes == ["subshell", "process_substitution", "eval", "inline-shell"]


def test_optional_trailer_snapshot_and_validate_values(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("body\ndiff_added: 10\ndiff_deleted: 2\nmechanical_churn: false\ndiff_lines: 12\n")
    keys = tmp_path / "keys"
    cp = run_cli("plan", "optional-trailers", "snapshot-keys", "--plan-file", str(plan), "--output", str(keys))
    assert cp.returncode == 0, cp.stderr
    assert keys.read_text() == "diff_added\ndiff_deleted\nmechanical_churn\n"
    assert keys.with_name(keys.name + ".values").read_text() == "diff_added=10\ndiff_deleted=2\nmechanical_churn=false\n"
    assert run_cli("plan", "optional-trailers", "validate-values", "--plan-file", str(plan), "--values-file", str(keys) + ".values").returncode == 0


def test_check_plan_size_log_contract_and_mechanical_churn(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("line\n" * 4 + "diff_added: 2500\nmechanical_churn: true\ndiff_lines: 2500\n")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["SIZE_TRIGGER_FIRED"] == "false"
    assert out["SOFT_ADVISORY"] == "true"
    assert out["DIFF_ADDED"] == "2500"
    assert (tmp_path / ".larch-drift-baseline.env").is_file()


def test_validate_plan_emits_stable_log_in_design_tmpdir(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "demo.sh"
    script.parent.mkdir()
    script.write_text("#!/usr/bin/env bash\necho 'usage: demo --known'\n")
    script.chmod(0o755)
    (tmp_path / "scripts" / "dry-runnable-scripts.tsv").write_text("script\thook\n")
    subprocess.run(["git", "init"], cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    plan = tmp_path / "plan.txt"
    plan.write_text("```bash\nscripts/demo.sh --unknown\n```\ndiff_lines: 1\n")
    cp = run_cli("plan", "validate", "--plan-file", str(plan), "--repo-root", str(tmp_path), "--design-tmpdir", str(tmp_path), cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["VALIDATE_STATUS"] == "defects-found"
    assert out["VALIDATE_LOG_FILE"] == str(tmp_path / "validate-plan-commands.log")
    assert (tmp_path / "validate-plan-commands.log").read_text().endswith("UNSAFE_TOKEN_COUNT=0\n")


def test_compose_plan_goals_test_rejects_short_pointer(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("TBD\n" + "x" * 80)
    cp = run_cli("plan", "compose-goals-test", "--plan-file", str(plan), "--goal-text", "ship it")
    assert cp.returncode == 2


def test_compose_plan_goals_test_extracts_testing_section(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Implementation Plan\n## Plan\nDo work.\n## Test Strategy\nRun pytest.\n" + "x" * 80 + "\n")
    cp = run_cli("plan", "compose-goals-test", "--plan-file", str(plan), "--goal-text", "ship it")
    assert cp.returncode == 0, cp.stderr
    assert cp.stdout.startswith("## Goal\nship it\n\n## Implementation Plan\nDo work.")
    assert "## Test plan\nRun pytest." in cp.stdout


def test_auto_fix_unavailable_contract(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndiff_lines: 1\n")
    cp = run_cli(
        "plan",
        "auto-fix-commands",
        "--design-tmpdir",
        str(tmp_path),
        "--plan-file",
        str(plan),
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["AUTOFIX_STATUS"] == "unavailable"
    assert out["ATTEMPTS"] == "0"


def test_revise_plan_with_waterfall_records_failed_no_patch(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n")
    findings = tmp_path / "findings.txt"
    findings.write_text("finding\n")
    feature = tmp_path / "feature-description.txt"
    feature.write_text("feature\n")
    fake = tmp_path / "fake-launch.sh"
    fake.write_text('#!/usr/bin/env bash\nwhile [ $# -gt 0 ]; do case "$1" in --output) out=$2; shift 2;; *) shift;; esac; done\n: > "$out"\nexit 0\n')
    fake.chmod(0o755)
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
    }
    cp = run_cli(
        "plan",
        "revise-waterfall",
        "--design-tmpdir",
        str(tmp_path),
        "--plan-file",
        str(plan),
        "--findings-file",
        str(findings),
        "--feature-file",
        str(feature),
        "--round-num",
        "1",
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "failed-no-patch"
    assert out["REVISE_TIER_1_STATUS"] == "skipped-not-present"
    assert (tmp_path / "plan-review" / "round-1" / "revise" / "revise.env").is_file()
