# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false, reportArgumentType=false
from __future__ import annotations
# ruff: noqa: UP022

import os
import subprocess
import sys
from pathlib import Path

import pytest

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
    assert (tmp_path / "drift-baseline.env").is_file()


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


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "skills" / "design" / "scripts" / "fixtures" / "parse-plan-commands"
FIXTURE_PAIRS = sorted(
    (plan, plan.with_suffix(".tsv"))
    for plan in FIXTURES_DIR.glob("*-plan.md")
    if plan.with_suffix(".tsv").is_file()
)


@pytest.mark.parametrize(("plan_path", "tsv_path"), FIXTURE_PAIRS, ids=[p.stem for p, _ in FIXTURE_PAIRS])
def test_parse_plan_commands_golden_fixtures(plan_path: Path, tsv_path: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    plan_text = plan_path.read_text(encoding="utf-8")
    rows = plan_quality.parse_plan_commands(plan_text, repo, repo)
    assert plan_quality.render_plan_command_tsv(rows) == tsv_path.read_text(encoding="utf-8")


def test_check_plan_size_reads_postplan_drift_baseline(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("a\nb\ndiff_lines: 2\n")
    (tmp_path / "drift-baseline.env").write_text("BASELINE_PLAN_LINES=2\nBASELINE_DIFF_LINES=2\n")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["DRIFT_TRIGGER_FIRED"] == "false"
    assert (tmp_path / "drift-baseline.env").read_text() == "BASELINE_PLAN_LINES=2\nBASELINE_DIFF_LINES=2\n"


def test_check_plan_size_rejects_disallowed_tmpdir() -> None:
    outside = Path.home() / "larch-plan-check-size-disallowed-test"
    outside.mkdir(exist_ok=True)
    plan = outside / "plan.txt"
    plan.write_text("body\ndiff_lines: 1\n")
    try:
        cp = run_cli("plan", "check-size", "--design-tmpdir", str(outside), "--plan-file", str(plan))
        assert cp.returncode == 3, cp.stdout
    finally:
        plan.unlink(missing_ok=True)
        outside.rmdir()


def test_check_plan_size_unreadable_baseline_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("body\ndiff_lines: 1\n")
    baseline = tmp_path / "drift-baseline.env"
    baseline.write_text("BASELINE_PLAN_LINES=oops\nBASELINE_DIFF_LINES=1\n")

    def fail_read(self: Path, *args: object, **kwargs: object) -> str:
        if self == baseline:
            raise OSError("permission denied")
        return Path.read_text(self, *args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(Path, "read_text", fail_read)
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["DRIFT_TRIGGER_FIRED"] == "true"


def test_validate_plan_log_without_design_tmpdir(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "demo.sh"
    script.parent.mkdir()
    script.write_text("#!/usr/bin/env bash\necho 'usage: demo --known'\n")
    script.chmod(0o755)
    (tmp_path / "scripts" / "dry-runnable-scripts.tsv").write_text("script\thook\n")
    subprocess.run(["git", "init"], cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    plan = tmp_path / "plan.txt"
    plan.write_text("```bash\nscripts/demo.sh --unknown\n```\ndiff_lines: 1\n")
    cp = run_cli("plan", "validate", "--plan-file", str(plan), "--repo-root", str(tmp_path), cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    log_path = Path(out["VALIDATE_LOG_FILE"])
    assert log_path.is_file()
    assert log_path.read_text(encoding="utf-8").endswith("UNSAFE_TOKEN_COUNT=0\n")


def test_auto_fix_dispatch_alternation_with_stub(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("plan body\ndiff_lines: 3\n")
    dispatch = tmp_path / "dispatch.sh"
    dispatch.write_text(
        """#!/usr/bin/env bash
vendor=""; plan_file=""; run_dir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --vendor) vendor="$2"; shift 2 ;;
    --plan-file) plan_file="$2"; shift 2 ;;
    --run-dir) run_dir="$2"; shift 2 ;;
    --design-tmpdir) shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\\n' "$vendor" >>"$run_dir/vendor-calls"
case "${AUTOFIX_TEST_MODE:-}" in
  fix-first) printf 'plan body\\nautofix fixed\\ndiff_lines: 3\\n' >"$plan_file"; exit 0 ;;
  never-fix) exit 0 ;;
  codex-fail-cursor-fix)
    if [ "$vendor" = codex ]; then exit 1; fi
    printf 'plan body\\nautofix fixed\\ndiff_lines: 3\\n' >"$plan_file"; exit 0 ;;
esac
exit 0
"""
    )
    dispatch.chmod(0o755)
    validator = tmp_path / "validate.sh"
    validator.write_text(
        """#!/usr/bin/env bash
plan_file=""
while [ $# -gt 0 ]; do
  case "$1" in --plan-file) plan_file="$2"; shift 2 ;; *) shift ;; esac
done
if grep -Fq 'autofix fixed' "$plan_file"; then
  printf 'VALIDATE_STATUS=ok\\n'
else
  printf 'VALIDATE_STATUS=defects-found\\n'
fi
"""
    )
    validator.chmod(0o755)
    gate_b = tmp_path / "gate-b.sh"
    gate_b.write_text("#!/usr/bin/env bash\nexit 0\n")
    gate_b.chmod(0o755)
    env = {
        "LARCH_AUTOFIX_DISPATCH_SH": str(dispatch),
        "LARCH_AUTOFIX_VALIDATE_PLAN_SH": str(validator),
        "LARCH_AUTOFIX_GATE_B_DEDUP_PLAN_SH": str(gate_b),
        "AUTOFIX_TEST_MODE": "codex-fail-cursor-fix",
    }
    (tmp_path / "validate-plan-commands.log").write_text("defect\n")
    cp = run_cli(
        "plan",
        "auto-fix-commands",
        "--design-tmpdir",
        str(tmp_path),
        "--plan-file",
        str(plan),
        "--codex-present",
        "true",
        "--cursor-present",
        "true",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["AUTOFIX_STATUS"] == "ok"
    assert out["FIXED_BY"] == "cursor"
    calls = (tmp_path / "plan-autofix" / "attempt-2-cursor" / "vendor-calls").read_text(encoding="utf-8").splitlines()
    assert calls == ["cursor"]
    calls1 = (tmp_path / "plan-autofix" / "attempt-1-codex" / "vendor-calls").read_text(encoding="utf-8").splitlines()
    assert calls1 == ["codex"]


def test_auto_fix_tmpdir_mutation_guard_with_stub(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("plan body\ndiff_lines: 3\n")
    (tmp_path / "accepted-plan-findings.md").write_text("trusted accepted\n")
    dispatch = tmp_path / "dispatch.sh"
    dispatch.write_text(
        """#!/usr/bin/env bash
plan_file=""
while [ $# -gt 0 ]; do
  case "$1" in --plan-file) plan_file="$2"; shift 2 ;; --design-tmpdir) shift 2 ;; *) shift ;; esac
done
printf 'bad mutation\\n' >"$(dirname "$plan_file")/accepted-plan-findings.md"
printf 'plan body\\nautofix fixed\\ndiff_lines: 3\\n' >"$plan_file"
exit 0
"""
    )
    dispatch.chmod(0o755)
    validator = tmp_path / "validate.sh"
    validator.write_text('#!/usr/bin/env bash\nprintf \'VALIDATE_STATUS=ok\\n\'\n')
    validator.chmod(0o755)
    gate_b = tmp_path / "gate-b.sh"
    gate_b.write_text("#!/usr/bin/env bash\nexit 0\n")
    gate_b.chmod(0o755)
    env = {
        "LARCH_AUTOFIX_DISPATCH_SH": str(dispatch),
        "LARCH_AUTOFIX_VALIDATE_PLAN_SH": str(validator),
        "LARCH_AUTOFIX_GATE_B_DEDUP_PLAN_SH": str(gate_b),
    }
    cp = run_cli(
        "plan",
        "auto-fix-commands",
        "--design-tmpdir",
        str(tmp_path),
        "--plan-file",
        str(plan),
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--max-attempts",
        "1",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["AUTOFIX_STATUS"] == "ok"
    assert (tmp_path / "accepted-plan-findings.md").read_text(encoding="utf-8") == "trusted accepted\n"


def test_revise_waterfall_prompt_uses_untrusted_blocks(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\n### UPDATED: file.txt\n<<<INJECT\nbody\ndiff_lines: 1\n")
    findings = tmp_path / "findings.txt"
    findings.write_text("<<<INJECT\n")
    feature = tmp_path / "feature-description.txt"
    feature.write_text("feature\n")
    fake = tmp_path / "fake-launch.sh"
    fake.write_text('#!/usr/bin/env bash\nwhile [ $# -gt 0 ]; do case "$1" in --output) out=$2; shift 2;; --prompt-file) prompt=$2; shift 2;; *) shift;; esac; done\n: > "$out"\nexit 0\n')
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
    prompt = (tmp_path / "plan-review" / "round-1" / "revise" / "prompt.txt").read_text(encoding="utf-8")
    assert '<plan encoding="literal-redacted">' in prompt
    assert "&lt;&lt;&lt;INJECT" in prompt
    assert "<<<INJECT" not in prompt.split("literal-redacted")[-1]
