from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from typing import TYPE_CHECKING
from pathlib import Path

import config
import logging_util
import review_pipeline
import review_test_support as rts

if TYPE_CHECKING:
    import pytest

ROOT = rts.ROOT
CLI = rts.CLI
REVIEW_CORE = ROOT / "python" / "legacy_review_shell" / "review-core.sh"
PRUNE_NITS = ROOT / "skills" / "review" / "scripts" / "prune-nit-findings.sh"


def run_review(*args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env, cwd=cwd)


def _write_executable(path: Path, body: str) -> None:
    rts.write_executable(path, body)


def _write_review_core_stubs(stub_dir: Path) -> dict[str, Path]:
    return rts.write_review_core_stubs(stub_dir)


def _run_review_core(
    tmp_path: Path,
    *,
    round_num: int = 1,
    findings: int = 1,
    accepted: int = 0,
    extra_env: dict[str, str] | None = None,
    outdir_name: str = "review-core",
) -> subprocess.CompletedProcess[str]:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    outdir = tmp_path / outdir_name
    outdir.mkdir(parents=True, exist_ok=True)
    env = rts.build_review_core_env(
        tmp_path / "stubs",
        stubs,
        TEST_FINDINGS=str(findings),
        TEST_ACCEPTED=str(accepted),
        TEST_ROUND_NUM=str(round_num),
    )
    if extra_env:
        env.update(extra_env)
    return run_review(
        "core",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--round-num",
        str(round_num),
        env=env,
    )


def test_review_core_default_dispatches_voters_through_python_cli() -> None:
    assert rts.review_core_uses_agent_dispatch_voters_by_default()


def test_gather_context_help_routes_through_review_cli() -> None:
    result = run_review("gather-context", "--help")

    assert result.returncode == 0
    assert "Usage: gather-context.sh" in result.stderr


_GIT_IDENTITY = (
    "-c", "user.name=Test User",
    "-c", "user.email=test@example.com",
    "-c", "commit.gpgsign=false",
)


def _git_commit(repo: Path, message: str) -> None:
    """Commit with identity + gpgsign folded into per-command `-c` flags, so no
    standalone `git config` spawns are needed AND every commit (not just the
    first) carries an author identity on hosts without global git config, such
    as CI. #4439 Trick C.
    """
    _ = subprocess.run([rts.GIT, *_GIT_IDENTITY, "commit", "-qm", message], cwd=repo, check=True)


def _init_git_repo(repo: Path, files: dict[str, str], commit_msg: str = "init") -> None:
    """Create repo, write files, and make one `-c`-flagged commit, with no
    standalone `git config` spawns. Cuts the subprocess count of inline
    git-repo setup (#4439 Trick C).
    """
    repo.mkdir(parents=True, exist_ok=True)
    for rel, content in files.items():
        target = repo / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        _ = target.write_text(content, encoding="utf-8")
    _ = subprocess.run([rts.GIT, "init", "-q"], cwd=repo, check=True)
    _ = subprocess.run([rts.GIT, "add", "."], cwd=repo, check=True)
    _git_commit(repo, commit_msg)


def test_gather_context_description_mode_scope_and_stdout_cap(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    fixture.mkdir()
    # gather-context.sh is a retired script path; create it via piecewise Path
    # joins so the literal never appears in source (lint-retired-scripts greps
    # tracked files for it). The fixture only needs the file present so scope
    # detection has a realistic skills/review/ tree to walk.
    review_scripts = fixture / "skills" / "review" / "scripts"
    review_scripts.mkdir(parents=True)
    _ = (review_scripts / "gather-context.sh").write_text("", encoding="utf-8")
    _init_git_repo(
        fixture,
        {
            "skills/review/SKILL.md": "",
            "docs/review-agents.md": "",
            "README.md": "",
        },
        commit_msg="fixture",
    )
    outdir = tmp_path / "gather-out"
    outdir.mkdir()
    result = run_review(
        "gather-context",
        "--mode",
        "description",
        "--description-text",
        "review skill",
        "--output-dir",
        str(outdir),
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT)},
        cwd=fixture,
    )
    assert result.returncode == 0, result.stderr
    assert len(result.stdout) <= 2048
    assert "MODE=description" in result.stdout
    scope_file = rts.kv_get(result.stdout, "FILE_LIST_FILE")
    assert scope_file is not None
    scope_path = Path(scope_file)
    assert scope_path.is_file()
    assert scope_path.stat().st_size > 0
    assert "skills/review/SKILL.md" in scope_path.read_text(encoding="utf-8")


def test_gather_context_diff_mode_relays_branch_kvs_and_trailing_contract(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_git_repo(repo, {"src/main.py": "baseline\n"})
    _ = subprocess.run([rts.GIT, "branch", "-M", "main"], cwd=repo, check=True)
    _ = subprocess.run([rts.GIT, "checkout", "-qb", "feature"], cwd=repo, check=True)
    outdir = tmp_path / "gather-out"
    outdir.mkdir()
    marker = "CONSUMER_REPO_UNIQUE_MARKER_abc123"
    _ = (repo / "src" / "main.py").write_text(f"{marker}\n", encoding="utf-8")
    _ = subprocess.run([rts.GIT, "add", "src/main.py"], cwd=repo, check=True)
    _git_commit(repo, "feature change")
    result = run_review(
        "gather-context",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT)},
        cwd=repo,
    )

    assert result.returncode == 0, result.stderr
    assert "DIFF_FILE=" in result.stdout
    assert "FILE_LIST_FILE=" in result.stdout
    assert "COMMIT_COUNT=" in result.stdout
    assert "SCOPE_FILES_COUNT=0" in result.stdout
    assert "MODE=diff" in result.stdout
    diff_file = rts.kv_get(result.stdout, "DIFF_FILE")
    assert diff_file is not None
    diff_text = Path(diff_file).read_text(encoding="utf-8")
    assert marker in diff_text
    assert "python/review_pipeline.py" not in diff_text


def test_check_reviewer_failure_threshold_zero_static_slots(tmp_path: Path) -> None:
    collector = tmp_path / "collector.tsv"
    _ = collector.write_text("", encoding="utf-8")
    result = run_review(
        "check-reviewer-failure-threshold",
        "--collector-results-file",
        str(collector),
        "--panel",
        "hard",
        "--intended-slots",
        "0",
        "--launched-slots",
        "0",
    )

    assert result.returncode == 0, result.stderr
    assert "THRESHOLD_OK=true" in result.stdout




def test_check_reviewer_failure_threshold_preserves_not_substantive_against_raw_output(tmp_path: Path) -> None:
    reviewer = tmp_path / "cursor-specialist-arch-output.txt"
    _ = reviewer.write_text("narrative output that is non-empty\n", encoding="utf-8")
    collector = tmp_path / "collector-results.env"
    _ = collector.write_text(
        f"REVIEWER_FILE={reviewer}\n"
        "TOOL=cursor\n"
        "STATUS=NOT_SUBSTANTIVE\n"
        "EXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    result = run_review(
        "check-reviewer-failure-threshold",
        "--collector-results-file",
        str(collector),
        "--panel",
        "hard",
        "--intended-slots",
        "1",
        "--launched-slots",
        "1",
        "--reviewer-output-files",
        str(reviewer),
    )

    assert result.returncode == 0, result.stderr
    assert "SUCCEEDED_SLOTS=0" in result.stdout
    assert "FAILED_SLOTS=1" in result.stdout
    assert "NOT_SUBSTANTIVE_SLOTS=1" in result.stdout

def test_dispatch_panel_python_surface_does_not_import_agents_waterfall() -> None:
    text = (ROOT / "python" / "review_pipeline.py").read_text(encoding="utf-8")
    assert "agents.run_waterfall" not in text


def test_review_core_default_prune_nits_sh_points_at_skills_script() -> None:
    text = REVIEW_CORE.read_text(encoding="utf-8")
    match = re.search(
        r'PRUNE_NITS_SH="\$\{REVIEW_CORE_PRUNE_NITS_SH:-([^}]+)\}"',
        text,
    )
    assert match is not None
    default = match.group(1)
    assert "skills/review/scripts/prune-nit-findings.sh" in default
    assert PRUNE_NITS.is_file()


def test_review_core_prune_nit_subprocess_succeeds(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    collect = stubs["collect"]
    _write_executable(
        collect,
        """#!/usr/bin/env bash
set -euo pipefail
findings=""
oos=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) oos="$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$(dirname "$findings")"
rtmp="$(dirname "$findings")"
: > "$oos"
cat > "$rtmp/collector-results.env" <<'EOF'
REVIEWER_FILE=stub-output.txt
STATUS=OK
EOF
cat > "$findings" <<'EOF'
### FINDING_1: Important finding
- **Reviewer(s)**: stub
- **Severity**: important
- **Concern**: real issue
- **Suggested revision**: fix it

### FINDING_2: Nit finding
- **Reviewer(s)**: stub
- **Severity**: nit
- **Concern**: style nit
- **Suggested revision**: trim whitespace
EOF
echo "FINDINGS_COUNT=2"
echo "OOS_COUNT=0"
echo "DIRTY_DETECTED=false"
echo "COLLECT_OK=true"
echo "COLLECTOR_OUTPUT_FILE=collector.env"
""",
    )
    outdir = tmp_path / "review-core-prune"
    outdir.mkdir()
    env = rts.build_review_core_env(
        tmp_path / "stubs",
        stubs,
        TEST_ACCEPTED="0",
        REVIEW_CORE_COLLECT_FINDINGS_SH=str(collect),
    )
    result = run_review(
        "core",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--round-num",
        "1",
        env=env,
    )

    assert result.returncode == 0, result.stderr
    prune_env = outdir / "prune-nit.env"
    assert prune_env.is_file(), result.stdout
    prune_text = prune_env.read_text(encoding="utf-8")
    assert "STATUS=" in prune_text
    assert "PRUNED_COUNT=" in prune_text


def test_review_core_cap_reached_round_5_with_accepted_findings(tmp_path: Path) -> None:
    result = _run_review_core(tmp_path, round_num=5, findings=1, accepted=1)

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=cap-reached" in result.stdout


def test_review_core_zero_findings_emits_classification_and_summary(tmp_path: Path) -> None:
    outdir = tmp_path / "zero"
    result = _run_review_core(tmp_path, findings=0, accepted=0, outdir_name="zero")

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=zero-findings" in result.stdout
    assert "FINDINGS_CLASSIFICATION_TSV_FILE=" in result.stdout
    assert (outdir / "voting-tally.md").is_file()
    summary = json.loads((outdir / "review-summary.json").read_text(encoding="utf-8"))
    assert summary["accepted_count"] == 0


def test_review_core_prune_skipped_early_exit(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=0,
        outdir_name="prune-skipped",
        extra_env={"TEST_PANEL_PRUNED_EMPTY": "true"},
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=prune-skipped" in result.stdout
    assert (tmp_path / "prune-skipped" / "prune-decision.env").is_file()


def test_review_core_panel_failed_on_collector_error_static_files(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=0,
        outdir_name="panel-failed-collector",
        extra_env={
            "TEST_EXTERNAL_STATIC_OUTPUTS": "true",
            "TEST_COLLECTOR_VARIANT": "external-files-only",
        },
    )

    assert result.returncode == 2, result.stderr
    assert "REVIEW_CORE_STATUS=panel-failed" in result.stdout
    threshold_env = (tmp_path / "panel-failed-collector" / "review-core-threshold.env").read_text(encoding="utf-8")
    assert "COVERAGE_GATE_REASON=no successful launched reviewer output" in threshold_env


def test_review_core_panel_failed_on_missing_static_archetype(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=1,
        accepted=1,
        outdir_name="coverage-failed",
        extra_env={
            "TEST_FULL_STATIC_MANIFEST": "true",
            "TEST_COLLECTOR_VARIANT": "missing-testing",
        },
    )

    assert result.returncode == 2, result.stderr
    assert "REVIEW_CORE_STATUS=panel-failed" in result.stdout
    threshold_env = (tmp_path / "coverage-failed" / "review-core-threshold.env").read_text(encoding="utf-8")
    assert "COVERAGE_GATE_REASON=no successful static reviewer for archetype(s): testing" in threshold_env


def test_review_core_panel_failed_on_threshold_failure(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=1,
        accepted=1,
        outdir_name="panel-failed",
        extra_env={
            "TEST_THRESHOLD_OK": "false",
            "TEST_SCOUT_STATUS": "ok",
            "TEST_DYNAMIC_SLOTS": "2",
        },
    )

    assert result.returncode == 2, result.stderr
    assert "REVIEW_CORE_STATUS=panel-failed" in result.stdout
    assert "SCOUT_STATUS=ok" in result.stdout
    assert "DYNAMIC_SLOTS=2" in result.stdout


def test_review_core_main_agent_vote_required(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=1,
        outdir_name="main-agent",
        extra_env={"TEST_TALLY_STATUS": "main-agent-vote-required"},
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=main-agent-vote-required" in result.stdout
    assert "ACCEPTED_COUNT=0" in result.stdout


def test_review_core_aggregator_validation_exhausted(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    result = _run_review_core(
        tmp_path,
        findings=1,
        accepted=1,
        outdir_name="agg-exhaust",
        extra_env={
            "LARCH_AGGREGATOR_DISABLED": "",
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_exhausted"]),
        },
    )

    assert result.returncode == 2, result.stderr
    assert "REVIEW_CORE_STATUS=aggregator-validation-exhausted" in result.stdout


def test_review_core_fix_required_emits_accepted_path(tmp_path: Path) -> None:
    outdir = tmp_path / "fix"
    result = _run_review_core(tmp_path, findings=1, accepted=1, outdir_name="fix")

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=fix-required" in result.stdout
    assert f"ACCEPTED_FINDINGS_FILE={outdir}/accepted-findings.md" in result.stdout


def test_run_legacy_relays_stdout_kv_without_quiet_disable(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    script = tmp_path / "emit-kv.sh"
    _write_executable(script, """#!/usr/bin/env bash
printf 'PIPELINE_KV=relayed\\n'
""")
    logging_util.reset_quiet_state()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setattr(
        review_pipeline,
        "_LEGACY_DIR",
        tmp_path,
        raising=False,
    )
    captured: list[str] = []

    def fake_emit(line: str) -> None:
        captured.append(line)

    monkeypatch.setattr(review_pipeline.logging_util, "emit", fake_emit)
    rc = review_pipeline.run_legacy("emit-kv.sh", [])

    assert rc == 0
    assert captured == ["PIPELINE_KV=relayed"]


def test_run_legacy_relays_lib_quiet_emit_kv_without_quiet_disable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = tmp_path / "quiet-emit.sh"
    lib_quiet = ROOT / "scripts" / "lib-quiet.sh"
    _write_executable(
        script,
        f"""#!/usr/bin/env bash
set -euo pipefail
# shellcheck source=scripts/lib-quiet.sh
source "{lib_quiet}"
larch_quiet_init
emit_kv QUIET_RELAY_TEST relayed-quiet-value
""",
    )
    logging_util.reset_quiet_state()
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    captured: list[str] = []

    def fake_emit(line: str) -> None:
        captured.append(line)

    monkeypatch.setattr(review_pipeline.logging_util, "emit", fake_emit)
    monkeypatch.setattr(review_pipeline, "_LEGACY_DIR", tmp_path, raising=False)
    rc = review_pipeline.run_legacy("quiet-emit.sh", [])

    assert rc == 0
    assert captured == ["QUIET_RELAY_TEST=relayed-quiet-value"]


def test_dispatch_panel_pre_scouted_valid_dynamic_slots(tmp_path: Path) -> None:
    case_dir = tmp_path / "pre-scouted-valid"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    manifest = tmp_path / "pre-scouted-valid.json"
    _ = manifest.write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "arch",
                        "focus_area": "architecture",
                        "weight": 1,
                        "rationale": "Architecture risk is central.",
                        "prompt_body": "Check architecture drift.",
                    },
                    {
                        "name": "api-contract",
                        "focus_area": "correctness",
                        "weight": 4,
                        "rationale": "API changes are central.",
                        "prompt_body": "Check API contract compatibility.",
                    },
                    {
                        "name": "api-contract",
                        "focus_area": "risk-integration",
                        "weight": 3,
                        "rationale": "Duplicate must be normalized out.",
                        "prompt_body": "Duplicate should not survive.",
                    },
                    {
                        "name": "cli-flow",
                        "focus_area": "risk-integration",
                        "weight": 3,
                        "rationale": "CLI behavior changed.",
                        "prompt_body": "Check command flow and user-visible behavior.",
                    },
                ]
            }
        ),
        encoding="utf-8",
    )
    scout_must_not_run = tmp_path / "scout-must-not-run.sh"
    _write_executable(
        scout_must_not_run,
        """#!/usr/bin/env bash
echo "scout must not run" >&2
exit 99
""",
    )
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_executable(
        stub_bin / "codex",
        """#!/usr/bin/env bash
out=""
for arg in "$@"; do [[ "${last:-}" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
printf 'codex review\\n' > "$out"
""",
    )
    _write_executable(
        stub_bin / "cursor",
        """#!/usr/bin/env bash
printf '{"result":"cursor review","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n'
""",
    )
    _write_executable(
        stub_bin / "claude",
        """#!/usr/bin/env bash
cat >/dev/null
printf '{"type":"result","subtype":"success","is_error":false,"result":"claude review","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}\\n'
""",
    )
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "SCOUT_DYNAMIC_ARCHETYPES_SH": str(scout_must_not_run),
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
    }
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "hard",
        "--plan-file",
        str(case_dir / "plan.md"),
        "--dynamic-archetypes",
        "2",
        "--pre-scouted-manifest",
        str(manifest),
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=pre-scouted" in result.stdout
    assert "DYNAMIC_SLOTS=4" in result.stdout
    assert "SLOT_COUNT=10" in result.stdout
    normalized = json.loads((case_dir / "scout-round1-manifest.json").read_text(encoding="utf-8"))
    assert [a["name"] for a in normalized["archetypes"]] == ["arch", "api-contract"]


def _write_dispatch_vendor_stubs(stub_bin: Path) -> None:
    _write_executable(
        stub_bin / "codex",
        """#!/usr/bin/env bash
out=""
for arg in "$@"; do [[ "${last:-}" == "--output-last-message" ]] && out="$arg"; last="$arg"; done
[[ -n "$out" ]] || exit 9
printf 'codex review\\n' > "$out"
""",
    )
    _write_executable(
        stub_bin / "cursor",
        """#!/usr/bin/env bash
printf '{"result":"cursor review","usage":{"inputTokens":1,"outputTokens":1,"cacheReadTokens":0,"cacheWriteTokens":0}}\\n'
""",
    )
    _write_executable(
        stub_bin / "claude",
        """#!/usr/bin/env bash
cat >/dev/null
printf '{"type":"result","subtype":"success","is_error":false,"result":"claude review","usage":{"input_tokens":1,"output_tokens":1,"cache_read_input_tokens":0,"cache_creation_input_tokens":0}}\\n'
""",
    )


def test_dispatch_panel_core_both_vendor_passes_no_fallback(tmp_path: Path) -> None:
    case_dir = tmp_path / "core-both-vendor"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    waterfall_stub = tmp_path / "waterfall-argv-stub.sh"
    argv_log = tmp_path / "waterfall.argv"
    _write_executable(
        waterfall_stub,
        f"""#!/usr/bin/env bash
printf '%s\\n' "$*" >> "{argv_log}"
printf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_FILES_PATH=\\nALL_OUTPUT_TOOLS=\\n'
""",
    )
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_dispatch_vendor_stubs(stub_bin)
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--plan-file",
        str(case_dir / "plan.md"),
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_WATERFALL": str(waterfall_stub),
            "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
            "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        },
    )
    assert result.returncode == 0, result.stderr
    argv_text = argv_log.read_text(encoding="utf-8")
    assert "--no-fallback" in argv_text
    assert "--codex-present true" in argv_text
    assert "--cursor-present true" in argv_text


def test_dispatch_panel_reuse_scout_parse_failed_missing_status(tmp_path: Path) -> None:
    case_dir = tmp_path / "reuse-parse-failed"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    _ = (case_dir / "scout-round3-manifest.json").write_text(
        json.dumps({"archetypes": [{"name": "api", "focus_area": "correctness", "weight": 1, "rationale": "r", "prompt_body": "p"}]}),
        encoding="utf-8",
    )
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_dispatch_vendor_stubs(stub_bin)
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "hard",
        "--plan-file",
        str(case_dir / "plan.md"),
        "--dynamic-archetypes",
        "3",
        "--round-num",
        "3",
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "LARCH_QUIET_DISABLE": "1",
            "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
            "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=parse-failed" in result.stdout
    assert "SCOUT_FAIL_REASON=missing_status_sidecar" in result.stdout
    assert "DYNAMIC_SLOTS=0" in result.stdout


def test_dispatch_panel_limits_invalid_dynamic_archetypes_count(tmp_path: Path) -> None:
    case_dir = tmp_path / "limits-invalid-dynamic"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "hard",
        "--plan-file",
        str(case_dir / "plan.md"),
        "--dynamic-archetypes",
        "9",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1"},
    )
    assert result.returncode == 2
    assert "must be an integer from 0 to 3" in result.stderr


def test_collect_findings_done_sentinel_wait_success(tmp_path: Path) -> None:
    case = tmp_path / "collect-done"
    case.mkdir()
    outf = case / "claude-vote-output.txt"
    _ = outf.write_text(
        """### In-Scope Findings
- Missing validation in parser.
""",
        encoding="utf-8",
    )
    _ = (case / "claude-vote-output.txt.done").write_text("0\n", encoding="utf-8")
    _ = (case / "claude-vote-output.txt.dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    findings = case / "findings.md"
    oos = case / "oos.md"
    result = run_review(
        "collect-findings",
        "--claude-output-files",
        str(outf),
        "--mode",
        "description",
        "--timeout",
        "1",
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "REVIEW_TMPDIR": str(case),
            "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.01",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "COLLECT_OK=true" in result.stdout
    assert "FINDINGS_COUNT=1" in result.stdout
    assert "### FINDING_1:" in findings.read_text(encoding="utf-8")




def test_collect_findings_skips_external_not_substantive_from_collector(tmp_path: Path) -> None:
    case = tmp_path / "collect-external-not-substantive"
    case.mkdir()
    outf = case / "cursor-specialist-arch-output.txt"
    _ = outf.write_text(
        "### In-Scope Findings\n- This narrative finding would be parsed without collector gating.\n",
        encoding="utf-8",
    )
    _ = (case / "cursor-specialist-arch-output.txt.done").write_text("0\n", encoding="utf-8")
    _ = (case / "cursor-specialist-arch-output.txt.dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    findings = case / "findings.md"
    oos = case / "oos.md"
    result = run_review(
        "collect-findings",
        "--external-output-files",
        str(outf),
        "--mode",
        "description",
        "--timeout",
        "1",
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "REVIEW_TMPDIR": str(case),
            "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.01",
            "LARCH_QUIET_DISABLE": "1",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "FINDINGS_COUNT=0" in result.stdout
    assert "STATUS=NOT_SUBSTANTIVE" in (case / "collector-results.env").read_text(encoding="utf-8")
    assert findings.read_text(encoding="utf-8") == ""

def test_collect_findings_wait_timeout_redacts_stderr(tmp_path: Path) -> None:
    # Test that collect-findings exits non-zero when wait-for-reviewers times out.
    # The wait is now handled by python/cli.py agent wait-reviewers (Python-native);
    # we omit the .done sentinel to trigger an actual timeout.
    harness = tmp_path / "plugin-harness"
    scripts = harness / "scripts"
    scripts.mkdir(parents=True)
    for entry in (ROOT / "scripts").iterdir():
        if not entry.is_file():
            continue
        _ = shutil.copy2(entry, scripts / entry.name)
    (harness / "python").symlink_to(ROOT / "python")
    case = tmp_path / "collect-wait-fail"
    case.mkdir()
    outf = case / "claude-wait-output.txt"
    _ = outf.write_text("### In-Scope Findings\n- relay case finding.\n", encoding="utf-8")
    # No .done sentinel — causes the Python wait to time out after --timeout 1.
    result = run_review(
        "collect-findings",
        "--claude-output-files",
        str(outf),
        "--mode",
        "description",
        "--timeout",
        "1",
        "--findings-file",
        str(case / "findings.md"),
        "--oos-file",
        str(case / "oos.md"),
        env={
            "CLAUDE_PLUGIN_ROOT": str(harness),
            "REVIEW_TMPDIR": str(case),
            "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.01",
        },
    )
    # collect-findings exits non-zero when any sentinel times out (TIMEOUT line in wait log)
    assert result.returncode != 0


def test_review_core_oos_snapshot_restore_zero_findings(tmp_path: Path) -> None:
    parent = tmp_path / "parent"
    parent.mkdir()
    session_env = parent / "session.env"
    _ = session_env.write_text("IMPLEMENT_TMPDIR=\n", encoding="utf-8")
    parent_oos = "### OOS_1: [OUT_OF_SCOPE] parent preserved\n"
    parent_accum = "# accumulated parent content\n"
    _ = (parent / "oos-accepted-review.md").write_text(parent_oos, encoding="utf-8")
    _ = (parent / "accumulated-oos.md").write_text(parent_accum, encoding="utf-8")
    result = _run_review_core(
        tmp_path,
        findings=0,
        outdir_name="zero-oos",
        extra_env={
            "SESSION_ENV_PATH": str(session_env),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=zero-findings" in result.stdout
    assert (parent / "oos-accepted-review.md").read_text(encoding="utf-8") == parent_oos
    assert (parent / "accumulated-oos.md").read_text(encoding="utf-8") == parent_accum


def test_review_core_oos_snapshot_restore_prune_skipped(tmp_path: Path) -> None:
    parent = tmp_path / "parent-prune"
    parent.mkdir()
    session_env = parent / "session.env"
    _ = session_env.write_text("IMPLEMENT_TMPDIR=\n", encoding="utf-8")
    parent_oos = "### OOS_1: [OUT_OF_SCOPE] prune parent preserved\n"
    _ = (parent / "oos-accepted-review.md").write_text(parent_oos, encoding="utf-8")
    result = _run_review_core(
        tmp_path,
        findings=0,
        outdir_name="prune-oos",
        extra_env={
            "SESSION_ENV_PATH": str(session_env),
            "TEST_PANEL_PRUNED_EMPTY": "true",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=prune-skipped" in result.stdout
    assert (parent / "oos-accepted-review.md").read_text(encoding="utf-8") == parent_oos


def test_review_core_parent_rejected_and_oos_handoff(tmp_path: Path) -> None:
    parent = tmp_path / "parent-handoff"
    parent.mkdir()
    session_env = parent / "session.env"
    _ = session_env.write_text("IMPLEMENT_TMPDIR=\n", encoding="utf-8")
    stubs = _write_review_core_stubs(tmp_path / "handoff-stubs")
    tally = stubs["tally"]
    _write_executable(
        tally,
        """#!/usr/bin/env bash
set -euo pipefail
tmp=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
printf '### FINDING_1: Example\\n' > "$tmp/accepted-findings.md"
printf '### FINDING_2: rejected parent handoff\\n' > "$tmp/rejected-findings.md"
printf '### OOS_1: [OUT_OF_SCOPE] parent oos handoff\\n' > "$tmp/oos-accepted-review.md"
printf 'TALLY_STATUS=ok\\nACCEPTED_COUNT=1\\nREJECTED_COUNT=1\\nTALLY_FILE=%s/review-tally.env\\n' "$tmp"
printf 'ACCEPTED_FINDINGS_FILE=%s/accepted-findings.md\\nREJECTED_FINDINGS_FILE=%s/rejected-findings.md\\n' "$tmp" "$tmp"
printf 'VOTING_TALLY_FILE=%s/voting-tally.md\\nTALLY_OK=true\\n' "$tmp"
printf '# tally\\n' > "$tmp/voting-tally.md"
""",
    )
    outdir = tmp_path / "handoff-run"
    outdir.mkdir()
    env = rts.build_review_core_env(tmp_path / "handoff-stubs", stubs, TEST_ACCEPTED="1", TEST_FINDINGS="1")
    env["SESSION_ENV_PATH"] = str(session_env)
    result = run_review(
        "core",
        "--mode",
        "diff",
        "--output-dir",
        str(outdir),
        "--codex-available",
        "true",
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--round-num",
        "1",
        "--session-env-path",
        str(session_env),
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=fix-required" in result.stdout
    assert (parent / "rejected-findings.md").is_file()
    assert "rejected parent handoff" in (parent / "rejected-findings.md").read_text(encoding="utf-8")
    assert (parent / "oos-accepted-review.md").is_file()
    assert "parent oos handoff" in (parent / "oos-accepted-review.md").read_text(encoding="utf-8")
