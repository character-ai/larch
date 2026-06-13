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
REPO_ROOT = Path(__file__).resolve().parents[1]


def run_cli(*args: str, cwd: Path | None = None, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run([sys.executable, str(CLI), *args], cwd=cwd, text=True, capture_output=True, env=merged, check=False)


def _write_executable(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)
    return path


def _revise_base(tmp_path: Path, plan_text: str | None = None) -> tuple[Path, Path, Path]:
    plan = tmp_path / "plan.txt"
    plan.write_text(plan_text or "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n", encoding="utf-8")
    findings = tmp_path / "findings.txt"
    findings.write_text("finding\n", encoding="utf-8")
    feature = tmp_path / "feature-description.txt"
    feature.write_text("feature\n", encoding="utf-8")
    return plan, findings, feature


def _run_revise(tmp_path: Path, plan: Path, findings: Path, feature: Path, env: dict[str, str], *extra: str) -> subprocess.CompletedProcess[str]:
    return run_cli(
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
        "true",
        "--cursor-present",
        "false",
        *extra,
        env=env,
    )


def _validate_text(plan_text: str, tmp_path: Path, registry: Path | None = None, source_kind: str = "plan") -> plan_quality.ValidationSummary:
    plan = tmp_path / "case-plan.md"
    plan.write_text(plan_text, encoding="utf-8")
    rows = plan_quality.parse_plan_commands(plan.read_text(encoding="utf-8"), REPO_ROOT, REPO_ROOT)
    return plan_quality.validate_plan_command_rows(rows, REPO_ROOT, registry, source_kind, help_timeout=5, dry_run_timeout=5)


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


_TRAILER_AWK_PARSE_CASES = [
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", 3, "100", "50", "true"),
    ("none-present", "body\ndiff_lines: 1\n", 0, None, None, "false"),
    ("octal-rejected", "body\ndiff_added: 08\ndiff_deleted: 09\ndiff_lines: 10\n", 0, None, None, "false"),
    ("block-boundary", "body\ndiff_added: 99\nnot a trailer\ndiff_added: 5\ndiff_lines: 10\n", 1, "5", None, "false"),
    ("blank-before-diff-lines", "body\ndiff_added: 99\n\ndiff_lines: 10\n", 0, None, None, "false"),
    ("octal-then-valid", "body\ndiff_added: 08\ndiff_added: 5\ndiff_lines: 10\n", 1, "5", None, "false"),
    ("mech-true", "body\ndiff_added: 1\nmechanical_churn: true\ndiff_lines: 10\n", 2, "1", None, "true"),
    ("mech-false", "body\ndiff_added: 1\nmechanical_churn: false\ndiff_lines: 10\n", 2, "1", None, "false"),
    ("retain-010", "body\ndiff_added: 010\ndiff_deleted: 010\ndiff_lines: 10\n", 2, "010", "010", "false"),
    ("duplicate-diff-added", "body\ndiff_added: 1\ndiff_added: 2\ndiff_lines: 10\n", 2, "2", None, "false"),
]

_TRAILER_AWK_KEYS_CASES = [
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", ("diff_added", "diff_deleted", "mechanical_churn")),
    ("none-present", "body\ndiff_lines: 1\n", ()),
    ("octal-rejected", "body\ndiff_added: 08\ndiff_deleted: 09\ndiff_lines: 10\n", ()),
    ("octal-then-valid", "body\ndiff_added: 08\ndiff_added: 5\ndiff_lines: 10\n", ("diff_added",)),
    ("blank-before-diff-lines", "body\ndiff_added: 99\n\ndiff_lines: 10\n", ()),
    ("mech-true", "body\ndiff_added: 1\nmechanical_churn: true\ndiff_lines: 10\n", ("diff_added", "mechanical_churn")),
    ("mech-false", "body\ndiff_added: 1\nmechanical_churn: false\ndiff_lines: 10\n", ("diff_added", "mechanical_churn")),
    ("retain-010", "body\ndiff_added: 010\ndiff_deleted: 010\ndiff_lines: 10\n", ("diff_added", "diff_deleted")),
    ("duplicate-diff-added", "body\ndiff_added: 1\ndiff_added: 2\ndiff_lines: 10\n", ("diff_added",)),
    ("block-boundary", "body\ndiff_added: 99\nnot a trailer\ndiff_added: 5\ndiff_lines: 10\n", ("diff_added",)),
]

_TRAILER_AWK_VALUES_CASES = [
    ("block-boundary", "body\ndiff_added: 99\nnot a trailer\ndiff_added: 5\ndiff_lines: 10\n", ("diff_added=5",)),
    ("none-present", "body\ndiff_lines: 1\n", ()),
    ("octal-rejected", "body\ndiff_added: 08\ndiff_deleted: 09\ndiff_lines: 10\n", ()),
    ("octal-then-valid", "body\ndiff_added: 08\ndiff_added: 5\ndiff_lines: 10\n", ("diff_added=5",)),
    ("blank-before-diff-lines", "body\ndiff_added: 99\n\ndiff_lines: 10\n", ()),
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", ("diff_added=100", "diff_deleted=50", "mechanical_churn=true")),
    ("duplicate-diff-added", "body\ndiff_added: 1\ndiff_added: 2\ndiff_lines: 10\n", ("diff_added=2",)),
    ("mech-true", "body\ndiff_added: 1\nmechanical_churn: true\ndiff_lines: 10\n", ("diff_added=1", "mechanical_churn=true")),
    ("mech-false", "body\ndiff_added: 1\nmechanical_churn: false\ndiff_lines: 10\n", ("diff_added=1", "mechanical_churn=false")),
    ("retain-010", "body\ndiff_added: 010\ndiff_deleted: 010\ndiff_lines: 10\n", ("diff_added=010", "diff_deleted=010")),
]

_TRAILER_AWK_HAS_KEY_CASES = [
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", "diff_added", 0),
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", "diff_deleted", 0),
    ("all-three-present", "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n", "mechanical_churn", 0),
    ("none-present", "body\ndiff_lines: 1\n", "diff_added", 1),
    ("none-present", "body\ndiff_lines: 1\n", "diff_deleted", 1),
    ("none-present", "body\ndiff_lines: 1\n", "mechanical_churn", 1),
    ("octal-rejected", "body\ndiff_added: 08\ndiff_deleted: 09\ndiff_lines: 10\n", "diff_added", 1),
    ("octal-rejected", "body\ndiff_added: 08\ndiff_deleted: 09\ndiff_lines: 10\n", "diff_deleted", 1),
    ("block-boundary", "body\ndiff_added: 99\nnot a trailer\ndiff_added: 5\ndiff_lines: 10\n", "diff_added", 0),
    ("blank-before-diff-lines", "body\ndiff_added: 99\n\ndiff_lines: 10\n", "diff_added", 1),
    ("octal-then-valid", "body\ndiff_added: 08\ndiff_added: 5\ndiff_lines: 10\n", "diff_added", 0),
    ("boundary-orphan-only", "body\ndiff_added: 99\nnot a trailer\ndiff_lines: 10\n", "diff_added", 1),
    ("mech-true", "body\ndiff_added: 1\nmechanical_churn: true\ndiff_lines: 10\n", "mechanical_churn", 0),
    ("mech-false", "body\ndiff_added: 1\nmechanical_churn: false\ndiff_lines: 10\n", "mechanical_churn", 0),
    ("retain-010", "body\ndiff_added: 010\ndiff_deleted: 010\ndiff_lines: 10\n", "diff_added", 0),
    ("retain-010", "body\ndiff_added: 010\ndiff_deleted: 010\ndiff_lines: 10\n", "diff_deleted", 0),
]


@pytest.mark.parametrize(("name", "plan_text", "count", "added", "deleted", "mech"), _TRAILER_AWK_PARSE_CASES)
def test_optional_trailer_awk_parse_parity(name: str, plan_text: str, count: int, added: str | None, deleted: str | None, mech: str) -> None:
    meta = plan_quality.parse_optional_metadata(plan_text)
    assert meta.metadata_trailer_lines == count
    assert meta.diff_added == added
    assert meta.diff_deleted == deleted
    assert meta.mechanical_churn == mech


@pytest.mark.parametrize(("name", "plan_text", "keys"), _TRAILER_AWK_KEYS_CASES)
def test_optional_trailer_awk_keys_parity(name: str, plan_text: str, keys: tuple[str, ...]) -> None:
    assert plan_quality.parse_optional_metadata(plan_text).keys == keys


@pytest.mark.parametrize(("name", "plan_text", "values"), _TRAILER_AWK_VALUES_CASES)
def test_optional_trailer_awk_values_parity(name: str, plan_text: str, values: tuple[str, ...]) -> None:
    assert plan_quality.parse_optional_metadata(plan_text).values == values


@pytest.mark.parametrize(("name", "plan_text", "key", "want_rc"), _TRAILER_AWK_HAS_KEY_CASES)
def test_optional_trailer_awk_has_key_parity(tmp_path: Path, name: str, plan_text: str, key: str, want_rc: int) -> None:
    plan = tmp_path / f"{name}.txt"
    plan.write_text(plan_text, encoding="utf-8")
    cp = run_cli("plan", "optional-trailers", "has-key", "--plan-file", str(plan), "--key", key)
    assert cp.returncode == want_rc


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


def test_revise_waterfall_restores_when_emit_plan_gate_fails(tmp_path: Path) -> None:
    original = "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;;
  esac
done
cat >"$out" <<'PLAN'
## Plan
### UPDATED: file.txt
changed
diff_lines: 2
PLAN
""",
    )
    driver = _write_executable(tmp_path / "driver.sh", "#!/usr/bin/env bash\nprintf 'EMIT_PLAN_STATUS=failed\\n'\nexit 0\n")
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
    }
    cp = _run_revise(tmp_path, plan, findings, feature, env, "--patch-format", "file-replacement")
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_TIER_1_STATUS"] == "emit-plan-failed"
    assert out["REVISE_STATUS"] == "failed-apply"
    assert plan.read_text(encoding="utf-8") == original


def test_revise_waterfall_restores_after_unified_patch_apply_failure(tmp_path: Path) -> None:
    original = "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
out=""; prompt=""
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; --prompt-file) prompt="$2"; shift 2 ;; *) shift ;;
  esac
done
if grep -Fq 'complete replacement plan' "$prompt"; then
  : >"$out"
else
  cat >"$out" <<'PATCH'
--- a/plan.txt
+++ b/plan.txt
@@ -99,1 +99,1 @@
-missing
+changed
PATCH
fi
""",
    )
    driver = _write_executable(tmp_path / "driver.sh", "#!/usr/bin/env bash\nprintf 'EMIT_PLAN_STATUS=ok\\n'\n")
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
    }
    cp = _run_revise(tmp_path, plan, findings, feature, env)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_TIER_1_STATUS"] == "apply-failed"
    assert out["REVISE_STATUS"] == "failed-apply"
    assert plan.read_text(encoding="utf-8") == original


def test_revise_waterfall_falls_back_to_file_replacement_in_tier_order(tmp_path: Path) -> None:
    plan, findings, feature = _revise_base(tmp_path)
    calls = tmp_path / "calls.txt"
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        f"""#!/usr/bin/env bash
out=""; prompt=""
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; --prompt-file) prompt="$2"; shift 2 ;; *) shift ;;
  esac
done
printf '%s\\n' "$(basename "$out")" >>"{calls}"
if grep -Fq 'complete replacement plan' "$prompt"; then
  cat >"$out" <<'PLAN'
## Plan
### UPDATED: file.txt
fallback fixed
diff_lines: 2
PLAN
else
  printf 'not a diff\\n' >"$out"
fi
""",
    )
    driver = _write_executable(tmp_path / "driver.sh", "#!/usr/bin/env bash\nprintf 'EMIT_PLAN_STATUS=ok\\n'\n")
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
    }
    cp = _run_revise(tmp_path, plan, findings, feature, env)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "ok-fallback"
    assert out["REVISE_TIER_4_STATUS"] == "ok"
    assert calls.read_text(encoding="utf-8").splitlines() == ["codex-output.txt", "claude-output.txt", "codex-output.txt"]
    assert "fallback fixed" in plan.read_text(encoding="utf-8")


def test_revise_waterfall_heading_guard_restores_replacement(tmp_path: Path) -> None:
    original = "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in --output) out="$2"; shift 2 ;; *) shift ;;
  esac
done
cat >"$out" <<'PLAN'
## Plan
body without plan headings
diff_lines: 1
PLAN
""",
    )
    driver = _write_executable(tmp_path / "driver.sh", "#!/usr/bin/env bash\nprintf 'EMIT_PLAN_STATUS=ok\\n'\n")
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
    }
    cp = _run_revise(tmp_path, plan, findings, feature, env, "--patch-format", "file-replacement")
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_TIER_1_STATUS"] == "invalid-patch"
    assert out["REVISE_STATUS"] == "failed-validation"
    assert plan.read_text(encoding="utf-8") == original


FIXTURES_DIR = Path(__file__).resolve().parents[1] / "skills" / "design" / "scripts" / "fixtures" / "parse-plan-commands"
def _parse_plan_fixture_tsv(plan_path: Path) -> Path:
    return plan_path.with_name(plan_path.stem.removesuffix("-plan") + ".tsv")


FIXTURE_PAIRS = sorted(
    (plan, _parse_plan_fixture_tsv(plan))
    for plan in FIXTURES_DIR.glob("*-plan.md")
    if _parse_plan_fixture_tsv(plan).is_file()
)


def test_parse_plan_commands_fixture_pairs_count() -> None:
    assert len(FIXTURE_PAIRS) == 13


@pytest.mark.parametrize(("plan_path", "tsv_path"), FIXTURE_PAIRS, ids=[p.stem for p, _ in FIXTURE_PAIRS])
def test_parse_plan_commands_golden_fixtures(plan_path: Path, tsv_path: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    plan_text = plan_path.read_text(encoding="utf-8")
    rows = plan_quality.parse_plan_commands(plan_text, repo, repo)
    assert plan_quality.render_plan_command_tsv(rows) == tsv_path.read_text(encoding="utf-8")


def test_validate_plan_commands_fixture_parity(tmp_path: Path) -> None:
    fixture_dir = REPO_ROOT / "skills" / "design" / "scripts" / "fixtures" / "validate-plan-commands"
    demo = (fixture_dir / "demo-plan.md").read_text(encoding="utf-8")
    summary = _validate_text(demo, tmp_path)
    assert "DEFECT script=skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh kind=unknown-flag flag=unknown-flag" in summary.log_text
    assert summary.status == "defects-found"
    assert summary.defect_count == 1

    missing = """## Plan

```bash
scripts/does-not-exist-zzzz-validate-fixture.sh
```

diff_lines: 1
"""
    summary = _validate_text(missing, tmp_path)
    assert "DEFECT script=scripts/does-not-exist-zzzz-validate-fixture.sh kind=missing-script" in summary.log_text

    dots = """## Plan

```bash
scripts/../python/cli.py redact secrets
```

diff_lines: 1
"""
    rows = plan_quality.parse_plan_commands(dots, REPO_ROOT, REPO_ROOT)
    assert any(row.row_type == "parse_note" for row in rows)
    summary = plan_quality.validate_plan_command_rows(rows, REPO_ROOT)
    assert summary.status == "ok"

    allow_plan = """## Plan

### Files to update

- **UPDATED**: skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh
  - Adds flag: known-flag

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh --known-flag x
```

diff_lines: 1
"""
    summary = _validate_text(allow_plan, tmp_path)
    assert "kind=unknown-flag flag=known-flag" not in summary.log_text
    assert summary.status == "ok"

    launch_context = (fixture_dir / "launch-context-plan.md").read_text(encoding="utf-8")
    summary = _validate_text(launch_context, tmp_path)
    assert "flag=context-files" not in summary.log_text
    assert summary.status == "ok"

    dotslash = """## Plan

```bash
./python/cli.py redact secrets
```

diff_lines: 1
"""
    assert _validate_text(dotslash, tmp_path).status == "ok"

    registry = tmp_path / "dry-registry.tsv"
    registry.write_text(
        "script_path\thook\tdoc_anchor\n"
        "skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh\tLARCH_DRY_RUN=1\t\n"
        "skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-fail.sh\tLARCH_DRY_RUN=1\t\n",
        encoding="utf-8",
    )
    tier3_ok = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh --dry-flag x
```

diff_lines: 1
"""
    summary = _validate_text(tier3_ok, tmp_path, registry)
    assert summary.status == "ok"
    assert "kind=dry-run-failed" not in summary.log_text

    tier3_fail = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-fail.sh --dry-flag x
```

diff_lines: 1
"""
    summary = _validate_text(tier3_fail, tmp_path, registry)
    assert "kind=dry-run-failed" in summary.log_text

    unsafe = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh --dry-flag 'x;y'
```

diff_lines: 1
"""
    summary = _validate_text(unsafe, tmp_path, registry)
    assert "kind=unsafe-token" in summary.log_text
    assert summary.unsafe_token_count == 1

    summary = _validate_text(tier3_fail, tmp_path, registry, source_kind="composed")
    assert "kind=dry-run-failed" not in summary.log_text

    bad_registry = tmp_path / "bad-registry.tsv"
    bad_registry.write_text(
        "script_path\thook\tdoc_anchor\n"
        "skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-dry.sh\tmy-mode\t\n",
        encoding="utf-8",
    )
    summary = _validate_text(tier3_ok, tmp_path, bad_registry)
    assert "kind=unknown-registry-hook hook=my-mode" in summary.log_text

    validate_only_registry = tmp_path / "validate-only-registry.tsv"
    validate_only_registry.write_text(
        "script_path\thook\tdoc_anchor\n"
        "skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-validate-only.sh\t--validate-only\t\n",
        encoding="utf-8",
    )
    validate_only = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-validate-only.sh --dry-flag x
```

diff_lines: 1
"""
    summary = _validate_text(validate_only, tmp_path, validate_only_registry)
    assert summary.status == "ok"
    assert "TIER3_CAPTURE script=skills/design/scripts/fixtures/validate-plan-commands/demo-tier3-validate-only.sh" in summary.log_text

    empty_help = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-empty-help.sh --should-be-ignored x
```

diff_lines: 1
"""
    summary = _validate_text(empty_help, tmp_path)
    assert "SKIPPED_FLAG_CHECK script=skills/design/scripts/fixtures/validate-plan-commands/demo-empty-help.sh" in summary.log_text
    assert summary.skipped_count == 1

    nonzero_help = """## Plan

```bash
skills/design/scripts/fixtures/validate-plan-commands/demo-help-nonzero-rc.sh --bogus-flag
```

diff_lines: 1
"""
    summary = _validate_text(nonzero_help, tmp_path)
    assert "kind=unknown-flag flag=bogus-flag" in summary.log_text

    dot_newskip = (REPO_ROOT / "skills" / "design" / "scripts" / "fixtures" / "parse-plan-commands" / "dot-newskip-plan.md").read_text(encoding="utf-8")
    summary = _validate_text(dot_newskip, tmp_path)
    assert "SKIPPED script=skills/design/scripts/fixtures/tmp-new2.sh reason=new-script" in summary.log_text
    assert summary.status == "ok"


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
    outside = REPO_ROOT / ".pytest-larch-plan-check-size-disallowed-test"
    outside.mkdir(exist_ok=True)
    plan = outside / "plan.txt"
    plan.write_text("body\ndiff_lines: 1\n")
    try:
        cp = run_cli("plan", "check-size", "--design-tmpdir", str(outside), "--plan-file", str(plan))
        assert cp.returncode == 3, cp.stdout
    finally:
        plan.unlink(missing_ok=True)
        outside.rmdir()


def test_revise_waterfall_rejects_disallowed_design_tmpdir(tmp_path: Path) -> None:
    plan, findings, feature = _revise_base(tmp_path)
    disallowed = Path.home() / "larch-revise-disallowed-test"
    cp = run_cli(
        "plan",
        "revise-waterfall",
        "--design-tmpdir",
        str(disallowed),
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
    )
    assert cp.returncode == 2
    assert "path not under allowlist" in cp.stderr


def test_auto_fix_rejects_disallowed_design_tmpdir(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndiff_lines: 1\n")
    disallowed = Path.home() / "larch-autofix-disallowed-test"
    cp = run_cli(
        "plan",
        "auto-fix-commands",
        "--design-tmpdir",
        str(disallowed),
        "--plan-file",
        str(plan),
        "--codex-present",
        "false",
        "--cursor-present",
        "false",
    )
    assert cp.returncode == 2
    assert "path not under allowlist" in cp.stderr


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


def test_validate_plan_uses_temp_log_for_disallowed_design_tmpdir(tmp_path: Path) -> None:
    script = tmp_path / "scripts" / "demo.sh"
    script.parent.mkdir()
    script.write_text("#!/usr/bin/env bash\necho 'usage: demo --known'\n")
    script.chmod(0o755)
    (tmp_path / "scripts" / "dry-runnable-scripts.tsv").write_text("script\thook\n")
    subprocess.run(["git", "init"], cwd=tmp_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    plan = tmp_path / "plan.txt"
    plan.write_text("```bash\nscripts/demo.sh --unknown\n```\ndiff_lines: 1\n")
    disallowed = Path.home() / "larch-plan-validate-disallowed-test"
    cp = run_cli("plan", "validate", "--plan-file", str(plan), "--repo-root", str(tmp_path), "--design-tmpdir", str(disallowed), cwd=tmp_path)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    log_path = Path(out["VALIDATE_LOG_FILE"])
    assert log_path.is_file()
    assert log_path != disallowed / "validate-plan-commands.log"


def test_validate_plan_defaults_to_plugin_root_for_session_tmpdir_plan(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("```bash\nskills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh --unknown-flag\n```\ndiff_lines: 1\n")
    cp = run_cli("plan", "validate", "--plan-file", str(plan), "--design-tmpdir", str(tmp_path), cwd=Path("/"))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["VALIDATE_STATUS"] == "defects-found"
    assert out["VALIDATE_DEFECT_COUNT"] == "1"


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


def test_auto_fix_revalidation_uses_consumer_repo_root(tmp_path: Path) -> None:
    consumer = tmp_path / "consumer"
    consumer.mkdir()
    subprocess.run(["git", "init"], cwd=consumer, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    script = consumer / "scripts" / "local-fixture.sh"
    script.parent.mkdir()
    script.write_text("#!/usr/bin/env bash\necho 'usage: local-fixture --ok'\n")
    script.chmod(0o755)
    design_tmp = tmp_path / "design"
    design_tmp.mkdir()
    plan = design_tmp / "plan.txt"
    plan.write_text("```bash\nscripts/local-fixture.sh --bad-flag\n```\ndiff_lines: 1\n")
    repo_root_log = tmp_path / "repo-root.log"
    dispatch = tmp_path / "dispatch.sh"
    dispatch.write_text(
        """#!/usr/bin/env bash
plan_file=""
while [ $# -gt 0 ]; do
  case "$1" in
    --plan-file) plan_file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf 'fixed plan\\ndiff_lines: 2\\n' >"$plan_file"
exit 0
"""
    )
    dispatch.chmod(0o755)
    validator = tmp_path / "validate.sh"
    validator.write_text(
        f"""#!/usr/bin/env bash
repo_root=""
plan_file=""
while [ $# -gt 0 ]; do
  case "$1" in
    --repo-root) repo_root="$2"; shift 2 ;;
    --plan-file) plan_file="$2"; shift 2 ;;
    *) shift ;;
  esac
done
printf '%s\\n' "$repo_root" >>"{repo_root_log}"
if [ -f "$repo_root/scripts/local-fixture.sh" ] && grep -Fq 'fixed plan' "$plan_file"; then
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
    }
    (design_tmp / "validate-plan-commands.log").write_text("defect\n")
    cp = run_cli(
        "plan",
        "auto-fix-commands",
        "--design-tmpdir",
        str(design_tmp),
        "--plan-file",
        str(plan),
        "--repo-root",
        str(consumer.resolve()),
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        cwd=consumer,
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["AUTOFIX_STATUS"] == "ok"
    logged_roots = repo_root_log.read_text(encoding="utf-8").strip().splitlines()
    assert logged_roots
    assert all(Path(line).resolve() == consumer.resolve() for line in logged_roots)


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
    validator.write_text("""#!/usr/bin/env bash
printf 'VALIDATE_STATUS=ok\\n'
""")
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


def test_allow_flag_accepts_dot_slash_prefixed_script(tmp_path: Path) -> None:
    script = REPO_ROOT / "skills" / "design" / "scripts" / "fixtures" / "validate-plan-commands" / "demo-stdout-help.sh"
    plan = f"""### UPDATED: {script.relative_to(REPO_ROOT)}
- Adds flag: `--known-flag`
```bash
./{script.relative_to(REPO_ROOT)} --known-flag
```
diff_lines: 1
"""
    summary = _validate_text(plan, tmp_path)
    assert "kind=unknown-flag flag=known-flag" not in summary.log_text


def test_check_plan_size_missing_plan_returns_rc2(tmp_path: Path) -> None:
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 2, cp.stdout
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["PLAN_SIZE_STATUS"] == "missing-plan"


def test_check_plan_size_missing_diff_lines_returns_rc2(tmp_path: Path) -> None:
    (tmp_path / "plan.txt").write_text("body only\n", encoding="utf-8")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 2, cp.stdout
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["PLAN_SIZE_STATUS"] == "missing-diff-lines"


def test_check_plan_size_invalid_mechanical_churn_returns_rc2(tmp_path: Path) -> None:
    (tmp_path / "plan.txt").write_text("body\nmechanical_churn: 35\ndiff_lines: 10\n", encoding="utf-8")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 2, cp.stdout
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["PLAN_SIZE_STATUS"] == "invalid-mechanical-churn"


def test_check_plan_size_hard_trigger_fires(tmp_path: Path) -> None:
    body = "\n".join(["line"] * 801)
    (tmp_path / "plan.txt").write_text(f"{body}\ndiff_lines: 801\n", encoding="utf-8")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["SIZE_TRIGGER_FIRED"] == "true"
    assert "plan-body-lines" in out["TRIGGER_REASONS"]


def test_validate_plan_missing_plan_file_returns_rc2(tmp_path: Path) -> None:
    missing = tmp_path / "missing-plan.txt"
    cp = run_cli("plan", "validate", "--plan-file", str(missing), "--repo-root", str(REPO_ROOT))
    assert cp.returncode == 2
    assert "unreadable plan file" in cp.stderr


def test_validate_commands_missing_tsv_returns_rc2(tmp_path: Path) -> None:
    missing = tmp_path / "missing.tsv"
    log = tmp_path / "validate.log"
    cp = run_cli(
        "plan",
        "validate-commands",
        "--tsv-file",
        str(missing),
        "--log-file",
        str(log),
        "--repo-root",
        str(REPO_ROOT),
    )
    assert cp.returncode == 2
    assert "unreadable TSV" in cp.stderr


def test_validate_commands_defaults_plugin_root_without_repo_root(tmp_path: Path) -> None:
    tsv = tmp_path / "commands.tsv"
    tsv.write_text(
        "row_type\tsource_line\tscript_path\tflag\tflag_value\tnote\tcmd_uid\n"
        "invocation\t2\tskills/design/scripts/fixtures/validate-plan-commands/demo-stdout-help.sh\tunknown-flag\t\t\tcmd1\n",
        encoding="utf-8",
    )
    log = tmp_path / "validate.log"
    cp = run_cli("plan", "validate-commands", "--tsv-file", str(tsv), "--log-file", str(log), cwd=Path("/"))
    assert cp.returncode == 0, cp.stderr
    assert "VALIDATE_STATUS=defects-found" in cp.stdout
    assert log.read_text(encoding="utf-8").endswith("UNSAFE_TOKEN_COUNT=0\n")


def test_revise_waterfall_restores_plan_after_failed_round(tmp_path: Path) -> None:
    original = "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
while [ $# -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --plan-file) plan="$2"; shift 2 ;;
    *) shift ;;
  esac
done
cat >"$plan" <<'PLAN'
## Plan
### UPDATED: file.txt
corrupted
diff_lines: 9
PLAN
: >"$out"
exit 0
""",
    )
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
    }
    cp = _run_revise(tmp_path, plan, findings, feature, env)
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"].startswith("failed")
    assert plan.read_text(encoding="utf-8") == original


def test_redact_capture_withholds_raw_text_on_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    secret = "SECRET_TOKEN=super-secret-value\n"

    def fail_redact(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=(), returncode=1, stdout="", stderr="")

    monkeypatch.setattr(plan_quality.subprocess, "run", fail_redact)
    redacted = plan_quality._redact_capture(REPO_ROOT, secret)
    assert secret not in redacted
    assert "withheld" in redacted


def test_git_status_snapshot_detects_untracked_content_change(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    untracked = tmp_path / "scratch.txt"
    untracked.write_text("before\n", encoding="utf-8")
    before = plan_quality._git_status_snapshot(tmp_path)
    untracked.write_text("after\n", encoding="utf-8")
    after = plan_quality._git_status_snapshot(tmp_path)
    assert before != after
