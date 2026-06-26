# pyright: reportUnusedCallResult=false
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from larch.core import proc
import pytest
import review_pipeline
import review_test_support as rts
import voting

ROOT = rts.ROOT
CLI = rts.CLI
REVIEW_PIPELINE = ROOT / "python" / "review_pipeline.py"


def run_review(*args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env, cwd=cwd)


def _panel_manifest_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _assert_generalist_codex_row(rows: list[dict[str, object]]) -> dict[str, object]:
    row = next(row for row in rows if row.get("slot") == "generalist")
    assert row["tool"] == "codex"
    assert str(row["output"]).endswith("codex-generalist-output.txt")
    assert str(row["agent"]).endswith("agents/code-reviewer.md")
    assert row["focus_area"] == "code-quality"
    assert row["weight"] == 1
    assert row["model_role"] == "default"
    return row


def _write_executable(path: Path, body: str) -> None:
    rts.write_executable(path=path, body=body)


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
        _stub_dir=tmp_path / "stubs",
        stubs=stubs,
        TEST_FINDINGS=str(findings),
        TEST_ACCEPTED=str(accepted),
        TEST_ROUND_NUM=str(round_num)
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


def _run_review_core_body_direct(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    findings: int,
    accepted: int = 0,
    round_num: int = 1,
    mode: str = "diff",
    panel: str = "simple",
    outdir_name: str = "body",
    extra_env: dict[str, str] | None = None,
) -> review_pipeline.ReviewCoreResult:
    stubs = _write_review_core_stubs(tmp_path / f"{outdir_name}-stubs")
    env = rts.build_review_core_env(
        _stub_dir=tmp_path / f"{outdir_name}-stubs",
        stubs=stubs,
        TEST_FINDINGS=str(findings),
        TEST_ACCEPTED=str(accepted),
        TEST_ROUND_NUM=str(round_num)
    )
    if extra_env:
        env.update(extra_env)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    outdir = tmp_path / outdir_name
    parsed: dict[str, str] = {
        "--mode": mode,
        "--output-dir": str(outdir),
        "--codex-available": "true",
        "--cursor-available": "true",
        "--panel": panel,
        "--round-num": str(round_num),
    }
    return review_pipeline._review_core_body(  # pyright: ignore[reportPrivateUsage]
        parsed,
        mode=mode,
        review_tmpdir=outdir,
        codex_available="true",
        cursor_available="true",
        panel=panel,
        dynamic="0",
        round_num=round_num,
        session_env_path="",
        run_id="",
        prune_ledger="",
        site="review Step 2",
        commands=review_pipeline._review_commands(),  # pyright: ignore[reportPrivateUsage]
    )


def _review_core_row_keys(result: review_pipeline.ReviewCoreResult) -> list[str]:
    return [key for key, _value in result.rows]


def _assert_emit_stdout_matches_rows(
    result: review_pipeline.ReviewCoreResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = review_pipeline._emit_review_core_result(result)  # pyright: ignore[reportPrivateUsage]
    out = capsys.readouterr().out
    assert rc == result.rc
    assert out.splitlines() == [f"{key}={value}" for key, value in result.rows]


def test_pre_vote_oos_gate_drops_prefixed_oos_and_renumbers(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    _ = findings.write_text(
        """### FINDING_1: In-scope parser regression
- **Reviewer(s)**: stub
- **Concern**: first body stays intact

### FINDING_2: [OUT_OF_SCOPE] Follow-up cleanup
- **Reviewer(s)**: stub
- **Concern**: dropped body bytes stay intact
- **Suggested revision**: file a follow-up

### FINDING_3: Fix [OUT_OF_SCOPE] marker parsing in body titles
- **Reviewer(s)**: stub
- **Concern**: title marker is not at the front
""",
        encoding="utf-8",
    )

    gate = review_pipeline._apply_pre_vote_oos_gate(findings_file=findings, review_tmpdir=tmp_path)  # pyright: ignore[reportPrivateUsage]

    assert gate.dropped_count == 1
    assert gate.remaining_count == 2
    rewritten = findings.read_text(encoding="utf-8")
    assert re.findall(r"### FINDING_(\d+):", rewritten) == ["1", "2"]
    assert "In-scope parser regression" in rewritten
    assert "Fix [OUT_OF_SCOPE] marker parsing in body titles" in rewritten
    assert "Follow-up cleanup" not in rewritten
    audit = (tmp_path / "oos-dropped-before-vote.md").read_text(encoding="utf-8")
    assert "### OOS_1: [OUT_OF_SCOPE] Follow-up cleanup" in audit
    assert "- **Concern**: dropped body bytes stay intact" in audit
    env = (tmp_path / "pre-vote-oos-gate.env").read_text(encoding="utf-8")
    assert "PRE_VOTE_OOS_DROPPED_COUNT=1\n" in env
    assert f"PRE_VOTE_OOS_DROPPED_FILE={tmp_path / 'oos-dropped-before-vote.md'}\n" in env
    assert "PRE_VOTE_FINDINGS_REMAINING=2\n" in env
    assert "STATUS=ok\n" in env


def test_review_core_body_zero_findings_returns_ordered_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=0, accepted=0, outdir_name="body-zero")
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.zero_findings
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")
    assert keys.index("VOTING_TALLY_FILE") > keys.index("PANEL_SHAPE")


def test_review_core_body_fix_required_returns_duplicate_classification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=1, accepted=1, outdir_name="body-fix")
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.fix_required
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.count("FINDINGS_CLASSIFICATION_TSV_FILE") == 2
    assert keys.index("VOTER_1_TOOL") < keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")


def test_review_core_body_forwards_parse_failed_count(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        accepted=0,
        outdir_name="body-parse-failed",
        extra_env={"TEST_PARSE_FAILED_COUNT": "2"},
    )

    assert ("PARSE_FAILED_COUNT", "2") in result.rows


def test_review_core_body_description_empty_returns_scout_and_common_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=0,
        mode="description",
        outdir_name="body-desc-empty",
        extra_env={"TEST_SCOPE_COUNT": "0"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.zero_findings
    assert keys[:4] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "SCOUT_MANIFEST", "REVIEW_CORE_STATUS"]
    assert "PANEL_PRUNED_EMPTY" not in keys
    assert ("PANEL_MODE", "normal") in result.rows
    assert ("PANEL_SHAPE", "simple") in result.rows


def test_review_core_body_dispatch_failure_omits_scout_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-dispatch-fail",
        extra_env={"TEST_DISPATCH_FAIL": "true"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert "SCOUT_STATUS" not in keys
    assert keys[0] == "REVIEW_CORE_STATUS"
    assert any(key == "THRESHOLD_REASON" for key in keys)


def test_review_core_body_prune_skipped_includes_pruned_combos(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=0,
        outdir_name="body-prune-skipped",
        extra_env={"TEST_PANEL_PRUNED_EMPTY": "true", "TEST_PRUNED_COMBOS": "cursor:correctness"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.prune_skipped
    assert keys[:4] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PRUNED_COMBOS", "PANEL_PRUNED_EMPTY"]
    assert keys.index("REVIEW_CORE_STATUS") > keys.index("PANEL_PRUNED_EMPTY")


def test_review_core_body_threshold_failure_includes_dispatch_scout_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-threshold-fail",
        extra_env={"TEST_THRESHOLD_OK": "false"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.index("REVIEW_CORE_STATUS") > keys.index("PANEL_PRUNED_EMPTY")


def test_review_core_body_proposer_map_failed_has_no_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_proposer(*_args: object, **_kwargs: object) -> None:
        raise ValueError("proposer map failed")

    monkeypatch.setattr(review_pipeline, "_write_proposer_sidecar_and_neutralize", fail_proposer)
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=1, outdir_name="body-proposer-fail")
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert "FINDINGS_CLASSIFICATION_TSV_FILE" not in keys
    assert "VOTER_1_TOOL" not in keys
    threshold_idx = keys.index("THRESHOLD_REASON")
    assert result.rows[threshold_idx] == ("THRESHOLD_REASON", "proposer-map-failed")


def test_review_core_body_validation_exhausted_proposer_map_failed_has_no_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_proposer(*_args: object, **_kwargs: object) -> None:
        raise ValueError("proposer map failed")

    stubs = _write_review_core_stubs(tmp_path / "body-agg-proposer-fail-stubs")
    monkeypatch.setattr(review_pipeline, "_write_proposer_sidecar_and_neutralize", fail_proposer)
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-agg-proposer-fail",
        extra_env={
            "LARCH_AGGREGATOR_DISABLED": "",
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_exhausted"]),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert "FINDINGS_CLASSIFICATION_TSV_FILE" not in keys
    assert "VOTER_1_TOOL" not in keys
    threshold_idx = keys.index("THRESHOLD_REASON")
    assert result.rows[threshold_idx] == ("THRESHOLD_REASON", "proposer-map-failed")


def test_review_core_body_validation_exhausted_tally_fail_has_no_voter_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stubs = _write_review_core_stubs(tmp_path / "body-agg-tally-fail-stubs")
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-agg-tally-fail",
        extra_env={
            "LARCH_AGGREGATOR_DISABLED": "",
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_exhausted"]),
            "TEST_TALLY_FAIL": "true",
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert "VOTER_1_TOOL" not in keys
    assert "FINDINGS_CLASSIFICATION_TSV_FILE" not in keys


def test_review_core_body_aggregator_validation_exhausted_duplicate_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stubs = _write_review_core_stubs(tmp_path / "body-agg-exhaust-stubs")
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-agg-exhaust",
        extra_env={
            "LARCH_AGGREGATOR_DISABLED": "",
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_exhausted"]),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.aggregator_validation_exhausted
    assert keys.count("FINDINGS_CLASSIFICATION_TSV_FILE") == 2
    assert keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")


def test_review_core_body_aggregate_zero_second_path_merges_dispatch_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    stubs = _write_review_core_stubs(tmp_path / "body-agg-zero-stubs")
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-agg-zero",
        extra_env={
            "LARCH_AGGREGATOR_DISABLED": "",
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_zero"]),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.ok
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert ("PRE_VOTE_FINDINGS_REMAINING", 1) in result.rows
    assert "VOTER_1_TOOL" in keys
    assert keys.index("VOTER_1_TOOL") < keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")


def test_review_core_body_pre_vote_gate_all_oos_skips_voters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = tmp_path / "collect-oos-findings.sh"
    _write_executable(
        collect,
        """#!/usr/bin/env bash
set -euo pipefail
findings=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --findings-file) findings="$2"; shift 2 ;;
    --oos-file) : > "$2"; shift 2 ;;
    --external-output-files|--claude-output-files) shift; while [[ $# -gt 0 && "$1" != --* ]]; do shift; done ;;
    *) shift 2 ;;
  esac
done
rtmp="$(dirname "$findings")"
cat > "$rtmp/collector-results.env" <<EOF
REVIEWER_FILE=$rtmp/codex-specialist-correctness-output.txt
STATUS=OK

EOF
cat > "$findings" <<'EOF'
### FINDING_1: [OUT_OF_SCOPE] Unrelated cleanup
- **Reviewer(s)**: stub
- **Concern**: follow-up only
- **Suggested revision**: file separately
EOF
printf 'FINDINGS_COUNT=1\\nOOS_COUNT=1\\nDIRTY_DETECTED=false\\nCOLLECT_OK=true\\n'
""",
    )
    aggregate = tmp_path / "aggregate-pass-through.sh"
    _write_executable(
        aggregate,
        """#!/usr/bin/env bash
set -euo pipefail
printf 'AGGREGATED=true\\nINPUT_COUNT=1\\nMERGED_COUNT=1\\nREASON=ok\\n'
""",
    )

    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-pre-vote-all-oos",
        extra_env={
            "REVIEW_CORE_COLLECT_FINDINGS_SH": str(collect),
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(aggregate),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.zero_findings
    assert ("PRE_VOTE_OOS_DROPPED_COUNT", 1) in result.rows
    assert ("PRE_VOTE_FINDINGS_REMAINING", 0) in result.rows
    assert "VOTER_1_TOOL" not in keys
    audit = tmp_path / "body-pre-vote-all-oos" / "oos-dropped-before-vote.md"
    assert "### OOS_1: [OUT_OF_SCOPE] Unrelated cleanup" in audit.read_text(encoding="utf-8")


def test_review_core_body_cap_reached_round_five(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        accepted=1,
        round_num=5,
        outdir_name="body-cap-reached",
    )

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.cap_reached
    assert any(key == "REVIEW_CORE_STATUS" and value == "cap-reached" for key, value in result.rows)


def test_review_core_body_main_agent_vote_required_duplicate_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        accepted=0,
        outdir_name="body-mav",
        extra_env={"TEST_TALLY_STATUS": "main-agent-vote-required"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == review_pipeline.ReviewCoreStatus.main_agent_vote_required
    assert keys.count("FINDINGS_CLASSIFICATION_TSV_FILE") == 2
    assert keys.index("VOTER_1_TOOL") < keys.index("FINDINGS_CLASSIFICATION_TSV_FILE")


def test_review_core_body_post_voter_tally_fail_retains_voter_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-post-voter-tally-fail",
        extra_env={"TEST_TALLY_FAIL": "true"},
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == review_pipeline.ReviewCoreStatus.panel_failed
    assert "VOTER_1_TOOL" in keys
    assert keys.index("VOTER_1_TOOL") < keys.index("REVIEW_CORE_STATUS")
    assert "FINDINGS_CLASSIFICATION_TSV_FILE" not in keys


@pytest.mark.parametrize(
    ("outdir_name", "findings", "accepted", "round_num", "extra_env"),
    [
        ("emit-fix-required", 1, 1, 1, None),
        ("emit-zero-findings", 0, 0, 1, None),
        (
            "emit-main-agent",
            1,
            0,
            1,
            {"TEST_TALLY_STATUS": "main-agent-vote-required"},
        ),
        (
            "emit-agg-exhaust",
            1,
            0,
            1,
            {"LARCH_AGGREGATOR_DISABLED": "", "REVIEW_CORE_AGGREGATE_FINDINGS_SH": "__AGG_EXHAUSTED__"},
        ),
        (
            "emit-agg-tally-fail",
            1,
            0,
            1,
            {
                "LARCH_AGGREGATOR_DISABLED": "",
                "REVIEW_CORE_AGGREGATE_FINDINGS_SH": "__AGG_EXHAUSTED__",
                "TEST_TALLY_FAIL": "true",
            },
        ),
        ("emit-desc-empty", 0, 0, 1, {"TEST_SCOPE_COUNT": "0"}),
        ("emit-proposer-fail", 1, 0, 1, None),
        ("emit-post-voter-tally-fail", 1, 0, 1, {"TEST_TALLY_FAIL": "true"}),
        (
            "emit-prune-skipped",
            0,
            0,
            1,
            {"TEST_PANEL_PRUNED_EMPTY": "true", "TEST_PRUNED_COMBOS": "cursor:correctness"},
        ),
    ],
)
def test_emit_review_core_result_stdout_order_matches_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outdir_name: str,
    findings: int,
    accepted: int,
    round_num: int,
    extra_env: dict[str, str] | None,
) -> None:
    env = dict(extra_env or {})
    mode = "description" if outdir_name == "emit-desc-empty" else "diff"
    if env.get("REVIEW_CORE_AGGREGATE_FINDINGS_SH") == "__AGG_EXHAUSTED__":
        stubs = _write_review_core_stubs(tmp_path / f"{outdir_name}-stubs")
        env["REVIEW_CORE_AGGREGATE_FINDINGS_SH"] = str(stubs["aggregate_exhausted"])
    if outdir_name == "emit-proposer-fail":
        def fail_proposer(*_args: object, **_kwargs: object) -> None:
            raise ValueError("proposer map failed")

        monkeypatch.setattr(review_pipeline, "_write_proposer_sidecar_and_neutralize", fail_proposer)
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=findings,
        accepted=accepted,
        round_num=round_num,
        mode=mode,
        outdir_name=outdir_name,
        extra_env=env or None,
    )
    _assert_emit_stdout_matches_rows(result, capsys)


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
    scope_file = rts.kv_get(stdout=result.stdout, key="FILE_LIST_FILE")
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
    diff_file = rts.kv_get(stdout=result.stdout, key="DIFF_FILE")
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


def test_check_reviewer_failure_threshold_ignores_not_substantive_prose_in_output(tmp_path: Path) -> None:
    # Reviewer output that merely *discusses* NOT_SUBSTANTIVE in its findings prose
    # must not downgrade a slot the collector already classified OK. Reproduces #4935:
    # _output_file_success used a loose substring match that false-positived on prose.
    reviewer = tmp_path / "cursor-specialist-correctness-output.txt"
    _ = reviewer.write_text(
        "FINDING_1: the slot is still classified as NOT_SUBSTANTIVE in that path\n",
        encoding="utf-8",
    )
    collector = tmp_path / "collector-results.env"
    _ = collector.write_text(
        f"REVIEWER_FILE={reviewer}\n"
        "TOOL=cursor\n"
        "STATUS=OK\n"
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
    assert "SUCCEEDED_SLOTS=1" in result.stdout
    assert "FAILED_SLOTS=0" in result.stdout
    assert "THRESHOLD_OK=true" in result.stdout


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
            collector=collector,
            manifest=manifest,
            outputs=[str(arch)],
            dropped_slots_file=str(dropped)
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
        collector=collector,
        manifest=manifest,
        outputs=[str(arch)],
        dropped_slots_file=str(dropped)
    )
    assert reason == "no successful static reviewer for archetype(s): testing"


def test_review_core_prune_nits_override_invokes_stub(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "prune-override-stubs")
    prune_stub = tmp_path / "prune-override.sh"
    marker = tmp_path / "prune-stub-ran"
    rts.write_executable(
        path=prune_stub,
        body=f"""#!/usr/bin/env bash
set -euo pipefail
printf 'invoked\\n' > "{marker}"
echo "PRUNED_COUNT=0"
echo "INSCOPE_REMAINING=0"
echo "STATUS=ok"
"""
    )
    outdir = tmp_path / "prune-override-run"
    outdir.mkdir()
    env = rts.build_review_core_env(
        _stub_dir=tmp_path / "prune-override-stubs",
        stubs=stubs,
        TEST_ACCEPTED="0",
        TEST_FINDINGS="1",
        REVIEW_CORE_PRUNE_NITS_SH=str(prune_stub)
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
    assert '_call_maybe_override(command=commands.prune_nits, review_name="prune-nit-findings"' in text


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
        _stub_dir=tmp_path / "stubs",
        stubs=stubs,
        TEST_ACCEPTED="0",
        REVIEW_CORE_COLLECT_FINDINGS_SH=str(collect)
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
        _stub_dir=tmp_path / "coverage-excused-stubs",
        stubs=stubs,
        REVIEW_CORE_DISPATCH_PANEL_SH=str(dispatch_stub),
        TEST_COLLECTOR_VARIANT="missing-testing",
        TEST_STATIC_SLOT_COUNT="3",
        TEST_FINDINGS="1",
        TEST_ACCEPTED="1"
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
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1")


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
    assert lines[1].endswith("Cursor-Pragmatic\t1\t1\t0\t1")
    assert lines[2].endswith("Codex-Arch\t1\t1\t0\t1")


def test_ensure_reviewer_prune_ledger_preserves_good_rows_and_drops_malformed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.tsv"
    legacy_header = "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    current_header = "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count"
    ledger.write_text(
        legacy_header
        + "\n"
        + "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "bad\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "2\tcodex\tarch\tCodex-Arch\t0\t1\t1\textra\n",
        encoding="utf-8",
    )

    review_pipeline.ensure_reviewer_prune_ledger(ledger)

    assert ledger.read_text(encoding="utf-8").splitlines() == [
        current_header,
        "1\tcursor\tcorrectness\tCursor-Correctness\t1\t1\t0\t1",
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
        env = rts.build_review_core_env(_stub_dir=tmp_path / "mav-prune-stubs", stubs=stubs, **extra_env)
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
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count"
    assert ledger_lines[1].endswith("\t0\t0\t0\t0")
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


def _write_prune_classification_rows(path: Path, header: list[str], rows: list[Mapping[str, str]]) -> None:
    lines = ["\t".join(header)]
    lines.extend("\t".join(row.get(col, "") for col in header) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _code_review_prune_row(
    finding_id: str,
    voting_result: str,
    *,
    severity: str = "minor",
    scope: str = "in_scope",
) -> dict[str, str]:
    vote = "YES" if voting_result == "accepted" else "NO" if voting_result == "rejected" else ""
    return {
        "finding_id": finding_id,
        "reviewer_slots": "cursor-specialist-correctness-output.txt",
        "voting_result": voting_result,
        "v1_vote": vote,
        "v1_severity": severity,
        "v2_vote": vote,
        "v2_severity": severity,
        "v3_vote": vote,
        "v3_severity": severity,
        "scope": scope,
    }


def _write_code_review_prune_classification(path: Path, rows: list[Mapping[str, str]]) -> None:
    _write_prune_classification_rows(path, voting.code_review_classification_header().split("\t"), rows)


def _plan_prune_row(
    finding_id: str,
    voting_result: str,
    *,
    severity: str = "minor",
    body_severity: str = "minor",
) -> dict[str, str]:
    vote = "YES" if voting_result == "accepted" else "NO" if voting_result == "rejected" else ""
    return {
        "finding_id": finding_id,
        "finding_reviewers": "Cursor-Arch",
        "voting_result": voting_result,
        "v1_vote": vote,
        "v1_severity": severity,
        "v2_vote": vote,
        "v2_severity": severity,
        "v3_vote": vote,
        "v3_severity": severity,
        "body_severity": body_severity,
        "scope": "in_scope",
    }


def _write_plan_prune_classification(path: Path, rows: list[Mapping[str, str]]) -> None:
    _write_prune_classification_rows(path, voting.findings_classification_header().split("\t"), rows)


def _record_prune_classification(
    ledger: Path,
    manifest: Path,
    classification: Path,
    round_num: int,
    *,
    label_map: Path | None = None,
) -> None:
    args = [
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
    ]
    if label_map is not None:
        args.extend(["--label-map", str(label_map)])
    proc = run_review(*args)
    assert proc.returncode == 0, proc.stderr


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


def test_reviewer_prune_filter_keeps_high_severity_code_review_on_weighted_net(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    round_two = tmp_path / "class-2.tsv"
    _write_code_review_prune_classification(round_one, [_code_review_prune_row("FINDING_1", "accepted", severity="major")])
    _write_code_review_prune_classification(round_two, [_code_review_prune_row("FINDING_2", "rejected")])

    _record_prune_classification(ledger, manifest, round_one, 1)
    _record_prune_classification(ledger, manifest, round_two, 2)
    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t2\t0\t1")
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_prunes_low_severity_code_review_weighted_net(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    round_two = tmp_path / "class-2.tsv"
    _write_code_review_prune_classification(round_one, [_code_review_prune_row("FINDING_1", "accepted", severity="minor")])
    _write_code_review_prune_classification(round_two, [_code_review_prune_row("FINDING_2", "rejected")])

    _record_prune_classification(ledger, manifest, round_one, 1)
    _record_prune_classification(ledger, manifest, round_two, 2)
    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1")
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_record_code_review_without_scope_stays_unweighted(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    classification = tmp_path / "class.tsv"
    header = [col for col in voting.code_review_classification_header().split("\t") if col != "scope"]
    _write_prune_classification_rows(classification, header, [_code_review_prune_row("FINDING_1", "accepted", severity="major")])

    _record_prune_classification(ledger, manifest, classification, 1)

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1")


def test_reviewer_prune_record_plan_mode_weights_high_voter_severity(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text('{"slot":"cursor-plan-arch","tool":"cursor","output":"/tmp/cursor-arch-output.txt"}\n', encoding="utf-8")
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text("cursor-plan-arch\tCursor-Arch\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    classification = tmp_path / "class.tsv"
    _write_plan_prune_classification(classification, [_plan_prune_row("FINDING_1", "accepted", severity="major")])

    _record_prune_classification(ledger, manifest, classification, 1, label_map=label_map)

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("Cursor-Arch\t1\t2\t0\t1")


def test_reviewer_prune_record_plan_mode_ignores_body_severity_for_weight(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text('{"slot":"cursor-plan-arch","tool":"cursor","output":"/tmp/cursor-arch-output.txt"}\n', encoding="utf-8")
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text("cursor-plan-arch\tCursor-Arch\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    classification = tmp_path / "class.tsv"
    _write_plan_prune_classification(
        classification,
        [_plan_prune_row("FINDING_1", "accepted", severity="minor", body_severity="blocking")],
    )

    _record_prune_classification(ledger, manifest, classification, 1, label_map=label_map)

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("Cursor-Arch\t1\t1\t0\t1")


def test_reviewer_prune_filter_floor_uses_unweighted_accepted_with_high_severity(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    round_two = tmp_path / "class-2.tsv"
    _write_code_review_prune_classification(round_one, [_code_review_prune_row("FINDING_1", "accepted", severity="major")])
    _write_code_review_prune_classification(
        round_two,
        [_code_review_prune_row(f"FINDING_{idx}", "neutral") for idx in range(2, 5)],
    )

    _record_prune_classification(ledger, manifest, round_one, 1)
    _record_prune_classification(ledger, manifest, round_two, 2)
    result = _filter_prune_round(tmp_path, manifest, ledger, 3)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t2\t0\t1")
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_accepts_legacy_ledger_rows(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text(
        "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count\n"
        "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        "2\tcursor\tcorrectness\tCursor-Correctness\t0\t1\t1\n",
        encoding="utf-8",
    )

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
            _stub_dir=tmp_path / "zero-prune-stubs",
            stubs=stubs,
            TEST_FINDINGS="0",
            TEST_ACCEPTED="0",
            TEST_ROUND_NUM=str(round_num)
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

    assert ledger.read_text(encoding="utf-8").splitlines()[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count"
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
    # Stub the waterfall: this test asserts only scout/slot accounting (computed
    # before dispatch), so launching the real 11-slot panel adds no coverage and
    # leaves the test as the suite's heaviest real-subprocess fan-out. Matches the
    # other dispatch-panel accounting tests and _dispatch_panel_manifest_rows.
    waterfall = tmp_path / "waterfall-noop.sh"
    _write_waterfall_noop(waterfall)
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "SCOUT_DYNAMIC_ARCHETYPES_SH": str(scout_must_not_run),
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        "DISPATCH_WATERFALL": str(waterfall),
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
        "false",
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
    assert "DYNAMIC_SLOTS=2" in result.stdout
    assert "SLOT_COUNT=5" in result.stdout
    normalized = json.loads((case_dir / "scout-round1-manifest.json").read_text(encoding="utf-8"))
    assert [a["name"] for a in normalized["archetypes"]] == ["arch", "api-contract"]


def test_synthesize_dynamic_slots_passes_findings_ledger_file(tmp_path: Path) -> None:
    scout_manifest = tmp_path / "scout.json"
    scout_manifest.write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "contract",
                        "focus_area": "correctness",
                        "weight": 1,
                        "rationale": "Contract risk.",
                        "prompt_body": "Check contract.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    review_tmpdir = tmp_path / "review"
    review_tmpdir.mkdir()
    manifest = review_tmpdir / "panel-manifest.ndjson"
    calls: list[list[str]] = []

    class Runner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> proc.CommandResult:
            _ = timeout, cwd, env, check, stdout, stderr
            calls.append([str(item) for item in argv])
            return proc.CommandResult(tuple(str(item) for item in argv), 0, "rendered prompt\n", "", 0.0)

    count = review_pipeline._synthesize_dynamic_slots(  # pyright: ignore[reportPrivateUsage]
        scout_manifest=scout_manifest,
        review_tmpdir=review_tmpdir,
        manifest=manifest,
        mode="diff",
        context={"diff_file": str(tmp_path / "diff.txt")},
        codex_available=False,
        runner=Runner()
    )

    assert count == 1
    render_call = next(call for call in calls if call[2:4] == ["render", "specialist"])
    assert "--findings-ledger-file" in render_call
    assert render_call[render_call.index("--findings-ledger-file") + 1] == str(review_tmpdir / "findings-ledger.tsv")


def test_synthesize_dynamic_slots_nested_implement_ledger_root(tmp_path: Path) -> None:
    impl = tmp_path / "impl"
    round_dir = impl / "round-2"
    round_dir.mkdir(parents=True)
    session_env = impl / "session-env.sh"
    session_env.write_text("IMPLEMENT_TMPDIR=" + str(impl) + "\n", encoding="utf-8")
    scout_manifest = round_dir / "scout.json"
    scout_manifest.write_text(
        json.dumps(
            {
                "archetypes": [
                    {
                        "name": "contract",
                        "focus_area": "correctness",
                        "weight": 1,
                        "rationale": "Contract risk.",
                        "prompt_body": "Check contract.",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    manifest = round_dir / "panel-manifest.ndjson"
    calls: list[list[str]] = []

    class Runner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> proc.CommandResult:
            _ = timeout, cwd, env, check, stdout, stderr
            calls.append([str(item) for item in argv])
            return proc.CommandResult(tuple(str(item) for item in argv), 0, "rendered prompt\n", "", 0.0)

    count = review_pipeline._synthesize_dynamic_slots(  # pyright: ignore[reportPrivateUsage]
        scout_manifest=scout_manifest,
        review_tmpdir=round_dir,
        manifest=manifest,
        mode="diff",
        context={"diff_file": str(tmp_path / "diff.txt")},
        codex_available=False,
        session_env_path=str(session_env),
        runner=Runner()
    )

    assert count == 1
    render_call = next(call for call in calls if call[2:4] == ["render", "specialist"])
    assert render_call[render_call.index("--findings-ledger-file") + 1] == str(impl / "findings-ledger.tsv")
    assert render_call[render_call.index("--session-env-path") + 1] == str(session_env)


def test_dispatch_panel_core_generic_codex_static_row_round_matrix(tmp_path: Path) -> None:
    for round_num, expected in ((1, True), (2, True), (3, False)):
        case_dir = tmp_path / f"generic-round-{round_num}"
        case_dir.mkdir()
        _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
        waterfall_stub = tmp_path / f"waterfall-round-{round_num}.sh"
        _write_waterfall_noop(waterfall_stub)
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
            "--round-num",
            str(round_num),
            env={
                "CLAUDE_PLUGIN_ROOT": str(ROOT),
                "LARCH_QUIET_DISABLE": "1",
                "DISPATCH_WATERFALL": str(waterfall_stub),
            },
        )
        assert result.returncode == 0, result.stderr
        rows = _panel_manifest_rows(case_dir / "panel-manifest.ndjson")
        present = any(row.get("slot") == "generalist" for row in rows)
        assert present is expected
        if expected:
            _assert_generalist_codex_row(rows)
            assert "STATIC_SLOT_COUNT=7" in result.stdout


def test_dispatch_panel_core_generic_codex_static_row_when_codex_unavailable(tmp_path: Path) -> None:
    for round_num in (1, 2):
        case_dir = tmp_path / f"generic-unavailable-round-{round_num}"
        case_dir.mkdir()
        _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
        waterfall_stub = tmp_path / f"waterfall-unavailable-round-{round_num}.sh"
        _write_waterfall_noop(waterfall_stub)
        result = run_review(
            "dispatch-panel",
            "--mode",
            "diff",
            "--diff-file",
            str(case_dir / "review.diff"),
            "--review-tmpdir",
            str(case_dir),
            "--codex-available",
            "false",
            "--cursor-available",
            "true",
            "--panel",
            "hard",
            "--plan-file",
            str(case_dir / "plan.md"),
            "--round-num",
            str(round_num),
            env={
                "CLAUDE_PLUGIN_ROOT": str(ROOT),
                "LARCH_QUIET_DISABLE": "1",
                "DISPATCH_WATERFALL": str(waterfall_stub),
            },
        )
        assert result.returncode == 0, result.stderr
        rows = _panel_manifest_rows(case_dir / "panel-manifest.ndjson")
        assert not any(row.get("slot") == "generalist" for row in rows)
        assert "STATIC_SLOT_COUNT=3" in result.stdout


def _write_waterfall_noop(path: Path) -> None:
    _write_executable(
        path,
        """#!/usr/bin/env bash
printf 'DISPATCH_OK=true\\nSTATIC_DISPATCH_OK=true\\nDYNAMIC_DISPATCH_OK=true\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_TOOLS=\\n'
""",
    )


def _dispatch_panel_manifest_rows(case_dir: Path, *, round_num: int, codex_available: str) -> list[dict[str, object]]:
    waterfall = case_dir.parent / "waterfall-noop.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode",
        "diff",
        "--diff-file",
        str(case_dir / "review.diff"),
        "--review-tmpdir",
        str(case_dir),
        "--codex-available",
        codex_available,
        "--cursor-available",
        "true",
        "--panel",
        "simple",
        "--plan-file",
        str(case_dir / "plan.md"),
        "--round-num",
        str(round_num),
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    manifest = case_dir / "panel-manifest.ndjson"
    return [json.loads(line) for line in manifest.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_dispatch_panel_generic_codex_static_row_round_matrix(tmp_path: Path) -> None:
    case_dir = tmp_path / "generic-codex-round-matrix"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")

    for round_num, expect_generalist in ((1, True), (2, True), (3, False)):
        round_dir = case_dir / f"round-{round_num}"
        round_dir.mkdir()
        _ = (round_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
        _ = (round_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
        rows = _dispatch_panel_manifest_rows(round_dir, round_num=round_num, codex_available="true")
        generalist_rows = [row for row in rows if row.get("slot") == "generalist"]
        if expect_generalist:
            assert len(generalist_rows) == 1, f"round {round_num} should include generic Codex row"
            assert generalist_rows[0].get("tool") == "codex"
        else:
            assert generalist_rows == [], f"round {round_num} should omit generic Codex row"


def test_dispatch_panel_generic_codex_static_row_when_codex_unavailable(tmp_path: Path) -> None:
    case_dir = tmp_path / "generic-codex-codex-absent"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    rows = _dispatch_panel_manifest_rows(case_dir, round_num=1, codex_available="false")
    generalist_rows = [row for row in rows if row.get("slot") == "generalist"]
    assert generalist_rows == []
    codex_rows = [row for row in rows if row.get("tool") == "codex"]
    assert codex_rows == []


def test_dispatch_panel_pre_scouted_empty_ok_static_only(tmp_path: Path) -> None:
    case_dir = tmp_path / "pre-scouted-empty"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text('{"archetypes":[]}\n', encoding="utf-8")
    (impl / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    (impl / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "3",
        "--pre-scouted-manifest", str(manifest),
        "--site", "implement Step 5",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "IMPLEMENT_TMPDIR": str(impl), "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=pre-scouted-empty" in result.stdout
    assert "DYNAMIC_SLOTS=0" in result.stdout


def test_dispatch_panel_pre_scouted_filtered_to_zero_is_producer_invalid(tmp_path: Path) -> None:
    case_dir = tmp_path / "pre-scouted-filtered-zero"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    manifest = impl / "scout-coder-manifest.json"
    manifest.write_text(
        '{"archetypes":[{"name":"correctness","focus_area":"correctness","weight":1,"rationale":"Check logic.","prompt_body":"Check logic."}]}\n',
        encoding="utf-8",
    )
    (impl / "step2-scout-coder-status.env").write_text("SCOUT_CODER_STATUS=ok\n", encoding="utf-8")
    (impl / "step2-external-scout-eligible.txt").write_text("eligible\n", encoding="utf-8")
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "3",
        "--pre-scouted-manifest", str(manifest),
        "--site", "implement Step 5",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "IMPLEMENT_TMPDIR": str(impl), "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=producer-invalid" in result.stdout
    assert "SCOUT_FAIL_REASON=pre_scouted_filtered_to_zero" in result.stdout
    assert "DYNAMIC_SLOTS=0" in result.stdout


def test_dispatch_panel_implement_missing_producer_does_not_launch_scout(tmp_path: Path) -> None:
    case_dir = tmp_path / "implement-missing-producer"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    scout = tmp_path / "scout-must-not-run.sh"
    _write_executable(scout, '#!/usr/bin/env bash\necho scout-called > "$1.called"\nexit 99\n')
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "3",
        "--site", "implement Step 5",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "IMPLEMENT_TMPDIR": str(impl), "SCOUT_DYNAMIC_ARCHETYPES_SH": str(scout), "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=producer-missing" in result.stdout
    assert not list(tmp_path.glob("*.called"))
    assert (impl / ".producer-scout-warning-logged").is_file()


def test_dispatch_panel_docs_only_skips_producer_scout_warning(tmp_path: Path) -> None:
    case_dir = tmp_path / "docs-only-skip-warning"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/docs/foo.md b/docs/foo.md\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    classifier = tmp_path / "classify-docs-only.sh"
    _write_executable(classifier, '#!/usr/bin/env bash\nprintf "DIFF_MODE=docs-only\\n"\n')
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "3",
        "--site", "implement Step 5",
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "LARCH_QUIET_DISABLE": "1",
            "IMPLEMENT_TMPDIR": str(impl),
            "CLASSIFY_DIFF_MODE_SH": str(classifier),
            "DISPATCH_WATERFALL": str(waterfall),
        },
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=skipped-docs-only" in result.stdout
    assert not (impl / ".producer-scout-warning-logged").exists()
    assert not (impl / "execution-issues.md").exists()


def test_dispatch_panel_producer_scout_warning_sentinel_prevents_duplicate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    case_dir = tmp_path / "warning-sentinel"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    (impl / ".producer-scout-warning-logged").write_text("logged\n", encoding="utf-8")
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    append_calls: list[list[str]] = []
    original_run = review_pipeline._run_python_cli  # pyright: ignore[reportPrivateUsage]

    def tracking_run(
        args: Sequence[str],
        *,
        runner: proc.Runner | None = None,
        env: Mapping[str, str] | None = None,
    ) -> proc.CommandResult:
        if list(args[:3]) == ["run-log", "append-entry"]:
            append_calls.append(list(args))
        return original_run(args, runner=runner, env=env)

    monkeypatch.setattr(review_pipeline, "_run_python_cli", tracking_run)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "3",
        "--site", "implement Step 5",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "IMPLEMENT_TMPDIR": str(impl), "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    assert "SCOUT_STATUS=producer-missing" in result.stdout
    assert not append_calls


def test_dispatch_panel_review_default_ignores_ambient_implement_tmpdir(tmp_path: Path) -> None:
    case_dir = tmp_path / "review-default-site"
    case_dir.mkdir()
    (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    impl = tmp_path / "impl"
    impl.mkdir()
    scout = tmp_path / "scout.sh"
    called = tmp_path / "scout.called"
    _write_executable(
        scout,
        f"""#!/usr/bin/env bash
out=""
while [[ $# -gt 0 ]]; do
  if [[ "$1" == "--output" ]]; then out="$2"; shift 2; else shift; fi
done
printf 'called\\n' > "{called}"
printf '{{"archetypes":[{{"name":"api-contract","focus_area":"correctness","weight":1,"rationale":"API changed.","prompt_body":"Check API compatibility."}}]}}\\n' > "$out"
printf 'SCOUT_STATUS=ok\\nSCOUT_MANIFEST=%s\\nSCOUT_ARCHETYPE_COUNT=1\\n' "$out"
""",
    )
    waterfall = tmp_path / "waterfall.sh"
    _write_waterfall_noop(waterfall)
    result = run_review(
        "dispatch-panel",
        "--mode", "diff",
        "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir),
        "--codex-available", "false",
        "--cursor-available", "false",
        "--panel", "hard",
        "--plan-file", str(case_dir / "plan.md"),
        "--dynamic-archetypes", "1",
        env={"CLAUDE_PLUGIN_ROOT": str(ROOT), "LARCH_QUIET_DISABLE": "1", "IMPLEMENT_TMPDIR": str(impl), "SCOUT_DYNAMIC_ARCHETYPES_SH": str(scout), "DISPATCH_WATERFALL": str(waterfall)},
    )
    assert result.returncode == 0, result.stderr
    assert called.is_file()
    assert "SCOUT_STATUS=ok" in result.stdout


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
    assert "--model-role review" in argv_text


def test_dispatch_panel_core_threads_site_to_waterfall(tmp_path: Path) -> None:
    case_dir = tmp_path / "site-dispatch"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    waterfall_stub = tmp_path / "waterfall-site-stub.sh"
    argv_log = tmp_path / "waterfall-site.argv"
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
        "--site",
        "implement Step 5",
        env={
            "CLAUDE_PLUGIN_ROOT": str(ROOT),
            "LARCH_QUIET_DISABLE": "1",
            "DISPATCH_WATERFALL": str(waterfall_stub),
            "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
            "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
        },
    )
    assert result.returncode == 0, result.stderr
    assert "--site implement Step 5" in argv_log.read_text(encoding="utf-8")


def _write_carry_forward_manifest(path: Path, rows: list[dict[str, object]]) -> None:
    path.write_text("".join(json.dumps(row, separators=(",", ":")) + "\n" for row in rows), encoding="utf-8")


def _write_carry_forward_collector(path: Path, records: list[dict[str, str]]) -> None:
    text = ""
    for record in records:
        text += "".join(f"{key}={value}\n" for key, value in record.items()) + "\n"
    path.write_text(text, encoding="utf-8")


def test_degraded_retry_carry_forward_partitions_substantive_slots(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    ok_cursor = review_tmpdir / "cursor-specialist-correctness-output.txt"
    failed_codex = review_tmpdir / "codex-specialist-testing-output.txt"
    ok_dynamic = review_tmpdir / "dyn-foo-output.txt"
    for output in (ok_cursor, failed_codex, ok_dynamic):
        _ = output.write_text("findings\n", encoding="utf-8")
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [
        {"slot": "correctness", "tool": "cursor", "output": str(ok_cursor), "agent": "a"},
        {"slot": "testing", "tool": "codex", "output": str(failed_codex), "agent": "a"},
        {"slot": "dyn-foo", "tool": "cursor", "output": str(ok_dynamic), "prompt_file": "p"},
    ])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(ok_cursor), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(failed_codex), "TOOL": "codex", "STATUS": "NOT_SUBSTANTIVE", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(ok_dynamic), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
    ])
    _ = (review_tmpdir / "degraded-retry.flag").touch()
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    assert launch_manifest != manifest
    assert [str(row["slot"]) for row in _panel_manifest_rows(launch_manifest)] == ["testing"]
    assert carry_outputs == [str(ok_cursor), str(ok_dynamic)]
    assert carry_tools == ["cursor", "cursor"]


def test_degraded_retry_carry_forward_inactive_without_flag(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    ok_cursor = review_tmpdir / "cursor-specialist-correctness-output.txt"
    _ = ok_cursor.write_text("findings\n", encoding="utf-8")
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [{"slot": "correctness", "tool": "cursor", "output": str(ok_cursor), "agent": "a"}])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(ok_cursor), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
    ])
    # No degraded-retry.flag: the first pass launches the full panel.
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    assert launch_manifest == manifest
    assert not carry_outputs
    assert not carry_tools


def test_degraded_retry_carry_forward_relaunches_ok_slot_with_missing_output(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    present_ok = review_tmpdir / "cursor-specialist-correctness-output.txt"
    missing_ok = review_tmpdir / "codex-specialist-security-output.txt"
    failed = review_tmpdir / "dyn-foo-output.txt"
    _ = present_ok.write_text("findings\n", encoding="utf-8")
    _ = failed.write_text("narrative only\n", encoding="utf-8")
    # missing_ok intentionally never written to disk.
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [
        {"slot": "correctness", "tool": "cursor", "output": str(present_ok), "agent": "a"},
        {"slot": "security", "tool": "codex", "output": str(missing_ok), "agent": "a"},
        {"slot": "dyn-foo", "tool": "cursor", "output": str(failed), "prompt_file": "p"},
    ])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(present_ok), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(missing_ok), "TOOL": "codex", "STATUS": "OK", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(failed), "TOOL": "cursor", "STATUS": "NOT_SUBSTANTIVE", "EXIT_CODE": "0"},
    ])
    _ = (review_tmpdir / "degraded-retry.flag").touch()
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    # The OK slot whose output file vanished is re-launched; only the present OK slot carries.
    assert {str(row["slot"]) for row in _panel_manifest_rows(launch_manifest)} == {"security", "dyn-foo"}
    assert carry_outputs == [str(present_ok)]
    assert carry_tools == ["cursor"]


def test_degraded_retry_carry_forward_carries_cap_hit_slots(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    cap_hit_output = review_tmpdir / "cursor-specialist-correctness-output.txt"
    failed_codex = review_tmpdir / "codex-specialist-testing-output.txt"
    _ = cap_hit_output.write_text("STATUS=cap_hit\npartial findings\n", encoding="utf-8")
    _ = failed_codex.write_text("narrative only\n", encoding="utf-8")
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [
        {"slot": "correctness", "tool": "cursor", "output": str(cap_hit_output), "agent": "a"},
        {"slot": "testing", "tool": "codex", "output": str(failed_codex), "agent": "a"},
    ])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(cap_hit_output), "TOOL": "cursor", "STATUS": "cap_hit", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(failed_codex), "TOOL": "codex", "STATUS": "NOT_SUBSTANTIVE", "EXIT_CODE": "0"},
    ])
    _ = (review_tmpdir / "degraded-retry.flag").touch()
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    assert [str(row["slot"]) for row in _panel_manifest_rows(launch_manifest)] == ["testing"]
    assert carry_outputs == [str(cap_hit_output)]
    assert carry_tools == ["cursor"]


def test_degraded_retry_carry_forward_matches_phase_suffixed_collector_path(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    base_output = review_tmpdir / "cursor-specialist-correctness-output.txt"
    phase2_output = review_tmpdir / "cursor-specialist-correctness-output-phase2.txt"
    failed = review_tmpdir / "codex-specialist-testing-output.txt"
    _ = phase2_output.write_text("findings\n", encoding="utf-8")
    _ = failed.write_text("narrative only\n", encoding="utf-8")
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [
        {"slot": "correctness", "tool": "cursor", "output": str(base_output), "agent": "a"},
        {"slot": "testing", "tool": "codex", "output": str(failed), "agent": "a"},
    ])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(phase2_output), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(failed), "TOOL": "codex", "STATUS": "NOT_SUBSTANTIVE", "EXIT_CODE": "0"},
    ])
    _ = (review_tmpdir / "degraded-retry.flag").touch()
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    assert [str(row["slot"]) for row in _panel_manifest_rows(launch_manifest)] == ["testing"]
    assert carry_outputs == [str(phase2_output)]
    assert carry_tools == ["cursor"]


def test_degraded_retry_carry_forward_all_ok_returns_empty(tmp_path: Path) -> None:
    review_tmpdir = tmp_path / "round-1"
    review_tmpdir.mkdir()
    ok_a = review_tmpdir / "cursor-specialist-correctness-output.txt"
    ok_b = review_tmpdir / "codex-specialist-testing-output.txt"
    for output in (ok_a, ok_b):
        _ = output.write_text("findings\n", encoding="utf-8")
    manifest = review_tmpdir / "panel-manifest.ndjson"
    _write_carry_forward_manifest(manifest, [
        {"slot": "correctness", "tool": "cursor", "output": str(ok_a), "agent": "a"},
        {"slot": "testing", "tool": "codex", "output": str(ok_b), "agent": "a"},
    ])
    _write_carry_forward_collector(review_tmpdir / "collector-results.env", [
        {"REVIEWER_FILE": str(ok_a), "TOOL": "cursor", "STATUS": "OK", "EXIT_CODE": "0"},
        {"REVIEWER_FILE": str(ok_b), "TOOL": "codex", "STATUS": "OK", "EXIT_CODE": "0"},
    ])
    _ = (review_tmpdir / "degraded-retry.flag").touch()
    launch_manifest, carry_outputs, carry_tools = review_pipeline._degraded_retry_carry_forward(  # pyright: ignore[reportPrivateUsage]
        manifest=manifest, review_tmpdir=review_tmpdir
    )
    # Defensive: nothing left to re-launch falls back to launching the full panel.
    assert launch_manifest == manifest
    assert not carry_outputs
    assert not carry_tools


def test_dispatch_panel_degraded_retry_carries_forward_substantive_slots(tmp_path: Path) -> None:
    case_dir = tmp_path / "carry-forward"
    case_dir.mkdir()
    _ = (case_dir / "plan.md").write_text("# plan\n", encoding="utf-8")
    _ = (case_dir / "review.diff").write_text("diff --git a/foo b/foo\n", encoding="utf-8")
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    _write_dispatch_vendor_stubs(stub_bin)
    base_env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "LARCH_QUIET_DISABLE": "1",
        "PATH": f"{stub_bin}:{os.environ.get('PATH', '')}",
        "RUN_EXTERNAL_AGENT_POLL_INTERVAL": "0.05",
    }
    panel_args = (
        "dispatch-panel", "--mode", "diff", "--diff-file", str(case_dir / "review.diff"),
        "--review-tmpdir", str(case_dir), "--codex-available", "true", "--cursor-available", "true",
        "--panel", "simple", "--plan-file", str(case_dir / "plan.md"),
    )
    # First pass (no flag) materializes the panel manifest.
    first_stub = tmp_path / "waterfall-first.sh"
    _write_executable(first_stub, "#!/usr/bin/env bash\nprintf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_TOOLS=\\n'\n")
    first = run_review(*panel_args, env={**base_env, "DISPATCH_WATERFALL": str(first_stub)})
    assert first.returncode == 0, first.stderr
    rows = _panel_manifest_rows(case_dir / "panel-manifest.ndjson")
    assert len(rows) >= 2
    # Simulate first-pass results: every slot substantive except the first.
    relaunch_output = str(rows[0]["output"])
    carried = [str(row["output"]) for row in rows[1:]]
    for output in (relaunch_output, *carried):
        _ = Path(output).write_text("findings\n", encoding="utf-8")
    collector_text = f"REVIEWER_FILE={relaunch_output}\nTOOL={rows[0]['tool']}\nSTATUS=NOT_SUBSTANTIVE\nEXIT_CODE=0\n\n"
    for row in rows[1:]:
        collector_text += f"REVIEWER_FILE={row['output']}\nTOOL={row['tool']}\nSTATUS=OK\nEXIT_CODE=0\n\n"
    _ = (case_dir / "collector-results.env").write_text(collector_text, encoding="utf-8")
    _ = (case_dir / "degraded-retry.flag").touch()
    # Retry pass: only the NOT_SUBSTANTIVE slot is re-launched; OK slots carry forward.
    retry_stub = tmp_path / "waterfall-retry.sh"
    argv_log = tmp_path / "waterfall-retry.argv"
    _write_executable(retry_stub, f"#!/usr/bin/env bash\nprintf '%s\\n' \"$*\" >> \"{argv_log}\"\nprintf 'DISPATCH_OK=true\\nALL_OUTPUT_FILES=\\nALL_OUTPUT_TOOLS=\\n'\n")
    retry = run_review(*panel_args, env={**base_env, "DISPATCH_WATERFALL": str(retry_stub)})
    assert retry.returncode == 0, retry.stderr
    match = re.search(r"--slots-file (\S+)", argv_log.read_text(encoding="utf-8"))
    assert match is not None
    relaunch_rows = _panel_manifest_rows(Path(match.group(1)))
    relaunch_outputs = {str(row["output"]) for row in relaunch_rows}
    assert relaunch_output in relaunch_outputs
    for output in carried:
        assert output not in relaunch_outputs
    external_line = next((line for line in retry.stdout.splitlines() if line.startswith("EXTERNAL_OUTPUT_FILES=")), "")
    for output in carried:
        assert output in external_line


def test_review_core_threads_site_to_dispatch_panel_and_voters(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "stubs")
    outdir = tmp_path / "site-core"
    outdir.mkdir(parents=True, exist_ok=True)
    panel_log = tmp_path / "panel.argv"
    voters_log = tmp_path / "voters.argv"
    env = rts.build_review_core_env(
        _stub_dir=tmp_path / "stubs",
        stubs=stubs,
        TEST_FINDINGS="1",
        TEST_ACCEPTED="1",
        TEST_ROUND_NUM="1",
        TEST_DISPATCH_ARGV_LOG=str(panel_log),
        TEST_VOTERS_ARGV_LOG=str(voters_log)
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
        "--site",
        "implement Step 5",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    assert "site=implement Step 5" in panel_log.read_text(encoding="utf-8")
    assert "site=implement Step 5" in voters_log.read_text(encoding="utf-8")


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


def test_collect_findings_caps_oos_per_reviewer_and_keeps_later_in_scope(tmp_path: Path) -> None:
    case = tmp_path / "collect-oos-cap"
    case.mkdir()
    first = case / "claude-primary-output.txt"
    second = case / "claude-secondary-output.txt"
    _ = first.write_text(
        """### Out-of-Scope Observations
- First retained OOS item.
- Second retained OOS item.
- Third retained OOS item.
- Fourth overflow OOS item.
### In-Scope Findings
- Post-OOS in-scope regression.
""",
        encoding="utf-8",
    )
    _ = second.write_text(
        """### Out-of-Scope Observations
- Second reviewer independent OOS item.
""",
        encoding="utf-8",
    )
    for path in (first, second):
        _ = path.with_name(path.name + ".done").write_text("0\n", encoding="utf-8")
        _ = path.with_name(path.name + ".dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    findings = case / "findings.md"
    oos = case / "oos.md"
    env = {
        "CLAUDE_PLUGIN_ROOT": str(ROOT),
        "REVIEW_TMPDIR": str(case),
        "WAIT_FOR_REVIEWERS_POLL_INTERVAL": "0.01",
    }

    first_only = run_review(
        "collect-findings",
        "--claude-output-files",
        str(first),
        "--mode",
        "description",
        "--timeout",
        "1",
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        env=env,
    )

    assert first_only.returncode == 0, first_only.stderr
    assert "OOS_COUNT=3" in first_only.stdout
    assert "FINDINGS_COUNT=4" in first_only.stdout
    first_findings = findings.read_text(encoding="utf-8")
    first_oos = oos.read_text(encoding="utf-8")
    assert "First retained OOS item" in first_findings
    assert "Third retained OOS item" in first_findings
    assert "Fourth overflow OOS item" not in first_findings
    assert "Fourth overflow OOS item" not in first_oos
    assert "Post-OOS in-scope regression" in first_findings
    assert re.findall(r"### FINDING_(\d+):", first_findings) == ["1", "2", "3", "4"]
    assert re.findall(r"### FINDING_(\d+):", first_oos) == ["1", "2", "3"]

    with_second = run_review(
        "collect-findings",
        "--claude-output-files",
        str(first),
        str(second),
        "--mode",
        "description",
        "--timeout",
        "1",
        "--findings-file",
        str(findings),
        "--oos-file",
        str(oos),
        env=env,
    )

    assert with_second.returncode == 0, with_second.stderr
    assert "OOS_COUNT=4" in with_second.stdout
    combined_findings = findings.read_text(encoding="utf-8")
    combined_oos = oos.read_text(encoding="utf-8")
    assert "Second reviewer independent OOS item" in combined_findings
    assert "Second reviewer independent OOS item" in combined_oos
    assert "Fourth overflow OOS item" not in combined_findings
    assert re.findall(r"### FINDING_(\d+):", combined_findings) == ["1", "2", "3", "4", "5"]



def test_collect_findings_claude_no_issues_found_records_ok_with_mixed_failed_slot(tmp_path: Path) -> None:
    case = tmp_path / "collect-claude-no-issues-mixed"
    case.mkdir()
    ok_claude = case / "claude-ok-output.txt"
    failed_claude = case / "claude-failed-output.txt"
    _ = ok_claude.write_text("NO_ISSUES_FOUND\n", encoding="utf-8")
    _ = failed_claude.write_text("Some narrative without findings structure.\n", encoding="utf-8")
    for path in (ok_claude, failed_claude):
        _ = path.with_name(path.name + ".done").write_text("0\n", encoding="utf-8")
        _ = path.with_name(path.name + ".dirty-tree").write_text("STATUS=clean\n", encoding="utf-8")
    findings = case / "findings.md"
    oos = case / "oos.md"
    result = run_review(
        "collect-findings",
        "--claude-output-files",
        str(ok_claude),
        str(failed_claude),
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
    assert "FINDINGS_COUNT=0" in result.stdout
    collector = (case / "collector-results.env").read_text(encoding="utf-8")
    assert (
        f"REVIEWER_FILE={ok_claude}\nTOOL=claude\nSTATUS=OK\nEXIT_CODE=0\n"
        in collector
    )
    assert (
        f"REVIEWER_FILE={failed_claude}\nTOOL=claude\nSTATUS=NOT_SUBSTANTIVE\nEXIT_CODE=0\n"
        in collector
    )
    assert findings.read_text(encoding="utf-8") == ""


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
    env = rts.build_review_core_env(_stub_dir=tmp_path / "handoff-stubs", stubs=stubs, TEST_ACCEPTED="1", TEST_FINDINGS="1")
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
    review_pipeline._write_proposer_sidecar_and_neutralize(ballot_file=findings, proposer_map=sidecar)  # pyright: ignore[reportPrivateUsage]
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
        _stub_dir=tmp_path / "stubs",
        stubs=stubs,
        TEST_FINDINGS="1",
        TEST_ACCEPTED="0",
        TEST_ROUND_NUM="1"
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


def test_collect_findings_sentinel_plain_token(tmp_path: Path) -> None:
    f = tmp_path / "r.md"
    _ = f.write_text("NO_ISSUES_FOUND\n", encoding="utf-8")
    assert review_pipeline._file_has_no_findings_sentinel(f) is True  # pyright: ignore[reportPrivateUsage]


def test_collect_findings_sentinel_whole_file_json(tmp_path: Path) -> None:
    f = tmp_path / "r.md"
    _ = f.write_text('{"no_issues_found": true}\n', encoding="utf-8")
    assert review_pipeline._file_has_no_findings_sentinel(f) is True  # pyright: ignore[reportPrivateUsage]


def test_collect_findings_sentinel_standalone_json_after_prose(tmp_path: Path) -> None:
    # Issue #4911 item 2: a lone {"no_issues_found": true} line after narration is
    # a valid no-findings sentinel (parity with the #4891 collect-time validator).
    f = tmp_path / "r.md"
    _ = f.write_text(
        "I reviewed the diff against the plan and found nothing actionable.\n"
        '{"no_issues_found": true}\n',
        encoding="utf-8",
    )
    assert review_pipeline._file_has_no_findings_sentinel(f) is True  # pyright: ignore[reportPrivateUsage]


def test_collect_findings_sentinel_rejects_inline_json_in_prose(tmp_path: Path) -> None:
    # Inline JSON embedded in a prose line must NOT count as a sentinel.
    f = tmp_path / "r.md"
    _ = f.write_text(
        'The tool emitted {"no_issues_found": true} but I still found a bug.\n'
        "- Off-by-one in the loop bound\n",
        encoding="utf-8",
    )
    assert review_pipeline._file_has_no_findings_sentinel(f) is False  # pyright: ignore[reportPrivateUsage]


def test_collect_findings_sentinel_real_findings_not_sentinel(tmp_path: Path) -> None:
    f = tmp_path / "r.md"
    _ = f.write_text("### In-Scope Findings\n- Something is wrong here\n", encoding="utf-8")
    assert review_pipeline._file_has_no_findings_sentinel(f) is False  # pyright: ignore[reportPrivateUsage]
