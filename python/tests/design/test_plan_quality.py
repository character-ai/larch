# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportOperatorIssue=false, reportArgumentType=false, reportPrivateUsage=false
from __future__ import annotations
# ruff: noqa: UP022

import os
import subprocess
import sys
from pathlib import Path

import pytest

from larch.design import design_pause
from larch.core import logging_util
from larch.design import plan_quality
from larch.core import config

CLI = Path(__file__).resolve().parents[2] / "cli.py"
REPO_ROOT = Path(__file__).resolve().parents[3]


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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "false",
        *extra,
        env=env,
    )


def _validate_text(plan_text: str, tmp_path: Path, registry: Path | None = None, source_kind: str = "plan") -> plan_quality.ValidationSummary:
    plan = tmp_path / "case-plan.md"
    plan.write_text(plan_text, encoding="utf-8")
    rows = plan_quality.parse_plan_commands(plan_text=plan.read_text(encoding="utf-8"), repo_root=REPO_ROOT, plugin_root=REPO_ROOT)
    return plan_quality.validate_plan_command_rows(rows=rows, repo_root=REPO_ROOT, registry=registry, source_kind=source_kind, help_timeout=5, dry_run_timeout=5)


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
    rows = plan_quality.parse_plan_commands(plan_text=plan, repo_root=repo, plugin_root=repo)
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
    notes = [row.note for row in plan_quality.parse_plan_commands(plan_text=plan, repo_root=tmp_path, plugin_root=tmp_path) if row.row_type == "parse_note"]
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


def test_optional_trailer_validate_rejects_lost_keys(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("body\ndiff_added: 1\ndiff_lines: 2\n", encoding="utf-8")
    keys = tmp_path / "keys"
    assert run_cli("plan", "optional-trailers", "snapshot-keys", "--plan-file", str(plan), "--output", str(keys)).returncode == 0

    plan.write_text("body\ndiff_lines: 2\n", encoding="utf-8")

    assert not plan_quality.validate_optional_trailers_preserved(plan_file=plan, values_file=keys)
    assert run_cli("plan", "optional-trailers", "validate-values", "--plan-file", str(plan), "--values-file", str(keys)).returncode == 1


def test_optional_trailer_has_any_equivalent() -> None:
    assert bool(plan_quality.parse_optional_metadata("body\ndiff_added: 1\ndiff_lines: 2\n").keys)
    assert not plan_quality.parse_optional_metadata("body\ndiff_lines: 2\n").keys


def test_validate_difficulty_metadata_ignores_body_tokens() -> None:
    plan = (
        "body\n"
        "difficulty: NOT-A-TRAILER\n"
        "\n"
        "review_status: complete\n"
        "rounds_completed: 2\n"
        "difficulty: HARD\n"
        "diff_lines: 9\n"
    )

    ok, found = plan_quality.validate_difficulty_metadata(plan, require=True)

    assert ok is True
    assert found == "HARD"


def test_validate_plan_require_difficulty_stays_trailing_only(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndifficulty: MODERATE\n\n## Acceptance\nok\n\ndiff_lines: 9\n", encoding="utf-8")

    cp = run_cli(
        "plan",
        "validate",
        "--plan-file",
        str(plan),
        "--repo-root",
        str(REPO_ROOT),
        "--design-tmpdir",
        str(tmp_path),
        env={"LARCH_REQUIRE_PLAN_DIFFICULTY": "1"},
    )
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)

    assert cp.returncode == 0, cp.stderr
    assert out["VALIDATE_STATUS"] == "defects-found"
    assert out["VALIDATE_DEFECT_COUNT"] == "1"
    assert "DEFECT plan kind=difficulty-metadata" in (tmp_path / "validate-plan-commands.log").read_text(encoding="utf-8")


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


@pytest.mark.parametrize(("_name", "plan_text", "count", "added", "deleted", "mech"), _TRAILER_AWK_PARSE_CASES)
def test_optional_trailer_awk_parse_parity(_name: str, plan_text: str, count: int, added: str | None, deleted: str | None, mech: str) -> None:
    meta = plan_quality.parse_optional_metadata(plan_text)
    assert meta.metadata_trailer_lines == count
    assert meta.diff_added == added
    assert meta.diff_deleted == deleted
    assert meta.mechanical_churn == mech


@pytest.mark.parametrize(("_name", "plan_text", "keys"), _TRAILER_AWK_KEYS_CASES)
def test_optional_trailer_awk_keys_parity(_name: str, plan_text: str, keys: tuple[str, ...]) -> None:
    assert plan_quality.parse_optional_metadata(plan_text).keys == keys


@pytest.mark.parametrize(("_name", "plan_text", "values"), _TRAILER_AWK_VALUES_CASES)
def test_optional_trailer_awk_values_parity(_name: str, plan_text: str, values: tuple[str, ...]) -> None:
    assert plan_quality.parse_optional_metadata(plan_text).values == values


@pytest.mark.parametrize(("name", "plan_text", "key", "want_rc"), _TRAILER_AWK_HAS_KEY_CASES)
def test_optional_trailer_awk_has_key_parity(tmp_path: Path, name: str, plan_text: str, key: str, want_rc: int) -> None:
    plan = tmp_path / f"{name}.txt"
    plan.write_text(plan_text, encoding="utf-8")
    cp = run_cli("plan", "optional-trailers", "has-key", "--plan-file", str(plan), "--key", key)
    assert cp.returncode == want_rc


def test_optional_metadata_preserves_oversize_override_trailer() -> None:
    plan_text = (
        "body\n"
        "diff_added: 100\n"
        "mechanical_churn: false\n"
        "oversize_override: operator\n"
        "diff_lines: 200\n"
    )
    meta = plan_quality.parse_optional_metadata(plan_text)

    assert meta.oversize_override == "operator"
    assert meta.metadata_trailer_lines == 3
    assert "oversize_override" in meta.keys
    assert "oversize_override=operator" in meta.values


def test_optional_metadata_malformed_oversize_override_stops_block() -> None:
    plan_text = "body\ndiff_added: 100\noversize_override: maybe\ndiff_lines: 200\n"

    meta = plan_quality.parse_optional_metadata(plan_text)

    assert meta.oversize_override is None
    assert meta.metadata_trailer_lines == 0


def test_check_plan_size_log_contract_and_mechanical_churn_stays_hard(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("line\n" * 4 + "diff_added: 2500\nmechanical_churn: true\ndiff_lines: 2500\n")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["SIZE_TRIGGER_FIRED"] == "true"
    assert out["SOFT_ADVISORY"] == "true"
    assert out["DIFF_ADDED"] == "2500"
    assert "diff-added" in out["TRIGGER_REASONS"]
    assert "diff-lines" in out["TRIGGER_REASONS"]
    assert (tmp_path / "drift-baseline.env").is_file()


def test_check_plan_size_6524_meta_trips_oversize(tmp_path: Path) -> None:
    headings = "\n".join(
        f"### UPDATED: python/larch/design/file{i}.py"
        for i in range(74)
    )
    plan = tmp_path / "plan.txt"
    plan.write_text(
        f"## Plan\n\n## Files to modify/create\n\n{headings}\n"
        "diff_added: 1980\n"
        "diff_deleted: 1350\n"
        "mechanical_churn: true\n"
        "diff_lines: 3330\n",
        encoding="utf-8",
    )

    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)

    assert out["SIZE_TRIGGER_FIRED"] == "true"
    assert out["SOFT_ADVISORY"] == "true"
    assert out["DIFF_ADDED"] == "1980"
    assert out["DIFF_DELETED"] == "1350"
    assert out["DIFF_LINES"] == "3330"
    assert out["MECHANICAL_CHURN"] == "true"
    assert out["FIRM_HEADINGS"] == "74"
    assert out["TRIGGER_REASONS"]
    assert "diff-lines" in out["TRIGGER_REASONS"]


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
        "--codex-binary-found",
        "false",
        "--cursor-binary-found",
        "false",
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["AUTOFIX_STATUS"] == "unavailable"
    assert out["ATTEMPTS"] == "0"


def test_validator_autofix_calls_helper_in_process(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndiff_lines: 1\n", encoding="utf-8")
    calls: list[list[str]] = []

    def fake_auto_fix(argv: list[str]) -> int:
        calls.append(argv)
        print("AUTOFIX_STATUS=ok")
        print("FIXED_BY=codex")
        print(f"ORIGINAL_VALIDATE_LOG_FILE={tmp_path / 'validate-plan-commands.log'}")
        return 0

    monkeypatch.setattr(plan_quality, "auto_fix_plan_commands_main", fake_auto_fix)
    monkeypatch.setattr(plan_quality, "_validator_require_plugin_root", lambda: 1)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    rc = plan_quality.validator_autofix_main(["--site", "design Step 2b", "--validator-target-file", str(plan)])
    out = capsys.readouterr().out
    assert rc == 0
    assert calls
    assert "--plan-file" in calls[0]
    assert "AUTOFIX_STATUS=ok" in out
    assert "FIXED_BY=codex" in out


def test_validator_autofix_cycle_cap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndiff_lines: 1\n", encoding="utf-8")
    log = tmp_path / "validate.log"
    log.write_text("defect\n", encoding="utf-8")

    def fake_auto_fix(_argv: list[str]) -> int:
        print("AUTOFIX_STATUS=exhausted")
        print("FIXED_BY=")
        print(f"ORIGINAL_VALIDATE_LOG_FILE={log}")
        return 0

    def fake_record(**_kwargs: object) -> None:
        return None

    monkeypatch.setattr(plan_quality, "auto_fix_plan_commands_main", fake_auto_fix)
    monkeypatch.setattr(plan_quality, "_record_validator_escalation", fake_record)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    args = [
        "--site",
        "design Step 2b",
        "--validator-target-file",
        str(plan),
        "--validate-log-file",
        str(log),
        "--validate-defect-count",
        "1",
        "--validate-unsafe-token-count",
        "0",
        "--validate-skipped-count",
        "0",
    ]
    assert plan_quality.validator_autofix_main(args) == 0
    _ = capsys.readouterr()
    assert plan_quality.validator_autofix_main(args) == 0
    assert "AUTOFIX_STATUS=skipped-cycle-cap" in capsys.readouterr().out


def test_validator_autofix_pause_short_circuits(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".pause-requested").write_text("", encoding="utf-8")
    called = False

    def fake_pause(_ctx: object | None = None) -> int:
        nonlocal called
        called = True
        return 11

    monkeypatch.setattr(plan_quality, "_validator_pause_save", fake_pause)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    assert plan_quality.validator_autofix_main([]) == 11
    assert called


def test_validator_autofix_pause_save_uses_resolved_design_tmpdir_on_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    real = tmp_path / "real-design"
    real.mkdir()
    (real / ".pause-requested").write_text("", encoding="utf-8")
    link = tmp_path / "link-design"
    link.symlink_to(real)
    seen: list[str] = []

    def fake_pause(ctx: object | None = None) -> int:
        from larch.core.ctx import Ctx  # noqa: PLC0415  # pylint: disable=import-outside-toplevel

        assert isinstance(ctx, Ctx)
        seen.append(ctx.design_tmpdir)
        return 11

    monkeypatch.setattr(plan_quality, "_validator_pause_save", fake_pause)
    monkeypatch.setenv("DESIGN_TMPDIR", str(link))
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    assert plan_quality.validator_autofix_main([]) == 11
    assert Path(seen[0]).resolve() == real.resolve()


def test_validator_pause_save_uses_rehydrated_ctx_not_stale_ambient_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    (design / ".pause-requested").write_text("", encoding="utf-8")
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(
        "\n".join(
            [
                f"export DESIGN_TMPDIR={design.resolve()}",
                "export ISSUE_NUMBER=42",
                "export REPO=owner/repo",
                f"export CLAUDE_PLUGIN_ROOT={REPO_ROOT}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("ISSUE_NUMBER", "999")
    monkeypatch.setenv("REPO", "stale/repo")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))
    seen: list[list[str]] = []

    def fake_pause_save(argv: list[str]) -> int:
        seen.append(list(argv))
        return 0

    monkeypatch.setattr(design_pause, "pause_save_main", fake_pause_save)
    rc = plan_quality.validator_autofix_main(
        [
            "--session-env-path",
            str(env_path),
            "--claude-pid",
            "123",
            "--plugin-root",
            str(REPO_ROOT),
        ]
    )
    assert rc == 0
    assert seen
    argv = seen[0]
    assert argv[argv.index("--issue") + 1] == "42"
    assert argv[argv.index("--repo") + 1] == "owner/repo"


def test_validator_operator_cancel_audit_uses_rehydrated_summary_outcome_not_stale_ambient(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    design = tmp_path / "design"
    design.mkdir()
    env_path = tmp_path / "source-env.sh"
    env_path.write_text(
        "\n".join(
            [
                f"export DESIGN_TMPDIR={design.resolve()}",
                "export SUMMARY_OUTCOME=cancelled-operator",
                f"export CLAUDE_PLUGIN_ROOT={REPO_ROOT}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("DESIGN_TMPDIR", str(design))
    monkeypatch.setenv("SUMMARY_OUTCOME", "approved")
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(REPO_ROOT))

    def fake_run(cmd: list[str] | str, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd_list = list(cmd) if isinstance(cmd, list) else [str(cmd)]
        return subprocess.CompletedProcess(cmd_list, 0)

    monkeypatch.setattr(plan_quality.subprocess, "run", fake_run)
    rc = plan_quality.validator_autofix_main(
        [
            "--session-env-path",
            str(env_path),
            "--claude-pid",
            "123",
            "--plugin-root",
            str(REPO_ROOT),
            "--operator-cancel",
        ]
    )
    assert rc == 0
    sentinel = design / "design-failure-operator-action.env"
    assert sentinel.is_file()
    text = sentinel.read_text(encoding="utf-8")
    assert "OUTCOME=cancelled-operator" in text
    assert "OUTCOME=approved" not in text


def test_validator_autofix_rejects_missing_design_tmpdir(capsys: pytest.CaptureFixture[str]) -> None:
    rc = plan_quality.validator_autofix_main([])
    err = capsys.readouterr().err
    assert rc == 1
    assert "DESIGN_TMPDIR required" in err


def test_validator_autofix_rejects_relative_design_tmpdir(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setenv("DESIGN_TMPDIR", "relative/path")
    rc = plan_quality.validator_autofix_main([])
    err = capsys.readouterr().err
    assert rc == 2
    assert "ERROR=" in err


def test_validator_autofix_captures_emit_kv_with_quiet_active(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\nbody\ndiff_lines: 1\n", encoding="utf-8")

    def fake_auto_fix(_argv: list[str]) -> int:
        logging_util.emit_kv(key="AUTOFIX_STATUS", value="ok")
        logging_util.emit_kv(key="FIXED_BY", value="codex")
        return 0

    monkeypatch.setattr(plan_quality, "auto_fix_plan_commands_main", fake_auto_fix)
    monkeypatch.setattr(plan_quality, "_validator_require_plugin_root", lambda: 1)
    monkeypatch.setenv("DESIGN_TMPDIR", str(tmp_path))
    monkeypatch.delenv("LARCH_QUIET_DISABLE", raising=False)
    logging_util.quiet_init(argv0="parent-quiet")
    rc = plan_quality.validator_autofix_main(["--site", "design Step 2b", "--validator-target-file", str(plan)])
    out = capsys.readouterr().out
    assert rc == 0
    assert "AUTOFIX_STATUS=ok" in out
    assert "FIXED_BY=codex" in out


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
        "--codex-binary-found",
        "false",
        "--cursor-binary-found",
        "false",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "failed-no-patch"
    assert out["REVISE_TIER_1_STATUS"] == "skipped-binary-missing"
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
    assert out["REVISE_TIER_1_STATUS"] == "skipped-binary-missing"
    assert out["REVISE_TIER_2_STATUS"] == "emit-plan-failed"
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
    assert out["REVISE_TIER_1_STATUS"] == "skipped-binary-missing"
    assert out["REVISE_TIER_2_STATUS"] == "apply-failed"
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


def test_revise_waterfall_refreshes_oversize_override_authority_on_success(tmp_path: Path) -> None:
    original = "## Plan\n### UPDATED: file.txt\nbody\noversize_override: operator\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    assert plan_quality.set_oversize_override_main(["--design-tmpdir", str(tmp_path)]) == 0
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
changed body
oversize_override: operator
diff_lines: 2
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
    assert out["REVISE_STATUS"] == "ok"
    assert "changed body" in plan.read_text(encoding="utf-8")
    size_cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    size_out = dict(line.split("=", 1) for line in size_cp.stdout.splitlines() if "=" in line)
    assert size_cp.returncode == 0, size_cp.stdout
    assert size_out["OVERSIZE_OVERRIDE"] == "operator"


def test_revise_waterfall_attempts_cursor_first_when_present(tmp_path: Path) -> None:
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
if grep -Fq 'complete replacement plan' "$prompt" && [ "$(basename "$out")" = "cursor-output.txt" ]; then
  cat >"$out" <<'PLAN'
## Plan
### UPDATED: file.txt
cursor fixed
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
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "true",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "ok-fallback"
    assert out["REVISE_TIER_4_STATUS"] == "ok"
    assert out["REVISE_WINNING_TIER"] == "cursor"
    assert out["REVISE_PATCH_PATH"].endswith("revise/cursor-output.txt")
    # Cursor-first order in both the initial unified-diff pass and the
    # file-replacement fallback pass (Part 1: Cursor-first apply-agent).
    assert calls.read_text(encoding="utf-8").splitlines() == [
        "cursor-output.txt",
        "codex-output.txt",
        "claude-output.txt",
        "cursor-output.txt",
    ]


def test_revise_waterfall_tier4_merge_keeps_invalid_patch_over_emit_plan_failed(tmp_path: Path) -> None:
    original = "## Plan\nalpha\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
out=""; prompt=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --prompt-file) prompt="$2"; shift 2 ;;
    *) shift ;;
  esac
done
name=$(basename "$out")
if grep -Fq 'complete replacement plan' "$prompt"; then
  if [ "$name" = "codex-output.txt" ]; then
    cat >"$out" <<'PLAN'
## Plan
missing diff_lines trailer
PLAN
  elif [ "$name" = "cursor-output.txt" ]; then
    touch "${DESIGN_TMPDIR:?}/.force-emit-fail"
    cat >"$out" <<'PLAN'
## Plan
cursor fallback
diff_lines: 1
PLAN
  else
    : >"$out"
  fi
else
  : >"$out"
fi
""",
    )
    driver = _write_executable(
        tmp_path / "driver.sh",
        """#!/usr/bin/env bash
if [ -f "${DESIGN_TMPDIR:?}/.force-emit-fail" ]; then
  rm -f "${DESIGN_TMPDIR:?}/.force-emit-fail"
  printf 'EMIT_PLAN_STATUS=failed\\n'
else
  printf 'EMIT_PLAN_STATUS=ok\\n'
fi
""",
    )
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "true",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "failed-validation"
    assert out["REVISE_TIER_4_STATUS"] == "invalid-patch"
    assert out["REVISE_WINNING_TIER"] == ""
    assert out["REVISE_PATCH_PATH"] == ""
    assert plan.read_text(encoding="utf-8") == original
    revise_env = (tmp_path / "plan-review" / "round-1" / "revise" / "revise.env").read_text(encoding="utf-8")
    assert "REVISE_TIER_4_STATUS=invalid-patch" in revise_env
    assert "REVISE_PLAN_HASH_BEFORE=" in revise_env
    assert "REVISE_PLAN_HASH_AFTER=" in revise_env
    before, after = (line.split("=", 1)[1] for line in revise_env.splitlines() if line.startswith(("REVISE_PLAN_HASH_BEFORE=", "REVISE_PLAN_HASH_AFTER=")))
    assert before == after
    assert (tmp_path / "plan.txt.before-revise").is_file()


def test_revise_waterfall_ok_fallback_persists_revise_env_metadata(tmp_path: Path) -> None:
    plan, findings, feature = _revise_base(tmp_path)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
out=""; prompt=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --prompt-file) prompt="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if grep -Fq 'complete replacement plan' "$prompt"; then
  cat >"$out" <<'PLAN'
## Plan
### UPDATED: file.txt
persist fallback
diff_lines: 1
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
    revise_env = (tmp_path / "plan-review" / "round-1" / "revise" / "revise.env").read_text(encoding="utf-8")
    assert "REVISE_STATUS=ok-fallback" in revise_env
    assert "REVISE_TIER_4_STATUS=ok" in revise_env
    assert "REVISE_WINNING_TIER=codex" in revise_env
    assert out["REVISE_PATCH_PATH"].endswith("revise/codex-output.txt")
    assert not (tmp_path / "plan.txt.before-revise").exists()


def test_revise_waterfall_emit_plan_failure_on_codex_tier_sets_failed_apply(tmp_path: Path) -> None:
    original = "## Plan\nalpha\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    fake = _write_executable(
        tmp_path / "fake-launch.sh",
        """#!/usr/bin/env bash
out=""; prompt=""
while [ $# -gt 0 ]; do
  case "$1" in
    --output) out="$2"; shift 2 ;;
    --prompt-file) prompt="$2"; shift 2 ;;
    *) shift ;;
  esac
done
if grep -Fq 'complete replacement plan' "$prompt"; then
  : >"$out"
else
  name=$(basename "$out")
  if [ "$name" = "codex-output.txt" ]; then
    cat >"$out" <<'PATCH'
```diff
--- a/plan.txt
+++ b/plan.txt
@@ -1,3 +1,3 @@
 ## Plan
-alpha
+never persists
 diff_lines: 1
```
PATCH
  else
    : >"$out"
  fi
fi
""",
    )
    driver = _write_executable(tmp_path / "driver.sh", "#!/usr/bin/env bash\nprintf 'EMIT_PLAN_STATUS=failed\\n'\n")
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(fake),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(fake),
        "LARCH_TEST_DESIGN_DRIVER": str(driver),
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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "true",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["REVISE_STATUS"] == "failed-apply"
    assert out["REVISE_TIER_1_STATUS"] == "no-patch"
    assert out["REVISE_TIER_2_STATUS"] == "emit-plan-failed"
    assert out["REVISE_TIER_3_STATUS"] == "no-patch"
    assert out["REVISE_TIER_4_STATUS"] == "no-patch"
    assert "alpha" in plan.read_text(encoding="utf-8")


def test_validate_unified_headers_rejects_malformed_diff_lines() -> None:
    assert plan_quality.validate_unified_headers("--- \n+++ b/plan.txt\n") is False
    assert plan_quality.validate_unified_headers("--- a/plan.txt\n+++ \n") is False


def test_is_new_script_matches_dot_prefixed_claude_paths(tmp_path: Path) -> None:
    script = tmp_path / ".claude" / "skills" / "foo" / "scripts" / "new.sh"
    script.parent.mkdir(parents=True)
    script.write_text("#!/usr/bin/env bash\n", encoding="utf-8")
    plan = (
        "### NEW: .claude/skills/foo/scripts/new.sh\n"
        "```bash\n"
        ".claude/skills/foo/scripts/new.sh\n"
        "```\n"
        "diff_lines: 1\n"
    )
    rows = plan_quality.parse_plan_commands(plan_text=plan, repo_root=tmp_path, plugin_root=tmp_path)
    tsv = tmp_path / "commands.tsv"
    tsv.write_text(plan_quality.render_plan_command_tsv(rows), encoding="utf-8")
    log = tmp_path / "validate.log"
    cp = run_cli("plan", "validate-commands", "--tsv-file", str(tsv), "--repo-root", str(tmp_path), "--log-file", str(log))
    assert cp.returncode == 0, cp.stderr
    assert "VALIDATE_STATUS=ok" in cp.stdout


def test_check_plan_size_non_file_baseline_recovers_without_crash(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("body\ndiff_lines: 1\n", encoding="utf-8")
    original = tmp_path / "plan.txt-original"
    original.write_text("anchor\ndiff_lines: 2\n", encoding="utf-8")
    baseline = tmp_path / "drift-baseline.env"
    baseline.mkdir()
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["DRIFT_TRIGGER_FIRED"] == "false"
    assert any("drift baseline unreadable" in line for line in cp.stdout.splitlines())


def test_heading_count_includes_optional_scope_and_rejects_malformed(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text(
        "## Files to modify/create\n"
        "### NEW: a.txt\n"
        "### UPDATED: b.txt\n"
        "### REWRITTEN: c.txt\n"
        "### MAY_UPDATE: d.txt\n"
        "###MAY_UPDATE: malformed.txt\n",
        encoding="utf-8",
    )

    assert plan_quality._heading_count(plan) == 4


def test_compose_revise_prompt_preserves_optional_heading_type(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("## Plan\n### MAY_UPDATE: `docs/optional.md`\nbody\ndiff_lines: 1\n", encoding="utf-8")
    findings = tmp_path / "findings.txt"
    findings.write_text("finding\n", encoding="utf-8")
    feature = tmp_path / "feature-description.txt"
    feature.write_text("feature\n", encoding="utf-8")
    keys_file = tmp_path / "keys.env"

    prompt = plan_quality._compose_revise_prompt(plan=plan, findings=findings, feature=feature, keys_file=keys_file, patch_format="file-replacement")

    assert "When the original plan has `### NEW:`, `### UPDATED:`, `### REWRITTEN:`, or `### MAY_UPDATE:` headings, preserve at least one such heading." in prompt
    assert "Preserve `### MAY_UPDATE:` heading type when present; do not convert optional headings to `### NEW:`, `### UPDATED:`, or `### REWRITTEN:`." in prompt


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
    assert out["REVISE_TIER_1_STATUS"] == "skipped-binary-missing"
    assert out["REVISE_TIER_2_STATUS"] == "invalid-patch"
    assert out["REVISE_STATUS"] == "failed-validation"
    assert plan.read_text(encoding="utf-8") == original


FIXTURES_DIR = Path(__file__).resolve().parents[3] / "skills" / "design" / "scripts" / "fixtures" / "parse-plan-commands"
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
    rows = plan_quality.parse_plan_commands(plan_text=plan_text, repo_root=repo, plugin_root=repo)
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
    rows = plan_quality.parse_plan_commands(plan_text=dots, repo_root=REPO_ROOT, plugin_root=REPO_ROOT)
    assert any(row.row_type == "parse_note" for row in rows)
    summary = plan_quality.validate_plan_command_rows(rows=rows, repo_root=REPO_ROOT)
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
        "--codex-binary-found",
        "false",
        "--cursor-binary-found",
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
        "--codex-binary-found",
        "false",
        "--cursor-binary-found",
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


def test_validate_plan_command_rows_dual_root_existence(tmp_path: Path) -> None:
    # A script may exist only in the consumer repo (the #4490 regression) or
    # only in the plugin cache; either root must satisfy the existence check.
    repo = tmp_path / "consumer"
    plugin = tmp_path / "plugin"
    for base in (repo, plugin):
        (base / "skills" / "demo" / "scripts").mkdir(parents=True)
    consumer_only = repo / "skills" / "demo" / "scripts" / "consumer-only.sh"
    plugin_only = plugin / "skills" / "demo" / "scripts" / "plugin-only.sh"
    for script in (consumer_only, plugin_only):
        script.write_text("#!/usr/bin/env bash\necho hi\n", encoding="utf-8")
        script.chmod(0o755)

    def _summary(name: str) -> plan_quality.ValidationSummary:
        plan_text = f"## Plan\n\n```bash\nskills/demo/scripts/{name}\n```\n\ndiff_lines: 1\n"
        rows = plan_quality.parse_plan_commands(plan_text=plan_text, repo_root=repo, plugin_root=plugin)
        return plan_quality.validate_plan_command_rows(rows=rows, repo_root=repo, plugin_root=plugin, help_timeout=5, dry_run_timeout=5)

    # Found under the consumer repo root.
    assert "kind=missing-script" not in _summary("consumer-only.sh").log_text
    # Found under the plugin root fallback.
    assert "kind=missing-script" not in _summary("plugin-only.sh").log_text
    # Present in neither root: still flagged.
    assert "DEFECT script=skills/demo/scripts/nope.sh kind=missing-script" in _summary("nope.sh").log_text


def test_validate_plan_command_rows_single_root_unchanged(tmp_path: Path) -> None:
    # Without a plugin_root, a missing script is still flagged (no regression to
    # the legacy single-root behavior).
    repo = tmp_path / "consumer"
    (repo / "skills" / "demo" / "scripts").mkdir(parents=True)
    plan_text = "## Plan\n\n```bash\nskills/demo/scripts/gone.sh\n```\n\ndiff_lines: 1\n"
    rows = plan_quality.parse_plan_commands(plan_text=plan_text, repo_root=repo, plugin_root=repo)
    summary = plan_quality.validate_plan_command_rows(rows=rows, repo_root=repo, help_timeout=5, dry_run_timeout=5)
    assert "DEFECT script=skills/demo/scripts/gone.sh kind=missing-script" in summary.log_text


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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
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


def test_auto_fix_cursor_dispatch_sets_no_open_browser(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    design_tmpdir = tmp_path / "design"
    design_tmpdir.mkdir()
    prompt = design_tmpdir / "prompt.txt"
    prompt.write_text("fix the plan\n", encoding="utf-8")
    plugin = tmp_path / "plugin"
    (plugin / "python").mkdir(parents=True)
    captured_spawn_env: dict[str, str] = {}
    captured_spawn_cmd: list[str] = []

    def fake_resolve_model_args(_tool: str, *, with_effort: bool = False) -> plan_quality.agents.ModelArgResult:
        assert with_effort is True
        return plan_quality.agents.ModelArgResult(())

    def fake_check_output(_cmd: list[str], **_kwargs: object) -> str:
        return "100\n"

    def fake_run(cmd: list[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        cmd_list = list(cmd) if isinstance(cmd, list) else [cmd]
        if "cursor-wrap-prompt" in cmd_list:
            return subprocess.CompletedProcess(cmd_list, 0, "wrapped prompt", "")
        if "run-external-agent" in cmd_list:
            env = kwargs.get("env")
            captured_spawn_env.update(dict(env) if isinstance(env, dict) else os.environ.copy())
            captured_spawn_cmd.extend(cmd_list)
            return subprocess.CompletedProcess(cmd_list, 0, "", "")
        if "record-vendor-task" in cmd_list:
            return subprocess.CompletedProcess(cmd_list, 0, "", "")
        raise AssertionError(f"unexpected subprocess: {cmd_list}")

    monkeypatch.delenv("NO_OPEN_BROWSER", raising=False)
    monkeypatch.setattr(plan_quality.agents, "resolve_model_args", fake_resolve_model_args)
    monkeypatch.setattr(plan_quality.subprocess, "check_output", fake_check_output)
    monkeypatch.setattr(plan_quality.subprocess, "run", fake_run)

    rc = plan_quality._dispatch_vendor_fix(
        vendor="cursor",
        run_dir=run_dir,
        prompt=prompt,
        design_tmpdir=design_tmpdir,
        plugin=plugin,
        timeout=30,
    )

    assert rc == 0
    assert captured_spawn_env["NO_OPEN_BROWSER"] == "1"
    cursor_argv = captured_spawn_cmd[captured_spawn_cmd.index("--") + 1 :]
    assert cursor_argv[:3] == ["cursor", "agent", "-p"]


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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
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
        "--codex-binary-found",
        "false",
        "--cursor-binary-found",
        "false",
        env=env,
    )
    assert cp.returncode == 0, cp.stderr
    prompt = (tmp_path / "plan-review" / "round-1" / "revise" / "prompt.txt").read_text(encoding="utf-8")
    assert '<plan encoding="literal-redacted">' in prompt
    assert "&lt;&lt;&lt;INJECT" in prompt
    assert "<<<INJECT" not in prompt.split("literal-redacted")[-1]


def test_revise_waterfall_external_autofix_timing_task_kinds(tmp_path: Path) -> None:
    plan, findings, feature = _revise_base(tmp_path)
    codex_argv = tmp_path / "codex.argv"
    cursor_argv = tmp_path / "cursor.argv"
    claude_argv = tmp_path / "claude.argv"
    codex = _write_executable(
        tmp_path / "codex.sh",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >>"{codex_argv}"
exit 0
""",
    )
    cursor = _write_executable(
        tmp_path / "cursor.sh",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >>"{cursor_argv}"
exit 0
""",
    )
    claude = _write_executable(
        tmp_path / "claude.sh",
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >>"{claude_argv}"
exit 0
""",
    )
    env = {
        "LARCH_TEST_LAUNCH_CODEX_REVIEW": str(codex),
        "LARCH_TEST_LAUNCH_CURSOR_REVIEW": str(cursor),
        "LARCH_TEST_LAUNCH_CLAUDE_REVIEW": str(claude),
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
        "--codex-binary-found",
        "true",
        "--cursor-binary-found",
        "true",
        "--patch-format",
        "file-replacement",
        env=env,
    )

    assert cp.returncode == 0, cp.stderr
    assert "--timing-task-kind codex-plan-autofix" in codex_argv.read_text(encoding="utf-8")
    assert "--timing-task-kind cursor-plan-autofix" in cursor_argv.read_text(encoding="utf-8")


def test_revise_waterfall_default_launchers_use_python_cli(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    plan, findings, feature = _revise_base(tmp_path)
    recorded: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(cmd: list[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(cmd, list) and "launch-review" in cmd:
            recorded.append(list(cmd))
            out_path = cmd[cmd.index("--output") + 1]
            Path(out_path).write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        if isinstance(cmd, list) and "launch-claude-review" in cmd:
            out_path = cmd[cmd.index("--output") + 1]
            Path(out_path).write_text("", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        check = kwargs.pop("check", False)
        return real_run(cmd, check=check, **kwargs)  # type: ignore[arg-type,call-overload]

    monkeypatch.setattr(plan_quality.subprocess, "run", fake_run)
    for key in ("LARCH_TEST_LAUNCH_CODEX_REVIEW", "LARCH_TEST_LAUNCH_CURSOR_REVIEW", "LARCH_TEST_LAUNCH_CLAUDE_REVIEW"):
        monkeypatch.delenv(key, raising=False)

    rc = plan_quality.revise_plan_with_waterfall_main(
        [
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
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--patch-format",
            "file-replacement",
        ]
    )
    assert rc == 0
    codex_cmds = [cmd for cmd in recorded if "--tool" in cmd and cmd[cmd.index("--tool") + 1] == "codex"]
    cursor_cmds = [cmd for cmd in recorded if "--tool" in cmd and cmd[cmd.index("--tool") + 1] == "cursor"]
    assert codex_cmds
    assert cursor_cmds
    assert all(cmd[cmd.index("--model-role") + 1] == "fix" for cmd in codex_cmds)
    assert all("--model-role" not in cmd for cmd in cursor_cmds)
    for cmd in codex_cmds + cursor_cmds:
        assert cmd[0] == sys.executable
        assert cmd[1].endswith("python/cli.py")
        assert cmd[2:4] == ["agent", "launch-review"]


def test_revise_waterfall_default_design_driver_is_split_argv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Regression for #4434: the EMIT_PLAN gate's design-driver command must be a
    # properly-split argv list (argv[0] == sys.executable), not a single
    # space-joined string passed as argv[0] (which execve cannot resolve, so the
    # gate raised FileNotFoundError and the waterfall always bailed).
    original = "## Plan\n### UPDATED: file.txt\nbody\ndiff_lines: 1\n"
    plan, findings, feature = _revise_base(tmp_path, original)
    design_driver_cmds: list[list[str]] = []
    real_run = subprocess.run

    def fake_run(cmd: list[str] | str, **kwargs: object) -> subprocess.CompletedProcess[str]:
        if isinstance(cmd, list) and kwargs.get("input") == "ACTION=EMIT_PLAN\n":
            design_driver_cmds.append(list(cmd))
            return subprocess.CompletedProcess(cmd, 0, "EMIT_PLAN_STATUS=ok\n", "")
        if isinstance(cmd, list) and ("launch-review" in cmd or "launch-claude-review" in cmd):
            out_path = cmd[cmd.index("--output") + 1]
            Path(out_path).write_text("## Plan\n### UPDATED: file.txt\nchanged\ndiff_lines: 2\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, "", "")
        check = kwargs.pop("check", False)
        return real_run(cmd, check=check, **kwargs)  # type: ignore[arg-type,call-overload]

    monkeypatch.setattr(plan_quality.subprocess, "run", fake_run)
    for key in ("LARCH_TEST_LAUNCH_CODEX_REVIEW", "LARCH_TEST_LAUNCH_CURSOR_REVIEW", "LARCH_TEST_LAUNCH_CLAUDE_REVIEW", "LARCH_TEST_DESIGN_DRIVER"):
        monkeypatch.delenv(key, raising=False)

    rc = plan_quality.revise_plan_with_waterfall_main(
        [
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
            "--codex-binary-found",
            "true",
            "--cursor-binary-found",
            "true",
            "--patch-format",
            "file-replacement",
        ]
    )
    assert rc == 0
    assert design_driver_cmds, "emit_plan_gate never invoked the design driver"
    cmd = design_driver_cmds[0]
    assert cmd[0] == sys.executable
    assert " " not in cmd[0]
    assert cmd[1].endswith("python/cli.py")
    assert cmd[2:4] == ["design", "driver"]
    assert "--design-tmpdir" in cmd


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


def test_check_plan_size_numeric_mechanical_churn_normalizes_true(tmp_path: Path) -> None:
    (tmp_path / "plan.txt").write_text("body\nmechanical_churn: 35\ndiff_lines: 10\n", encoding="utf-8")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stdout
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["MECHANICAL_CHURN"] == "true"


def test_check_plan_size_zero_mechanical_churn_normalizes_false(tmp_path: Path) -> None:
    (tmp_path / "plan.txt").write_text("body\nmechanical_churn: 0\ndiff_lines: 10\n", encoding="utf-8")
    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stdout
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["MECHANICAL_CHURN"] == "false"


def test_check_plan_size_invalid_mechanical_churn_returns_rc2(tmp_path: Path) -> None:
    (tmp_path / "plan.txt").write_text("body\nmechanical_churn: TRUE\ndiff_lines: 10\n", encoding="utf-8")
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


def test_check_plan_size_firm_heading_surface_triggers_and_override(tmp_path: Path) -> None:
    headings = "\n".join(
        f"### UPDATED: `python/larch/pkg{i}/file.py`"
        for i in range(config.PLAN_SIZE_MAX_FIRM_HEADINGS + 1)
    )
    (tmp_path / "plan.txt").write_text(f"## Files to modify\n\n{headings}\ndiff_lines: 10\n", encoding="utf-8")
    assert plan_quality.set_oversize_override_main(["--design-tmpdir", str(tmp_path)]) == 0

    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["SIZE_TRIGGER_FIRED"] == "false"
    assert out["FIRM_HEADINGS"] == str(config.PLAN_SIZE_MAX_FIRM_HEADINGS + 1)
    assert out["SURFACES_TOUCHED"] == str(config.PLAN_SIZE_MAX_FIRM_HEADINGS + 1)
    assert out["OVERSIZE_OVERRIDE"] == "operator"
    assert "firm-headings" in out["TRIGGER_REASONS"]
    assert "surfaces" in out["TRIGGER_REASONS"]
    assert out["PLAN_SIZE_STATUS"] == "ok"


def test_check_plan_size_ignores_untrusted_oversize_override_trailer(tmp_path: Path) -> None:
    headings = "\n".join(
        f"### UPDATED: `python/larch/pkg{i}/file.py`"
        for i in range(config.PLAN_SIZE_MAX_FIRM_HEADINGS + 1)
    )
    (tmp_path / "plan.txt").write_text(f"## Files to modify\n\n{headings}\noversize_override: operator\ndiff_lines: 10\n", encoding="utf-8")

    cp = run_cli("plan", "check-size", "--design-tmpdir", str(tmp_path))
    assert cp.returncode == 0, cp.stderr
    out = dict(line.split("=", 1) for line in cp.stdout.splitlines() if "=" in line)
    assert out["SIZE_TRIGGER_FIRED"] == "true"
    assert out["OVERSIZE_OVERRIDE"] == ""
    assert out["PLAN_SIZE_STATUS"] == "ok"


def test_set_oversize_override_insert_remove_and_idempotent(tmp_path: Path) -> None:
    plan = tmp_path / "plan.txt"
    plan.write_text("body\ndiff_added: 10\ndiff_lines: 20\n", encoding="utf-8")
    authority = tmp_path / ".gate-b-oversize-override.sha256"

    assert plan_quality.set_oversize_override_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert plan.read_text(encoding="utf-8").splitlines() == [
        "body",
        "diff_added: 10",
        "oversize_override: operator",
        "diff_lines: 20",
    ]
    assert authority.is_file()
    assert plan_quality.set_oversize_override_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert plan.read_text(encoding="utf-8").count("oversize_override: operator") == 1
    assert plan_quality.set_oversize_override_main(["--design-tmpdir", str(tmp_path), "--remove"]) == 0
    assert "oversize_override" not in plan.read_text(encoding="utf-8")
    assert not authority.exists()


@pytest.mark.parametrize("env_value", ["0", "-1", "bad", ""])
def test_check_plan_size_invalid_drift_multiple_falls_back_to_two(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    env_value: str,
) -> None:
    (tmp_path / "plan.txt").write_text("line\n" * 4 + "diff_lines: 4\n", encoding="utf-8")
    monkeypatch.setenv(config.ENV_LARCH_DESIGN_DRIFT_MULTIPLE, env_value)
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert plan_quality.check_plan_size_main(["--design-tmpdir", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "DRIFT_MULTIPLE=2" in out


def test_validate_plan_argv_design_tmpdir_wins_over_stale_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    good = tmp_path / "good"
    good.mkdir()
    stale = tmp_path / "stale"
    stale.mkdir()
    plan = good / "plan.txt"
    plan.write_text("diff_lines: 1\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(stale))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert plan_quality.validate_plan_main(["--plan-file", str(plan), "--design-tmpdir", str(good)]) == 0
    out = capsys.readouterr().out
    assert str(good / "validate-plan-commands.log") in out
    assert not (stale / "validate-plan-commands.log").exists()


def test_check_plan_size_argv_design_tmpdir_wins_over_stale_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    good = tmp_path / "good"
    good.mkdir()
    stale = tmp_path / "stale"
    stale.mkdir()
    (good / "plan.txt").write_text("line\n" * 4 + "diff_lines: 4\n", encoding="utf-8")
    monkeypatch.setenv("DESIGN_TMPDIR", str(stale))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert plan_quality.check_plan_size_main(["--design-tmpdir", str(good)]) == 0
    out = capsys.readouterr().out
    assert "PLAN_LINES=4" in out
    assert (good / "drift-baseline.env").is_file()
    assert not (stale / "drift-baseline.env").exists()


def test_validate_plan_main_does_not_rehydrate_validator_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_rehydrate(_parsed: object) -> dict[str, str]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(plan_quality, "_rehydrate_validator_env", fake_rehydrate)
    plan = tmp_path / "plan.txt"
    plan.write_text("diff_lines: 1\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert plan_quality.validate_plan_main(["--plan-file", str(plan), "--repo-root", str(REPO_ROOT)]) == 0
    assert not called


def test_check_plan_size_main_does_not_rehydrate_validator_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    called = False

    def fake_rehydrate(_parsed: object) -> dict[str, str]:
        nonlocal called
        called = True
        return {}

    monkeypatch.setattr(plan_quality, "_rehydrate_validator_env", fake_rehydrate)
    (tmp_path / "plan.txt").write_text("line\n" * 4 + "diff_lines: 4\n", encoding="utf-8")
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")
    assert plan_quality.check_plan_size_main(["--design-tmpdir", str(tmp_path)]) == 0
    assert not called


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
    redacted = plan_quality.redact_capture(repo_root=REPO_ROOT, text=secret)
    assert secret not in redacted
    assert "withheld" in redacted


def test_git_status_snapshot_detects_untracked_content_change(tmp_path: Path) -> None:
    subprocess.run(["git", "init"], cwd=tmp_path, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "test"], cwd=tmp_path, check=True)
    untracked = tmp_path / "scratch.txt"
    untracked.write_text("before\n", encoding="utf-8")
    before = plan_quality.git_status_snapshot(tmp_path)
    untracked.write_text("after\n", encoding="utf-8")
    after = plan_quality.git_status_snapshot(tmp_path)
    assert before != after
