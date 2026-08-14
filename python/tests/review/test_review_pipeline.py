# pyright: reportUnusedCallResult=false
from __future__ import annotations

import json
import subprocess
from collections.abc import Mapping, Sequence
from pathlib import Path

from larch.core import proc
import pytest
from larch.review import coder_runner, dispatch_shared, snapshot
from larch.review import review_core_body, review_pipeline, review_pipeline_shared
from larch.review.review_types import ReviewCoreStatus
import review_test_support as rts
from larch.review import voting
from tests.support.review_wire import panel_manifest_ndjson, panel_manifest_row

ROOT = rts.ROOT
CLI = rts.CLI
REVIEW_PIPELINE = ROOT / "python" / "larch" / "review" / "review_pipeline.py"
REVIEW_CORE_BODY = ROOT / "python" / "larch" / "review" / "review_core_body.py"


def test_review_pipeline_exposes_only_measured_public_modules() -> None:
    assert review_pipeline.external_defaults is not None
    assert review_pipeline.logging_util is not None
    assert not hasattr(review_pipeline, "_ballot_block_count")
    assert not hasattr(review_pipeline, "review_core")
    assert not hasattr(review_pipeline, "reviewer_prune_record")


def run_review(*args: str, env: dict[str, str] | None = None, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return rts.run_review(*args, env=env, cwd=cwd)


def _panel_manifest_rows(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


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
) -> review_core_body.ReviewCoreResult:
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
    return review_core_body._review_core_body(  # pyright: ignore[reportPrivateUsage]
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
        commands=review_core_body._review_commands(),  # pyright: ignore[reportPrivateUsage]
    )


def _review_core_row_keys(result: review_core_body.ReviewCoreResult) -> list[str]:
    return [key for key, _value in result.rows]


def _assert_emit_stdout_matches_rows(
    result: review_core_body.ReviewCoreResult,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = review_core_body._emit_review_core_result(result)  # pyright: ignore[reportPrivateUsage]
    out = capsys.readouterr().out
    assert rc == result.rc
    assert out.splitlines() == [f"{key}={value}" for key, value in result.rows]


def test_oos_prefixed_findings_stay_on_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = """### FINDING_1: In-scope parser regression
- **Reviewer(s)**: stub
- **Concern**: first body stays intact

### FINDING_2: [OUT_OF_SCOPE] Follow-up cleanup
- **Reviewer(s)**: stub
- **Concern**: dropped body bytes stay intact
- **Suggested revision**: file a follow-up

### FINDING_3: [OUT_OF_SCOPE] [security] Sensitive cleanup
- **Reviewer(s)**: stub
- **Concern**: keep this local only
- **Focus area**: security

### FINDING_4: Fix [OUT_OF_SCOPE] marker parsing in body titles
- **Reviewer(s)**: stub
- **Concern**: title marker is not at the front
"""
    _ = findings.write_text(original, encoding="utf-8")

    assert review_core_body._ballot_block_count(findings) == 4  # pyright: ignore[reportPrivateUsage]
    assert findings.read_text(encoding="utf-8") == original
    assert not (tmp_path / "oos-dropped-before-vote.md").exists()
    assert not (tmp_path / "pre-vote-oos-gate.env").exists()


def test_security_oos_prefixed_findings_stay_on_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = """### FINDING_1: [OUT_OF_SCOPE] Security cleanup
- **Reviewer(s)**: stub
- **Concern**: local sidecar only
- **Focus area**: security
"""
    _ = findings.write_text(original, encoding="utf-8")

    assert review_core_body._ballot_block_count(findings) == 1  # pyright: ignore[reportPrivateUsage]
    assert findings.read_text(encoding="utf-8") == original
    assert not (tmp_path / "oos-dropped-security-local.md").exists()


def test_direct_oos_findings_stay_on_ballot(tmp_path: Path) -> None:
    findings = tmp_path / "findings.md"
    original = """### OOS_1: Direct out-of-scope item
- **Reviewer(s)**: stub
- **Concern**: direct ballot rows should count.
"""
    _ = findings.write_text(original, encoding="utf-8")

    assert review_core_body._ballot_block_count(findings) == 1  # pyright: ignore[reportPrivateUsage]
    assert findings.read_text(encoding="utf-8") == original
    assert not (tmp_path / "oos-dropped-direct.md").exists()


def test_prepare_pruned_ballot_missing_file_fails_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ctx = review_core_body.ReviewCoreBranchContext(
        commands=review_core_body.ReviewCommands("", "", "", "", "", "", "", "", ""),
        review_tmpdir=tmp_path,
        round_num=1,
        mode="diff",
        cursor_available="true",
        codex_available="true",
        session_env_path="",
        panel_manifest="",
        collector_results=tmp_path / "collector.env",
        not_substantive=0,
        panel_mode="normal",
        panel_shape="simple",
        scout_status="none",
        dynamic_slots="0",
        static_slot_count="0",
        run_id="",
        prune_ledger="",
        rows=[],
    )
    monkeypatch.setattr(review_core_body, "_prune_nits_for_ballot", lambda **_kwargs: object())

    result = review_core_body._prepare_pruned_ballot(ctx, findings_file=tmp_path / "missing.md")  # type: ignore[reportPrivateUsage]

    assert result is not None
    assert result.rc == 2
    assert result.status == ReviewCoreStatus.panel_failed
    assert ("THRESHOLD_REASON", "ballot-read-failed") in result.rows



def test_review_core_body_zero_findings_returns_ordered_rows(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=0, accepted=0, outdir_name="body-zero")
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == ReviewCoreStatus.zero_findings
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")
    assert keys.index("VOTING_TALLY_FILE") > keys.index("PANEL_SHAPE")


def test_review_core_body_fix_required_returns_duplicate_classification(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=1, accepted=1, outdir_name="body-fix")
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status == ReviewCoreStatus.fix_required
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.count("FINDINGS_CLASSIFICATION_TSV_FILE") == 2
    assert keys.index("VOTER_1_TOOL") < keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")


def _reviewer_collect_ledger(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, name: str) -> Path:
    # Point resolve_timing_ledger_path at a pre-created ledger through REVIEW_TMPDIR (its last
    # fallback key, and the only one with no other side effect in the review-core body), so the
    # test drives the real resolution the reviewers and aggregator use rather than a patched
    # binding. Clear the higher-priority keys so REVIEW_TMPDIR is the one that resolves.
    ledger_dir = tmp_path / name
    ledger_dir.mkdir()
    ledger = ledger_dir / "timing-ledger.tsv"
    _ = ledger.write_text("", encoding="utf-8")  # reviewers create this in prod; pre-create to pass the is_file gate
    for key in ("LARCH_TIMING_LEDGER", "LARCH_TIMING_SKILL", "IMPLEMENT_TMPDIR", "SESSION_ENV_PATH", "DESIGN_TMPDIR"):
        monkeypatch.delenv(key, raising=False)
    return ledger


def test_review_core_body_records_reviewer_collect_row(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # Issue #7179: on the aggregating path, the reviewers-to-aggregator window lands as a
    # reviewer-collect vendor row in the same timing ledger the reviewers and aggregator use, so
    # the Gantt shows it instead of a blank gap between the reviewer bars and the aggregator bar.
    ledger = _reviewer_collect_ledger(tmp_path, monkeypatch, name="timing-home")
    calls: list[dict[str, object]] = []

    def fake_record(_runner: object, **kwargs: object) -> bool:
        calls.append(kwargs)
        return True

    monkeypatch.setattr(dispatch_shared.rust_runtime, "timing_record_vendor_task", fake_record)

    result = _run_review_core_body_direct(
        tmp_path, monkeypatch, findings=1, accepted=1, outdir_name="body-collect",
        extra_env={"REVIEW_TMPDIR": str(ledger.parent)},
    )

    assert result.status == ReviewCoreStatus.fix_required
    assert len(calls) == 1
    call = calls[0]
    assert call["vendor"] == "claude"
    assert call["task_kind"] == "reviewer-collect"
    assert call["output"] == "reviewer-collect-round-1.out"
    assert call["skill"] == "implement"
    assert call["ledger"] == str(ledger)
    assert call["status"] == "complete"
    assert call["environment"] == {"IMPLEMENT_TMPDIR": str(ledger.parent)}
    assert isinstance(call["start_s"], float)
    assert isinstance(call["end_s"], float)


def test_review_core_body_skips_reviewer_collect_on_zero_findings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # The zero-findings path returns before the aggregator, so there is no reviewers-to-aggregator
    # gap to fill and no reviewer-collect row should be written (issue #7179).
    ledger = _reviewer_collect_ledger(tmp_path, monkeypatch, name="timing-home-zero")

    result = _run_review_core_body_direct(
        tmp_path, monkeypatch, findings=0, accepted=0, outdir_name="body-collect-zero",
        extra_env={"REVIEW_TMPDIR": str(ledger.parent)},
    )

    assert result.status == ReviewCoreStatus.zero_findings
    assert "reviewer-collect" not in ledger.read_text(encoding="utf-8")


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
    assert result.status == ReviewCoreStatus.zero_findings
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
    assert result.status == ReviewCoreStatus.panel_failed
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
    assert result.status == ReviewCoreStatus.prune_skipped
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
    assert result.status == ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert keys.index("REVIEW_CORE_STATUS") > keys.index("PANEL_PRUNED_EMPTY")


def test_review_core_body_threshold_failure_clears_public_oos_artifact(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-threshold-oos",
        extra_env={
            "TEST_COLLECTOR_VARIANT": "empty-with-oos",
            "TEST_THRESHOLD_OK": "false",
        },
    )

    assert result.rc == 2
    assert result.status == ReviewCoreStatus.panel_failed
    assert not (tmp_path / "body-threshold-oos" / "oos.md").read_text(encoding="utf-8").strip()


def test_review_core_body_proposer_map_failed_has_no_classification(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_proposer(*_args: object, **_kwargs: object) -> None:
        raise ValueError("proposer map failed")

    monkeypatch.setattr(review_core_body, "_write_proposer_sidecar_and_neutralize", fail_proposer)
    result = _run_review_core_body_direct(tmp_path, monkeypatch, findings=1, outdir_name="body-proposer-fail")
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == ReviewCoreStatus.panel_failed
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
    monkeypatch.setattr(review_core_body, "_write_proposer_sidecar_and_neutralize", fail_proposer)
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
    assert result.status == ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert "FINDINGS_CLASSIFICATION_TSV_FILE" not in keys
    assert "VOTER_1_TOOL" not in keys
    threshold_idx = keys.index("THRESHOLD_REASON")
    assert result.rows[threshold_idx] == ("THRESHOLD_REASON", "proposer-map-failed")


def test_review_core_body_validation_exhausted_tally_fail_has_voter_rows(
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
    assert result.status == ReviewCoreStatus.panel_failed
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert "VOTER_1_TOOL" in keys
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
    assert result.status == ReviewCoreStatus.aggregator_validation_exhausted
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
    assert result.status == ReviewCoreStatus.ok
    assert keys[:3] == ["SCOUT_STATUS", "DYNAMIC_SLOTS", "PANEL_PRUNED_EMPTY"]
    assert "VOTER_1_TOOL" in keys
    assert keys.index("VOTER_1_TOOL") < keys.index("FINDINGS_CLASSIFICATION_TSV_FILE") < keys.index("REVIEW_CORE_STATUS")


def _all_oos_collect_stub_body() -> str:
    return """#!/usr/bin/env bash
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
"""


def test_review_core_body_all_oos_dispatches_voters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = tmp_path / "collect-oos-findings.sh"
    _write_executable(collect, _all_oos_collect_stub_body())
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
        outdir_name="body-all-oos",
        extra_env={
            "REVIEW_CORE_COLLECT_FINDINGS_SH": str(collect),
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(aggregate),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status in {ReviewCoreStatus.ok, ReviewCoreStatus.fix_required}
    assert "VOTER_1_TOOL" in keys
    audit = tmp_path / "body-all-oos" / "oos-dropped-before-vote.md"
    assert not audit.exists()


def test_review_core_body_all_oos_validation_exhausted_dispatches_voters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = tmp_path / "collect-oos-findings.sh"
    _write_executable(collect, _all_oos_collect_stub_body())
    stubs = _write_review_core_stubs(tmp_path / "body-all-oos-agg-exhaust-stubs")
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-all-oos-agg-exhaust",
        extra_env={
            "REVIEW_CORE_COLLECT_FINDINGS_SH": str(collect),
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_exhausted"]),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 2
    assert result.status == ReviewCoreStatus.aggregator_validation_exhausted
    assert "VOTER_1_TOOL" in keys
    assert not (tmp_path / "body-all-oos-agg-exhaust" / "oos-dropped-before-vote.md").exists()


def test_review_core_body_all_oos_empty_merge_dispatches_voters(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collect = tmp_path / "collect-oos-findings.sh"
    _write_executable(collect, _all_oos_collect_stub_body())
    stubs = _write_review_core_stubs(tmp_path / "body-all-oos-agg-zero-stubs")
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        outdir_name="body-all-oos-agg-zero",
        extra_env={
            "REVIEW_CORE_COLLECT_FINDINGS_SH": str(collect),
            "REVIEW_CORE_AGGREGATE_FINDINGS_SH": str(stubs["aggregate_zero"]),
        },
    )
    keys = _review_core_row_keys(result)

    assert result.rc == 0
    assert result.status in {ReviewCoreStatus.ok, ReviewCoreStatus.fix_required}
    assert "VOTER_1_TOOL" in keys
    assert not (tmp_path / "body-all-oos-agg-zero" / "oos-dropped-before-vote.md").exists()


def test_review_core_body_cap_reached_round_two(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    result = _run_review_core_body_direct(
        tmp_path,
        monkeypatch,
        findings=1,
        accepted=1,
        round_num=2,
        outdir_name="body-cap-reached",
    )

    assert result.rc == 0
    assert result.status == ReviewCoreStatus.cap_reached
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
    assert result.status == ReviewCoreStatus.main_agent_vote_required
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
    assert result.status == ReviewCoreStatus.panel_failed
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

        monkeypatch.setattr(review_core_body, "_write_proposer_sidecar_and_neutralize", fail_proposer)
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


def test_review_core_default_dispatches_voters_through_the_bootstrap() -> None:
    assert rts.review_core_uses_agent_dispatch_voters_by_default()




def test_review_commands_route_through_verified_rust_entrypoints(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[tuple[str, list[str]]] = []

    def fake_larch(
        args: Sequence[str], *, runner: proc.Runner | None = None, env: Mapping[str, str] | None = None
    ) -> proc.CommandResult:
        del runner, env
        calls.append(("rust", list(args)))
        return proc.CommandResult(tuple(args), 0, "MODE=diff\n", "", 0.0)

    def fake_python(
        args: Sequence[str], *, runner: proc.Runner | None = None, env: Mapping[str, str] | None = None
    ) -> proc.CommandResult:
        del runner, env
        calls.append(("python", list(args)))
        return proc.CommandResult(tuple(args), 0, "", "", 0.0)

    monkeypatch.setattr(review_pipeline_shared, "run_larch", fake_larch)
    monkeypatch.setattr(review_pipeline_shared, "_run_python_cli", fake_python)

    gathered = review_pipeline_shared._call_review_command(  # pyright: ignore[reportPrivateUsage]  # tests the migration dispatch seam
        name="gather-context", args=["--mode", "diff"]
    )
    dispatched = review_pipeline_shared._call_review_command(  # pyright: ignore[reportPrivateUsage]  # tests the migration dispatch seam
        name="dispatch-panel", args=["--mode", "diff"]
    )
    collected = review_pipeline_shared._call_review_command(  # pyright: ignore[reportPrivateUsage]  # tests the migration dispatch seam
        name="collect-findings", args=[]
    )
    threshold = review_pipeline_shared._call_review_command(  # pyright: ignore[reportPrivateUsage]  # tests the migration dispatch seam
        name="check-reviewer-failure-threshold", args=[]
    )
    _ = review_pipeline_shared._call_review_command(  # pyright: ignore[reportPrivateUsage]  # proves remaining verbs retain their Python owner
        name="core", args=[]
    )

    assert gathered.stdout == "MODE=diff\n"
    assert dispatched.stdout == "MODE=diff\n"
    assert collected.stdout == "MODE=diff\n"
    assert threshold.stdout == "MODE=diff\n"
    assert calls == [
        ("rust", ["review", "gather-context", "--mode", "diff"]),
        ("rust", ["review", "dispatch-panel", "--mode", "diff"]),
        ("rust", ["review", "collect-findings"]),
        ("rust", ["review", "check-reviewer-failure-threshold"]),
        ("python", ["review", "core"]),
    ]


def test_static_coverage_reason_excuses_straggler_dropped_static_slot(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    arch = tmp_path / "codex-specialist-arch-output.txt"
    _ = arch.write_text("review\n", encoding="utf-8")
    _ = collector.write_text(f"REVIEWER_FILE={arch}\nSTATUS=OK\n\n", encoding="utf-8")
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        panel_manifest_ndjson(
            [
                panel_manifest_row("arch", "codex", arch, agent="agents/reviewer-arch.md"),
                panel_manifest_row(
                    "testing",
                    "cursor",
                    tmp_path / "cursor-specialist-testing-output.txt",
                    agent="agents/reviewer-testing.md",
                ),
            ]
        ),
        encoding="utf-8",
    )
    dropped = tmp_path / "dropped.tsv"
    _ = dropped.write_text("testing\tcursor\tstraggler-dropped\tcut\n", encoding="utf-8")

    assert (
        review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
            collector=collector,
            manifest=manifest,
            outputs=[str(arch)],
            dropped_slots_file=str(dropped)
        )
        == ""
    )


def test_static_coverage_reason_excuses_tool_absent_static_slot(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    arch = tmp_path / "codex-specialist-arch-output.txt"
    testing = tmp_path / "cursor-specialist-testing-output.txt"
    _ = arch.write_text("review\n", encoding="utf-8")
    _ = testing.write_text("review\n", encoding="utf-8")
    _ = collector.write_text(
        f"REVIEWER_FILE={arch}\nSTATUS=OK\n\n"
        f"REVIEWER_FILE={testing}\nSTATUS=OK\n\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        panel_manifest_ndjson(
            [
                panel_manifest_row("arch", "codex", arch, agent="agents/reviewer-arch.md"),
                panel_manifest_row(
                    "testing", "cursor", testing, agent="agents/reviewer-testing.md"
                ),
                panel_manifest_row(
                    "testing",
                    "codex",
                    tmp_path / "codex-specialist-testing-output.txt",
                    agent="agents/reviewer-testing.md",
                ),
            ]
        ),
        encoding="utf-8",
    )
    dropped = tmp_path / "dropped.tsv"
    _ = dropped.write_text("testing\tcodex\ttool-absent\tprimary tool codex not present\n", encoding="utf-8")

    assert (
        review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
            collector=collector,
            manifest=manifest,
            outputs=[str(arch), str(testing)],
            dropped_slots_file=str(dropped)
        )
        == ""
    )


def test_static_coverage_reason_accepts_all_not_substantive_static_slot(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    correctness = tmp_path / "codex-specialist-correctness-output.txt"
    _ = correctness.write_text("STATUS=NOT_SUBSTANTIVE\n", encoding="utf-8")
    _ = collector.write_text(
        f"REVIEWER_FILE={correctness}\n"
        "TOOL=codex\n"
        "STATUS=NOT_SUBSTANTIVE\n"
        "EXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        json.dumps(
            {
                "slot": "correctness",
                "tool": "codex",
                "output": str(correctness),
                "agent": "agents/reviewer-correctness.md",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    assert (
        review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
            collector=collector,
            manifest=manifest,
            outputs=[str(correctness)],
        )
        == ""
    )


def test_static_coverage_reason_rejects_mixed_not_substantive_and_failure(tmp_path: Path) -> None:
    collector = tmp_path / "collector-results.env"
    failed_codex = tmp_path / "codex-specialist-correctness-output.txt"
    thin_cursor = tmp_path / "cursor-specialist-correctness-output.txt"
    _ = failed_codex.write_text("ERROR\n", encoding="utf-8")
    _ = thin_cursor.write_text("STATUS=NOT_SUBSTANTIVE\n", encoding="utf-8")
    _ = collector.write_text(
        f"REVIEWER_FILE={failed_codex}\n"
        "TOOL=codex\n"
        "STATUS=ERROR\n"
        "EXIT_CODE=1\n\n"
        f"REVIEWER_FILE={thin_cursor}\n"
        "TOOL=cursor\n"
        "STATUS=NOT_SUBSTANTIVE\n"
        "EXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.ndjson"
    _ = manifest.write_text(
        "\n".join(
            [
                json.dumps(
                    {
                        "slot": "correctness",
                        "tool": "codex",
                        "output": str(failed_codex),
                        "agent": "agents/reviewer-correctness.md",
                    }
                ),
                json.dumps(
                    {
                        "slot": "correctness",
                        "tool": "cursor",
                        "output": str(thin_cursor),
                        "agent": "agents/reviewer-correctness.md",
                    }
                ),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    reason = review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
        collector=collector,
        manifest=manifest,
        outputs=[str(failed_codex), str(thin_cursor)],
    )
    assert reason == "no successful static reviewer for archetype(s): correctness"


def test_static_coverage_reason_does_not_excuse_tool_absent_when_surviving_vendor_failed(tmp_path: Path) -> None:
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
        "testing\tcodex\ttool-absent\tprimary tool codex not present\n"
        "testing\tcursor\tcollector-failure\tSTATUS=ERROR\n",
        encoding="utf-8",
    )

    reason = review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
        collector=collector,
        manifest=manifest,
        outputs=[str(arch)],
        dropped_slots_file=str(dropped)
    )
    assert reason == "no successful static reviewer for archetype(s): testing"


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

    reason = review_core_body._static_coverage_reason(  # pyright: ignore[reportPrivateUsage]
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




def test_review_core_default_prune_nits_uses_review_cli() -> None:
    text = REVIEW_CORE_BODY.read_text(encoding="utf-8")
    retired_prune = "/".join(("skills", "review", "scripts", "prune-nit-findings.sh"))  # noqa: FLY002
    assert retired_prune not in text
    assert "command=commands.prune_nits" in text
    assert 'review_name="prune-nit-findings"' in text
    assert '"--input-mode"' not in text


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


def test_review_core_cap_reached_round_2_with_accepted_findings(tmp_path: Path) -> None:
    result = _run_review_core(tmp_path, round_num=2, findings=1, accepted=1)

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
    assert "THRESHOLD_OK=false" in threshold_env
    assert "THRESHOLD_REASON=no successful launched reviewer output" in threshold_env
    assert "THRESHOLD_REASON=no successful launched reviewer output" in result.stdout


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
    assert "THRESHOLD_REASON=no successful static reviewer for archetype(s): testing" in result.stdout


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
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1\ttrue")


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
    assert lines[1].endswith("Cursor-Pragmatic\t1\t1\t0\t1\ttrue")
    assert lines[2].endswith("Codex-Arch\t1\t1\t0\t1\ttrue")


def test_ensure_reviewer_prune_ledger_preserves_good_rows_and_drops_malformed(tmp_path: Path) -> None:
    ledger = tmp_path / "ledger.tsv"
    legacy_header = "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count"
    current_header = "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count\tobserved"
    ledger.write_text(
        legacy_header
        + "\n"
        + "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "bad\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n"
        + "2\tcodex\tarch\tCodex-Arch\t0\t1\t1\textra\n",
        encoding="utf-8",
    )

    manifest = tmp_path / "empty.ndjson"
    classification = tmp_path / "classification.tsv"
    manifest.write_text("", encoding="utf-8")
    classification.write_text("finding_id\treviewer_slots\tvoting_result\n", encoding="utf-8")
    result = run_review(
        "reviewer-prune", "record",
        "--ledger", str(ledger),
        "--round", "3",
        "--manifest", str(manifest),
        "--classification", str(classification),
    )
    assert result.returncode == 0, result.stderr

    assert ledger.read_text(encoding="utf-8").splitlines() == [
        current_header,
        "1\tcursor\tcorrectness\tCursor-Correctness\t1\t1\t0\t1\ttrue",
    ]


def test_review_core_main_agent_vote_required_skips_prune_ledger_and_round_two_uses_round_one(tmp_path: Path) -> None:
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
        if round_num == 1:
            manifest = outdir / "panel-manifest.ndjson"

    assert manifest is not None
    ledger_lines = ledger.read_text(encoding="utf-8").splitlines()
    assert len(ledger_lines) == 2
    assert ledger_lines[1].startswith("1\t")
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


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


def test_reviewer_prune_record_and_filter_round_two(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text(
        '{"slot":"correctness","tool":"cursor","output":"/tmp/cursor-specialist-correctness-output.txt"}\n',
        encoding="utf-8",
    )
    classification = tmp_path / "class.tsv"
    classification.write_text("finding_id\treviewer_slots\tvoting_result\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    for round_num in (1,):
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
    assert ledger_lines[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count\tobserved"
    assert ledger_lines[1].endswith("\t0\t0\t0\t0\ttrue")
    out = tmp_path / "filtered.ndjson"
    result = run_review(
        "reviewer-prune",
        "filter",
        "--ledger",
        str(ledger),
        "--round",
        "2",
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


def test_reviewer_prune_filter_round_one_never_prunes(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["rejected"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 1)

    assert result.returncode == 0, result.stderr
    assert "PRUNE_ACTIVE=true" in result.stdout
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_round_two_prunes_no_accepted_history(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["rejected"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_round_two_prunes_no_history(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text(
        "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count\tobserved\n",
        encoding="utf-8",
    )

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_prunes_noisy_one_accept_combo(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted", "rejected"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_prunes_low_precision_positive_net(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted", "neutral", "neutral"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_keeps_high_severity_code_review_on_weighted_net(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    _write_code_review_prune_classification(round_one, [_code_review_prune_row("FINDING_1", "accepted", severity="major")])

    _record_prune_classification(ledger, manifest, round_one, 1)
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t2\t0\t1\ttrue")
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_keeps_low_severity_code_review_positive_net(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    _write_code_review_prune_classification(round_one, [_code_review_prune_row("FINDING_1", "accepted", severity="minor")])

    _record_prune_classification(ledger, manifest, round_one, 1)
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1\ttrue")
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_record_bare_classification_tokens_populate_counts(tmp_path: Path) -> None:
    # Issue #5733 regression: bare classification tokens joined against the
    # suffixed manifest output label must populate non-zero counts (previously
    # the join missed and the round-1 ledger was all-zero).
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    classification = tmp_path / "class.tsv"
    classification.write_text(
        "finding_id\treviewer_slots\tvoting_result\n"
        "FINDING_1\tcursor-specialist-correctness\taccepted\n"
        "FINDING_2\tcursor-specialist-correctness\taccepted\n"
        "FINDING_3\tcursor-specialist-correctness\trejected\n",
        encoding="utf-8",
    )
    ledger = tmp_path / "ledger.tsv"
    _record_prune_classification(ledger, manifest, classification, 1)

    row = ledger.read_text(encoding="utf-8").splitlines()[1]
    assert not row.endswith("\t0\t0\t0\t0")
    assert row.endswith("\t2\t2\t1\t3\ttrue")


def test_reviewer_prune_filter_round_two_keeps_productive_bare_token_panel(tmp_path: Path) -> None:
    # Issue #5733: a productive round-1 panel attributed with bare classification
    # tokens must survive the round-2 prune instead of being wiped empty.
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    productive = _code_review_prune_row("FINDING_1", "accepted", severity="major")
    productive["reviewer_slots"] = "cursor-specialist-correctness"
    _write_code_review_prune_classification(round_one, [productive])

    _record_prune_classification(ledger, manifest, round_one, 1)
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t2\t0\t1\ttrue")

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_record_code_review_without_scope_stays_unweighted(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    classification = tmp_path / "class.tsv"
    header = [col for col in voting.code_review_classification_header().split("\t") if col != "scope"]
    _write_prune_classification_rows(classification, header, [_code_review_prune_row("FINDING_1", "accepted", severity="major")])

    _record_prune_classification(ledger, manifest, classification, 1)

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t1\t0\t1\ttrue")


def test_reviewer_prune_record_plan_mode_weights_high_voter_severity(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text('{"slot":"cursor-plan-arch","tool":"cursor","output":"/tmp/cursor-arch-output.txt"}\n', encoding="utf-8")
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text("cursor-plan-arch\tCursor-Arch\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    classification = tmp_path / "class.tsv"
    _write_plan_prune_classification(classification, [_plan_prune_row("FINDING_1", "accepted", severity="major")])

    _record_prune_classification(ledger, manifest, classification, 1, label_map=label_map)

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("Cursor-Arch\t1\t2\t0\t1\ttrue")


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

    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("Cursor-Arch\t1\t1\t0\t1\ttrue")


def test_reviewer_prune_filter_floor_uses_unweighted_accepted_with_high_severity(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    round_one = tmp_path / "class-1.tsv"
    _write_code_review_prune_classification(
        round_one,
        [
            _code_review_prune_row("FINDING_1", "accepted", severity="major"),
            *(_code_review_prune_row(f"FINDING_{idx}", "neutral") for idx in range(2, 5)),
        ],
    )

    _record_prune_classification(ledger, manifest, round_one, 1)
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t1\t2\t0\t4\ttrue")
    assert "PRUNED_COUNT=1" in result.stdout
    assert "PANEL_PRUNED_EMPTY=true" in result.stdout


def test_reviewer_prune_filter_keeps_two_accepted_findings_despite_low_rate(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(
        tmp_path,
        [["accepted", "accepted", "neutral", "neutral", "neutral"]],
    )

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_keeps_skipped_plan_reviewer_without_observation(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    manifest.write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"/tmp/cursor-arch-output.txt"}\n',
        encoding="utf-8",
    )
    label_map = tmp_path / "label-map.tsv"
    label_map.write_text("cursor-plan-arch\tCursor-Arch\n", encoding="utf-8")
    reviewer_status = tmp_path / "reviewer-status.tsv"
    reviewer_status.write_text("slot\tstatus\telapsed\nCursor-Arch\tskipped\t\n", encoding="utf-8")
    classification = tmp_path / "class.tsv"
    _write_plan_prune_classification(classification, [])
    ledger = tmp_path / "ledger.tsv"

    record = run_review(
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
        "--reviewer-status",
        str(reviewer_status),
    )
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert record.returncode == 0, record.stderr
    assert ledger.read_text(encoding="utf-8").splitlines()[1].endswith("\t0\t0\t0\t0\tfalse")
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_accepts_legacy_ledger_rows(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    _write_single_prune_manifest(manifest)
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text(
        "round\ttool\tslot\tlabel\taccepted_count\trejected_count\ttotal_count\n"
        "1\tcursor\tcorrectness\tCursor-Correctness\t1\t0\t1\n",
        encoding="utf-8",
    )

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_keeps_exact_acceptance_floor(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted", "neutral"]])

    result = _filter_prune_round(tmp_path, manifest, ledger, 2)

    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=0" in result.stdout
    assert "PANEL_PRUNED_EMPTY=false" in result.stdout


def test_reviewer_prune_filter_round_two_active_and_off_override(tmp_path: Path) -> None:
    manifest, ledger = _record_prune_rounds(tmp_path, [["accepted", "rejected"]])

    round_one = _filter_prune_round(tmp_path, manifest, ledger, 1)
    round_two = _filter_prune_round(tmp_path, manifest, ledger, 2)
    disabled = _filter_prune_round(tmp_path, manifest, ledger, 2, env={"LARCH_REVIEWER_PRUNE": "off"})

    assert round_one.returncode == 0, round_one.stderr
    assert "PRUNED_COUNT=0" in round_one.stdout
    assert round_two.returncode == 0, round_two.stderr
    assert "PRUNED_COUNT=1" in round_two.stdout
    assert disabled.returncode == 0, disabled.stderr
    assert "PRUNE_ACTIVE=false" in disabled.stdout
    assert "PRUNED_COUNT=0" in disabled.stdout


def test_review_core_zero_findings_records_prune_ledger(tmp_path: Path) -> None:
    stubs = _write_review_core_stubs(tmp_path / "zero-prune-stubs")
    ledger = tmp_path / "reviewer-prune-ledger.tsv"
    manifest = tmp_path / "zero-prune-1" / "panel-manifest.ndjson"
    for round_num in (1,):
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

    assert ledger.read_text(encoding="utf-8").splitlines()[0] == "round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count\tobserved"
    result = _filter_prune_round(tmp_path, manifest, ledger, 2)
    assert result.returncode == 0, result.stderr
    assert "PRUNED_COUNT=1" in result.stdout

















































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
    review_core_body._write_proposer_sidecar_and_neutralize(ballot_file=findings, proposer_map=sidecar)  # pyright: ignore[reportPrivateUsage]
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


def test_apply_findings_with_coder_logs_panel_prompt_size(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    findings = tmp_path / "accepted-findings.md"
    findings.write_text(
        """### FINDING_1: Fix bug
- **Concern**: bug
- **Suggested revision**: fix it
""",
        encoding="utf-8",
    )
    round_dir = tmp_path / "round-5"
    result_file = round_dir / "coder.env"
    monkeypatch.setattr(coder_runner, "_submodule_paths", list)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(
        coder_runner,
        "_prepare_or_validate_pre_coder_snapshot",
        lambda target: snapshot.ValidatedPreCoderSnapshot(
            mode="head_untracked", root=snapshot.pre_coder_snapshot_dir(target), pre_head=""
        ),
    )  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(coder_runner, "_git_head", lambda: "")  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(coder_runner, "revalidate_pre_coder_snapshot", lambda *_a, **_k: None)  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(coder_runner, "_record_main_agent_required_vendor_task", lambda _round_dir: round_dir / "main.log")  # pyright: ignore[reportPrivateUsage]
    monkeypatch.setattr(coder_runner.external_defaults, "tool_order", lambda _role: [])
    wrong_artifact_dir = tmp_path / "wrong-panel-dir"
    monkeypatch.setenv("LARCH_PANEL_ARTIFACT_DIR", str(wrong_artifact_dir))

    result = coder_runner.apply_findings_with_coder(input_file=findings, round_dir=round_dir, result_file=result_file, round_num=5)

    assert result.status == "main-agent-required"
    tsv = round_dir / "panel-prompt-sizes.tsv"
    assert tsv.is_file()
    assert not (wrong_artifact_dir / "panel-prompt-sizes.tsv").exists()
    text = tsv.read_text(encoding="utf-8")
    assert "implementer" in text
    assert "# Review Fix Application" not in text
# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false








def test_review_core_tier_cap_controls_fix_required(tmp_path: Path) -> None:
    round2 = _run_review_core(tmp_path, round_num=2, findings=1, accepted=1, extra_env={"LARCH_QUIET_DISABLE": "1"})
    assert "REVIEW_CORE_STATUS=cap-reached" in round2.stdout
    hard = run_review(
        "core",
        "--mode", "diff",
        "--output-dir", str(tmp_path / "hard-core2"),
        "--codex-available", "true",
        "--cursor-available", "true",
        "--tier", "HARD",
        "--round-num", "2",
        env=rts.build_review_core_env(
            _stub_dir=tmp_path / "hard-stubs",
            stubs=_write_review_core_stubs(tmp_path / "hard-stubs"),
            TEST_FINDINGS="1",
            TEST_ACCEPTED="1",
            TEST_ROUND_NUM="2",
        ),
    )
    assert "REVIEW_CORE_STATUS=cap-reached" in hard.stdout
    assert "EFFECTIVE_ROUND_CAP=2" in hard.stdout




def test_prune_keeps_prune_exempt_rows_without_history(tmp_path: Path) -> None:
    manifest = tmp_path / "panel.ndjson"
    exempt = {"slot": "plan-fidelity-forced", "tool": "codex", "output": str(tmp_path / "pf.txt"), "prune_exempt": True}
    ordinary = {"slot": "correctness", "tool": "codex", "output": str(tmp_path / "c.txt")}
    manifest.write_text(json.dumps(exempt) + "\n" + json.dumps(ordinary) + "\n", encoding="utf-8")
    ledger = tmp_path / "ledger.tsv"
    ledger.write_text("round\ttool\tslot\tlabel\taccepted_count\tweighted_accepted_count\trejected_count\ttotal_count\n", encoding="utf-8")
    out = tmp_path / "out.ndjson"

    result = run_review(
        "reviewer-prune", "filter",
        "--ledger", str(ledger),
        "--round", "2",
        "--manifest", str(manifest),
        "--out", str(out),
    )

    rows = _panel_manifest_rows(out)
    assert result.returncode == 0, result.stderr
    assert "PRUNE_ACTIVE=true" in result.stdout
    assert [row["slot"] for row in rows] == ["plan-fidelity-forced"]
