# pyright: reportUnusedCallResult=false
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import review_pipeline
import review_test_support as rts
import voting

ROOT = rts.ROOT
CLI = rts.CLI
REVIEW_PIPELINE = ROOT / "python" / "review_pipeline.py"


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
    assert "Usage: review gather-context" in result.stderr


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


def test_check_reviewer_failure_threshold_ignores_straggler_drops(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    _ = collector.write_text("", encoding="utf-8")
    dropped = tmp_path / "dropped.tsv"
    _ = dropped.write_text("testing\tcodex\tstraggler-dropped\tcut\n", encoding="utf-8")
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
        "--dropped-slots-file",
        str(dropped),
    )

    assert result.returncode == 0, result.stderr
    assert "THRESHOLD_OK=true" in result.stdout
    assert "FAILED_SLOTS=0" in result.stdout
    assert "DROPPED_STATIC_SLOTS=0" in result.stdout

    _ = dropped.write_text("testing\tcodex\tcollector-failure\tSTATUS=ERROR\n", encoding="utf-8")
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
        "--dropped-slots-file",
        str(dropped),
    )

    assert result.returncode == 0, result.stderr
    assert "THRESHOLD_OK=false" in result.stdout
    assert "FAILED_SLOTS=1" in result.stdout
    assert "DROPPED_STATIC_SLOTS=1" in result.stdout


def test_static_coverage_reason_excuses_straggler_dropped_static_slot(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    arch = tmp_path / "codex-specialist-arch-output.txt"
    _ = arch.write_text("review\n", encoding="utf-8")
    _ = collector.write_text(f"REVIEWER_FILE={arch}\nSTATUS=OK\n\n", encoding="utf-8")
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "arch", "tool": "codex", "output": str(arch), "agent": "agents/reviewer-arch.md"}),
                json.dumps(
                    {
                        "slot": "testing",
                        "tool": "cursor",
                        "output": str(tmp_path / "cursor-specialist-testing-output.txt"),
                        "agent": "agents/reviewer-testing.md",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dropped = tmp_path / "dropped.tsv"
    _ = dropped.write_text("testing\tcursor\tstraggler-dropped\tcut\n", encoding="utf-8")

    import review_pipeline  # noqa: PLC0415

    assert (
        review_pipeline._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
            collector, manifest, [str(arch)], dropped_slots_file=str(dropped)
        )
        == ""
    )


def test_static_coverage_reason_does_not_excuse_mixed_straggler_and_genuine_failure(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    arch = tmp_path / "codex-specialist-arch-output.txt"
    _ = arch.write_text("review\n", encoding="utf-8")
    _ = collector.write_text(f"REVIEWER_FILE={arch}\nSTATUS=OK\n\n", encoding="utf-8")
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        "\n".join(
            [
                json.dumps({"slot": "arch", "tool": "codex", "output": str(arch), "agent": "agents/reviewer-arch.md"}),
                json.dumps(
                    {
                        "slot": "testing",
                        "tool": "codex",
                        "output": str(tmp_path / "codex-specialist-testing-output.txt"),
                        "agent": "agents/reviewer-testing.md",
                    }
                ),
                json.dumps(
                    {
                        "slot": "testing",
                        "tool": "cursor",
                        "output": str(tmp_path / "cursor-specialist-testing-output.txt"),
                        "agent": "agents/reviewer-testing.md",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    dropped = tmp_path / "dropped.tsv"
    _ = dropped.write_text(
        "testing\tcodex\tstraggler-dropped\tcut\n"
        "testing\tcursor\tcollector-failure\tSTATUS=ERROR\n",
        encoding="utf-8",
    )

    import review_pipeline  # noqa: PLC0415

    reason = review_pipeline._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
        collector, manifest, [str(arch)], dropped_slots_file=str(dropped)
    )
    assert reason == "no successful static reviewer for archetype(s): testing"


def test_review_core_prune_nits_override_invokes_stub(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "prune-override-stubs")
    prune_stub = tmp_path / "prune-override.sh"
    marker = tmp_path / "prune-stub-ran"
    rts.write_executable(
        prune_stub,
        f"""#!/usr/bin/env bash
set -euo pipefail
printf 'invoked\\n' > "{marker}"
echo "PRUNED_COUNT=0"
echo "INSCOPE_REMAINING=0"
echo "STATUS=ok"
""",
    )
    outdir = tmp_path / "prune-override-run"
    outdir.mkdir()
    env = rts.build_review_core_env(
        tmp_path / "prune-override-stubs",
        stubs,
        TEST_ACCEPTED="0",
        TEST_FINDINGS="1",
        REVIEW_CORE_PRUNE_NITS_SH=str(prune_stub),
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
    assert marker.is_file()
    assert (outdir / "prune-nit.env").read_text(encoding="utf-8").startswith("PRUNED_COUNT=0")


def test_dispatch_panel_python_surface_does_not_import_agents_waterfall() -> None:
    text = (ROOT / "python" / "review_pipeline.py").read_text(encoding="utf-8")
    assert "agents.run_waterfall" not in text


def test_review_core_default_prune_nits_uses_review_cli() -> None:
    text = REVIEW_PIPELINE.read_text(encoding="utf-8")
    retired_prune = "/".join(("skills", "review", "scripts", "prune-nit-findings.sh"))  # noqa: FLY002
    assert retired_prune not in text
    assert '_call_maybe_override(commands.prune_nits, "prune-nit-findings"' in text


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


def test_review_core_all_oos_parseable_output_bypasses_no_success_gate(tmp_path: Path) -> None:
    result = _run_review_core(
        tmp_path,
        findings=0,
        outdir_name="all-oos-parseable",
        extra_env={
            "TEST_EXTERNAL_STATIC_OUTPUTS": "true",
            "TEST_STATIC_SLOT_COUNT": "3",
            "TEST_COLLECTOR_VARIANT": "empty-with-oos",
        },
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=zero-findings" in result.stdout
    threshold_env = (tmp_path / "all-oos-parseable" / "review-core-threshold.env").read_text(encoding="utf-8")
    assert "COVERAGE_GATE_OK=true" in threshold_env
    assert "COVERAGE_GATE_REASON=parseable reviewer output present" in threshold_env


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


def test_review_core_static_coverage_excuses_straggler_dropped_archetype(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "coverage-excused-stubs")
    dispatch_stub = tmp_path / "coverage-excused-dispatch.sh"
    _write_executable(
        dispatch_stub,
        """#!/usr/bin/env bash
set -euo pipefail
tmp=""
panel="simple"
while [[ $# -gt 0 ]]; do
  case "$1" in
    --review-tmpdir) tmp="$2"; shift 2 ;;
    --panel) panel="$2"; shift 2 ;;
    *) shift 2 ;;
  esac
done
mkdir -p "$tmp"
correctness="$tmp/codex-specialist-correctness-output.txt"
edge="$tmp/codex-specialist-edge-cases-output.txt"
printf 'correctness review\\n' > "$correctness"
printf 'edge review\\n' > "$edge"
dropped="$tmp/panel.dropped-slots"
printf 'testing\\tcursor\\tstraggler-dropped\\tcut\\n' > "$dropped"
cat > "$tmp/panel-manifest.ndjson" <<EOF
{"slot":"correctness","tool":"codex","output":"$correctness","agent":"agents/reviewer-correctness.md"}
{"slot":"edge-cases","tool":"codex","output":"$edge","agent":"agents/reviewer-edge-cases.md"}
{"slot":"testing","tool":"cursor","output":"$tmp/cursor-specialist-testing-output.txt","agent":"agents/reviewer-testing.md"}
EOF
printf 'EXTERNAL_OUTPUT_FILES=%s %s\\n' "$correctness" "$edge"
printf 'CLAUDE_OUTPUT_FILES=\\nPANEL_MODE=waterfall\\nPANEL_SHAPE=%s\\n' "$panel"
printf 'SCOUT_STATUS=na\\nDYNAMIC_SLOTS=0\\nSTATIC_SLOT_COUNT=3\\nSLOT_COUNT=3\\n'
printf 'PANEL_MANIFEST=%s/panel-manifest.ndjson\\nDISPATCH_OK=true\\nDROPPED_SLOTS_FILE=%s\\n' "$tmp" "$dropped"
""",
    )
    outdir = tmp_path / "coverage-excused"
    outdir.mkdir()
    env = rts.build_review_core_env(
        tmp_path / "coverage-excused-stubs",
        stubs,
        REVIEW_CORE_DISPATCH_PANEL_SH=str(dispatch_stub),
        TEST_COLLECTOR_VARIANT="missing-testing",
        TEST_STATIC_SLOT_COUNT="3",
        TEST_FINDINGS="1",
        TEST_ACCEPTED="1",
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
        env=env,
    )

    assert result.returncode == 0, result.stderr
    assert "REVIEW_CORE_STATUS=panel-failed" not in result.stdout
    threshold_env = (outdir / "review-core-threshold.env").read_text(encoding="utf-8")
    assert "THRESHOLD_OK=true" in threshold_env
    assert "COVERAGE_GATE_OK=true" in threshold_env


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


def test_reviewer_prune_record_plan_mode_preserves_spaced_dynamic_label(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text(
        '{"slot":"dyn-cursor-plan-api-contract","tool":"cursor","output":"/tmp/cursor-dyn-api-contract-output.txt"}\n',
        encoding="utf-8",
    )
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text("dyn-cursor-plan-api-contract\tCursor-dyn-Api Contract\n", encoding="utf-8")
    classification = tmp_path / "class.tsv"
    classification.write_text(
        "finding_id\tfinding_reviewers\tvoting_result\n"
        "FINDING_1\tCursor-dyn-Api Contract\taccepted\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "ledger.tsv"
    result = run_review(
        "reviewer-prune",
        "record",
        "--ledger",
        str(ledger),
        "--round",
        "1",
        "--manifest",
        str(manifest),
        "--classification",
        str(classification),
        "--label-map",
        str(label_map),
    )
    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t0\t1")


def test_reviewer_prune_record_plan_mode_splits_whitespace_slug_labels(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text(
        '{"slot":"cursor-plan-pragmatic","tool":"cursor","output":"/tmp/cursor-pragmatic-output.txt"}\n'
        '{"slot":"codex-plan-arch","tool":"codex","output":"/tmp/codex-arch-output.txt"}\n',
        encoding="utf-8",
    )
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text(
        "cursor-plan-pragmatic\tCursor-Pragmatic\n"
        "codex-plan-arch\tCodex-Arch\n",
        encoding="utf-8",
    )
    classification = tmp_path / "class.tsv"
    classification.write_text(
        "finding_id\tfinding_reviewers\tvoting_result\n"
        "FINDING_1\tCursor-Pragmatic Codex-Arch\taccepted\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "ledger.tsv"

    result = run_review(
        "reviewer-prune",
        "record",
        "--ledger",
        str(ledger),
        "--round",
        "1",
        "--manifest",
        str(manifest),
        "--classification",
        str(classification),
        "--label-map",
        str(label_map),
    )

    assert result.returncode == 0, result.stderr
    lines = ledger.read_text(encoding="utf-8").splitlines()
    assert lines[1].endswith("Cursor-Pragmatic\t1\t0\t1")
    assert lines[2].endswith("Codex-Arch\t1\t0\t1")


def test_ensure_reviewer_prune_ledger_preserves_good_rows_and_drops_malformed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.tsv"
    header = "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    ledger.write_text(
        header
        + "\n"
        + "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "bad\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "2\tcodex\tarch\tCodex-Arch\t0\t1\t1\textra\n",
        encoding="utf-8",
    )

    review_pipeline.ensure_reviewer_prune_ledger(ledger)

    assert ledger.read_text(encoding="utf-8").splitlines() == [
        header,
        "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1",
    ]


def test_review_core_main_agent_vote_required_skips_prune_ledger_and_preserves_round_three(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "mav-prune-stubs")
    ledger = tmp_path / "reviewer-prune-ledger.tsv"
    manifest: Path | None = None
    for round_num, extra_env in (
        (1, {"TEST_FINDINGS": "1", "TEST_ACCEPTED": "1", "TEST_ROUND_NUM": "1"}),
        (2, {"TEST_FINDINGS": "1", "TEST_ACCEPTED": "0", "TEST_ROUND_NUM": "2", "TEST_TALLY_STATUS": "main-agent-vote-required"}),
    ):
        outdir = tmp_path / f"mav-prune-{round_num}"
        outdir.mkdir()
        env = rts.build_review_core_env(tmp_path / "mav-prune-stubs", stubs, **extra_env)
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
            str(round_num),
            "--prune-ledger",
            str(ledger),
            env=env,
        )
        assert result.returncode == 0, result.stderr
        manifest = outdir / "panel-manifest.ndjson"

    assert manifest is not None
    ledger_lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 2
    assert ledger_lines[1].startswith("1\t")
    result = _filter_prune_round(tmp_path, manifest, ledger, 3)
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


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


def test_reviewer_prune_record_and_filter_round_three(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text(
        '{"slot":"correctness","tool":"cursor","output":"/tmp/cursor-specialist-correctness-output.txt"}\n',
        encoding="utf-8",
    )
    classification = tmp_path / "class.tsv"
    classification.write_text("finding_id\treviewer_slots\tvoting_result\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    for round_num in (1, 2):
        result = run_review(
            "reviewer-prune",
            "record",
            "--ledger",
            str(ledger),
            "--round",
            str(round_num),
            "--manifest",
            str(manifest),
            "--classification",
            str(classification),
        )
        assert result.returncode == 0, result.stderr
    ledger_lines = ledger.read_text(encoding="utf-8").splitlines()
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1].endswith("\t0\t0\t0")
    out = tmp_path / "filtered.ndjson"
    result = run_review(
        "reviewer-prune",
        "filter",
        "--ledger",
        str(ledger),
        "--round",
        "3",
        "--manifest",
        str(manifest),
        "--out",
        str(out),
    )
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def _write_single_prune_manifest(path: Path) -> None:
    path.write_text(
        '{"slot":"correctness","tool":"cursor","output":"/tmp/cursor-specialist-correctness-output.txt"}\n',
        encoding="utf-8",
    )


def _write_prune_classification(path: Path, voting_results: list[str]) -> None:
    lines = ["finding_id\treviewer_slots\tvoting_result"]
    lines.extend(f"FINDING_{idx}\tcursor-specialist-correctness-output.txt\t{result}" for idx, result in enumerate(voting_results, start=1))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _record_prune_rounds(tmp_path: Path, round_results: list[list[str]]) -> tuple[Path, Path]:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    for round_num, results in enumerate(round_results, start=1):
        classification = tmp_path / f"class-{round_num}.tsv"
        _write_prune_classification(classification, results)
        proc = run_review(
            "reviewer-prune",
            "record",
            "--ledger",
            str(ledger),
            "--round",
            str(round_num),
            "--manifest",
            str(manifest),
            "--classification",
            str(classification),
        )
        assert proc.returncode == 0, proc.stderr
    return manifest, ledger


def _filter_prune_round(tmp_path: Path, manifest: Path, ledger: Path, round_num: int, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return run_review(
        "reviewer-prune",
        "filter",
        "--ledger",
        str(ledger),
        "--round",
        str(round_num),
        "--manifest",
        str(manifest),
        "--out",
        str(tmp_path / f"filtered-{round_num}.ndjson"),
        env=env,
    )


def test_reviewer_prune_filter_prunes_noisy_one_accept_combo(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted"], ["rejected"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_prunes_low_precision_positive_net(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted"], ["neutral", "neutral", "neutral"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_keeps_exact_acceptance_floor(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted"], ["neutral", "neutral"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_preserves_round_five_and_off_override(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted"], ["rejected"]])

    round_five = _filter_prune_round(tmp_path, manifest, ledger, 5)
    disabled = _filter_prune_round(tmp_path, manifest, ledger, 3, env={"LARCH_REVIEWER_PRUNE": "off"})

    assert round_five.returncode == 0, round_five.stderr
    assert "PRUNED_COUNT=0" in round_five.stdout
    assert disabled.returncode == 0, disabled.stderr
    assert "PRUNE_ACTIVE=false" in disabled.stdout
    assert "PRUNED_COUNT=0" in disabled.stdout


def test_review_core_zero_findings_records_prune_ledger(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "zero-prune-stubs")
    ledger = tmp_path / "reviewer-prune-ledger.tsv"
    manifest = tmp_path / "zero-prune-2" / "panel-manifest.ndjson"
    for round_num in (1, 2):
        outdir = tmp_path / f"zero-prune-{round_num}"
        outdir.mkdir()
        env = rts.build_review_core_env(
            tmp_path / "zero-prune-stubs",
            stubs,
            TEST_FINDINGS="0",
            TEST_ACCEPTED="0",
            TEST_ROUND_NUM=str(round_num),
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
            str(round_num),
            "--prune-ledger",
            str(ledger),
            env=env,
        )
        assert result.returncode == 0, result.stderr

    assert ledger.read_text(encoding="utf-8").splitlines()[0] == "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    result = _filter_prune_round(tmp_path, manifest, ledger, 3)
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout


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
    assert "--straggler-cutoff" in argv_text
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


def test_write_proposer_sidecar_and_neutralize(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text(
        "### FINDING_1: Example\n- **Reviewer**: cursor-arch\n- **Concern**: concern\n",
        encoding="utf-8",
    )
    sidecar = tmp_path / "proposer-map.tsv"
    review_pipeline._write_proposer_sidecar_and_neutralize(findings, sidecar)  # pyright: ignore[reportPrivateUsage]
    assert sidecar.is_file()
    neutral = findings.read_text(encoding="utf-8")
    assert "- **Reviewer**: anonymous" in neutral
    assert voting.read_proposer_map(sidecar)["FINDING_1"][0] == "cursor-arch"


def test_review_core_neutralizes_findings_before_voter_dispatch(tmp_path: Path) -> None:
    ballot_snapshot = tmp_path / "ballot-snapshot.md"
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    _write_executable(
        stubs["dispatch_voters"],
        f"""#!/usr/bin/env bash
set -euo pipefail
ballot=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --ballot-file) ballot="$2"; shift 2 ;;
    --review-tmpdir) shift 2 ;;
    --voter-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
cp "$ballot" "{ballot_snapshot}"
printf 'VOTER_1_PATH=/dev/null\\nVOTER_1_TOOL=claude\\nVOTER_1_STATUS=failed\\n'
printf 'VOTER_2_PATH=/dev/null\\nVOTER_2_TOOL=codex\\nVOTER_2_STATUS=failed\\n'
printf 'VOTER_3_PATH=/dev/null\\nVOTER_3_TOOL=cursor\\nVOTER_3_STATUS=failed\\n'
printf 'DISPATCH_OK=true\\n'
""",
    )
    outdir = tmp_path / "neutralized-findings"
    outdir.mkdir(parents=True, exist_ok=True)
    env = rts.build_review_core_env(
        tmp_path / "stubs",
        stubs,
        TEST_FINDINGS="1",
        TEST_ACCEPTED="0",
        TEST_ROUND_NUM="1",
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
    assert ballot_snapshot.is_file()
    snapshot = ballot_snapshot.read_text(encoding="utf-8")
    assert "- **Reviewer**: anonymous" in snapshot
    assert (outdir / "proposer-map.tsv").is_file()
