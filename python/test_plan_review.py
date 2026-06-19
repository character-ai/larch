from __future__ import annotations

import contextlib
import io
from pathlib import Path

import plan_review
import plan_review_round
import pytest
import voting
from test_support import ROOT, run_cli


def test_legacy_assets_removed_from_plan_review_module() -> None:
    assert not hasattr(plan_review, "_LEGACY_ASSETS")
    assert not hasattr(plan_review, "run_legacy_script")


def test_step3_loop_persist_envelope_merges_and_strips_reason(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "TALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nPLAN_REVIEW_CONTINUE_REASON=again\r\n",
        encoding="utf-8",
    )
    plan_review.step3_loop_persist_envelope(
        tmp_path,
        "main-agent-vote-required",
        2,
        2,
        2,
        values={"ACCEPTED_COUNT": "1"},
    )
    text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "LOOP_STATUS=main-agent-vote-required" in text
    assert "TALLY_PLAN_REVIEW_STATUS=ok" in text
    assert "PLAN_REVIEW_CONTINUE_REASON=again" in text


def test_step3_loop_persist_envelope_persists_and_emits_degraded_panel_warning(tmp_path: Path) -> None:
    values = {
        "LOOP_STATUS": "complete",
        "DEGRADED_PANEL_WARNING": "**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**",
    }
    plan_review.step3_loop_persist_envelope(tmp_path, "complete", 1, 1, 1, values=values)
    text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in text

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        plan_review.step3_loop_emit_envelope(tmp_path, "complete", 1, 1, 1, values)

    assert "DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in out.getvalue()


def test_step3_loop_persist_envelope_persists_and_emits_invalid_slot_panel_warning(tmp_path: Path) -> None:
    values = {
        "LOOP_STATUS": "complete",
        "INVALID_SLOT_PANEL_WARNING": "**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**",
    }
    plan_review.step3_loop_persist_envelope(tmp_path, "complete", 1, 1, 1, values=values)
    text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "INVALID_SLOT_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in text

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        plan_review.step3_loop_emit_envelope(tmp_path, "complete", 1, 1, 1, values)

    assert "INVALID_SLOT_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in out.getvalue()


def test_step3_loop_persist_envelope_writes_terminal_sentinels(tmp_path: Path) -> None:
    # #4688 hook-release contract: persisting the result env writes the
    # step-3-terminal sentinel pair so hook-bg-poll-guard.sh releases the marker.
    plan_review.step3_loop_persist_envelope(tmp_path, "complete", 1, 1, 1, values={})
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert (tmp_path / ".step3-terminal-persisted-this-run").is_file()


def test_step3_loop_persist_envelope_terminal_without_step3_on_midloop_bail(tmp_path: Path) -> None:
    # Mid-loop bail-outs write step-3-terminal (hook release) but not step-3
    # (the pause / Gate B milestone), per the split-sentinel contract.
    plan_review.step3_loop_persist_envelope(tmp_path, "main-agent-apply-required", 2, 2, 2, values={})
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert (tmp_path / ".step3-terminal-persisted-this-run").is_file()
    assert not (tmp_path / ".completed" / "step-3").exists()


def test_phase_driver_write_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / ".step3-review-result.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="symlink"):
        plan_review.step3_loop_persist_envelope(tmp_path, "complete", 1, 1, 1, values={})


def test_emit_plan_persists_diff_lines(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("## Plan\n\ndiff_lines: 42\n", encoding="utf-8")
    proc = run_cli("plan-review", "emit", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "EMIT_PLAN_STATUS=ok" in proc.stdout
    assert (tmp_path / "diff-lines.txt").read_text(encoding="utf-8") == "42\n"


def test_emit_plan_missing_diff_lines_fails(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("## Plan\n", encoding="utf-8")
    proc = run_cli("plan-review", "emit", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 1
    assert "EMIT_PLAN_STATUS=missing-diff-lines" in proc.stdout


def test_finalize_plan_creates_empty_artifacts_and_rejects_symlink(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("plan\n", encoding="utf-8")
    _ = (tmp_path / "diff-lines.txt").write_text("1\n", encoding="utf-8")
    proc = run_cli("plan-review", "finalize", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "FINALIZE_PLAN_STATUS=ok" in proc.stdout
    assert (tmp_path / "voting-tally.md").exists()

    (tmp_path / "voting-tally.md").unlink()
    _ = (tmp_path / "target").write_text("x", encoding="utf-8")
    (tmp_path / "voting-tally.md").symlink_to(tmp_path / "target")
    proc = run_cli("plan-review", "finalize", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 1
    assert "FINALIZE_PLAN_STATUS=invalid-artifact" in proc.stdout


def test_preview_large_plan_threshold_and_header(tmp_path: Path) -> None:
    body = "# Title\n" + "\n".join(f"## Section {i}" for i in range(3)) + "\n"
    _ = (tmp_path / "plan.txt").write_text(body, encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "preview",
        "--design-tmpdir",
        str(tmp_path),
        "--variant",
        "step3",
        env={"LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD": "1"},
    )
    assert proc.returncode == 0
    assert "## Plan Candidate for Review" in proc.stdout
    assert "The plan is very large" in proc.stdout


def test_step3_state_non_numeric_round_count_falls_back_to_zero(tmp_path: Path) -> None:
    (tmp_path / ".step3-reentry").touch()
    _ = (tmp_path / "review-round-count.txt").write_text("not-a-number\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "step3-state",
        "--design-tmpdir",
        str(tmp_path),
        "--direct-review-entry",
    )
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=direct-review-entry" in proc.stdout


def _seed_step3_downstream(tmp_path: Path) -> None:
    completed = tmp_path / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    for name in ("step-3", "step-3.5", "step-3-terminal", "step-3b", "step-4", "step-4b"):
        (completed / name).touch()
    (tmp_path / ".step3-terminal-persisted-this-run").touch()
    (tmp_path / ".gate-b-postapply-ready-1").touch()
    (tmp_path / ".gate-b-postapply-ready-2").touch()


def test_step3_state_direct_review_entry_noop_without_reentry(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--direct-review-entry")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=noop" in proc.stdout
    assert "REVIEW_ROUND_COUNT=0" in proc.stdout
    # No .step3-reentry breadcrumb -> nothing cleared.
    assert (tmp_path / ".completed" / "step-3").is_file()
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert (tmp_path / ".gate-b-postapply-ready-1").is_file()


def test_step3_state_direct_review_entry_clears_restores_and_consumes(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    (tmp_path / ".step3-reentry").touch()
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    # Settled round artifacts (<= round 2) plus a future round 3 that must survive.
    for n in (1, 2, 3):
        _ = (tmp_path / f".step3-round-{n}.phase").write_text("done\n", encoding="utf-8")
        _ = (tmp_path / f"plan-pre-apply-round-{n}.txt").write_text("x\n", encoding="utf-8")
    for name in (
        "accepted-plan-findings-all.md",
        ".accepted-plan-findings-all.prev.md",
        "oos-accepted-design.md",
        ".oos-accepted-design.prev.md",
    ):
        _ = (tmp_path / name).write_text("x\n", encoding="utf-8")
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--direct-review-entry")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=direct-review-entry" in proc.stdout
    assert "REVIEW_ROUND_COUNT=2" in proc.stdout
    # Downstream sentinels cleared.
    for name in ("step-3", "step-3.5", "step-3-terminal", "step-3b", "step-4", "step-4b"):
        assert not (tmp_path / ".completed" / name).exists()
    assert not (tmp_path / ".step3-terminal-persisted-this-run").exists()
    assert not (tmp_path / ".gate-b-postapply-ready-1").exists()
    assert not (tmp_path / ".gate-b-postapply-ready-2").exists()
    # Upstream package restored.
    for name in ("step-1e", "step-2a", "step-2b", "step-2b.5"):
        assert (tmp_path / ".completed" / name).is_file()
    # Settled rounds (<= 2) dropped, future round 3 preserved.
    assert not (tmp_path / ".step3-round-1.phase").exists()
    assert not (tmp_path / ".step3-round-2.phase").exists()
    assert not (tmp_path / "plan-pre-apply-round-2.txt").exists()
    assert (tmp_path / ".step3-round-3.phase").is_file()
    assert (tmp_path / "plan-pre-apply-round-3.txt").is_file()
    # Accumulated artifacts and the re-entry breadcrumb consumed.
    assert not (tmp_path / "accepted-plan-findings-all.md").exists()
    assert not (tmp_path / "oos-accepted-design.md").exists()
    assert not (tmp_path / ".step3-reentry").exists()


def test_step3_state_pause_hygiene_clears_but_preserves_findings_and_reentry(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    (tmp_path / ".step3-reentry").touch()
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-1.phase").write_text("done\n", encoding="utf-8")
    _ = (tmp_path / "accepted-plan-findings-all.md").write_text("x\n", encoding="utf-8")
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--direct-review-pause-hygiene")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=direct-review-pause-hygiene" in proc.stdout
    # Clears downstream and restores upstream, same as direct-review-entry.
    assert not (tmp_path / ".completed" / "step-3").exists()
    assert not (tmp_path / ".step3-terminal-persisted-this-run").exists()
    for name in ("step-1e", "step-2a", "step-2b", "step-2b.5"):
        assert (tmp_path / ".completed" / name).is_file()
    # But does NOT settle rounds, drop findings, or consume the breadcrumb.
    assert (tmp_path / ".step3-round-1.phase").is_file()
    assert (tmp_path / "accepted-plan-findings-all.md").is_file()
    assert (tmp_path / ".step3-reentry").is_file()


def test_step3_state_pause_hygiene_noop_without_reentry(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--direct-review-pause-hygiene")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=noop" in proc.stdout
    assert (tmp_path / ".completed" / "step-3").is_file()


def test_step3_state_auto_continuation_clears_without_restore(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-1.phase").write_text("done\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-2.phase").write_text("pending\n", encoding="utf-8")
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--auto-continuation-entry")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=auto-continuation-entry" in proc.stdout
    assert "REVIEW_ROUND_COUNT=1" in proc.stdout
    # Downstream cleared unconditionally (no .step3-reentry gate).
    for name in ("step-3", "step-3.5", "step-3-terminal", "step-3b", "step-4", "step-4b"):
        assert not (tmp_path / ".completed" / name).exists()
    assert not (tmp_path / ".gate-b-postapply-ready-1").exists()
    # Settled round 1 dropped, future round 2 preserved.
    assert not (tmp_path / ".step3-round-1.phase").exists()
    assert (tmp_path / ".step3-round-2.phase").is_file()
    # Upstream package NOT restored by auto-continuation.
    assert not (tmp_path / ".completed" / "step-2a").exists()


def test_round_artifact_allowlist_and_drift_baseline(tmp_path: Path) -> None:
    assert plan_review.round_artifact_included("round-summary.env")
    assert not plan_review.round_artifact_included("debug.txt")
    assert plan_review.round_revise_artifact_excluded("codex-output.txt")
    assert plan_review.round_revise_artifact_excluded("cursor-output.txt.token-record")
    assert plan_review.round_revise_artifact_excluded("codex-output.txt.stderr-tail")
    assert plan_review.drift_baseline_write_once(tmp_path, "10", "20") == 0
    assert (tmp_path / "drift-baseline.env").read_text(encoding="utf-8") == (
        "BASELINE_PLAN_LINES=10\nBASELINE_DIFF_LINES=20\n"
    )
    assert plan_review.drift_baseline_write_once(tmp_path, "99", "99") == 0
    assert "99" not in (tmp_path / "drift-baseline.env").read_text(encoding="utf-8")


def test_record_report_evidence_writes_escalation_ledger(tmp_path: Path) -> None:
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--record-report-evidence",
        "tally-error",
    )
    assert proc.returncode == 0, proc.stderr
    ledger = tmp_path / "design-failure-escalation-ledger.tsv"
    assert ledger.exists()
    text = ledger.read_text(encoding="utf-8")
    assert "trigger=tally-error" in text
    assert "phase=validation" in text


def test_record_report_evidence_requires_design_tmpdir() -> None:
    proc = run_cli(
        "plan-review",
        "run",
        "--record-report-evidence",
        "panel-failed",
    )
    assert proc.returncode == 2
    assert "design-tmpdir is required" in proc.stderr


def test_persist_round_start_s_rejects_disallowed_design_tmpdir() -> None:
    disallowed = ROOT / "python" / ".persist-round-start-disallowed-test-dir"
    disallowed.mkdir(exist_ok=True)
    try:
        assert plan_review.persist_design_round_start_s(disallowed, 1, 100) == 1
        proc = run_cli(
            "plan-review",
            "persist-round-start-s",
            "--design-tmpdir",
            str(disallowed),
            "--round-num",
            "1",
            "--start-s",
            "100",
        )
        assert proc.returncode == 1
    finally:
        if disallowed.exists():
            disallowed.rmdir()


def test_record_report_evidence_rejects_relative_tmpdir() -> None:
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        "relative",
        "--record-report-evidence",
        "panel-failed",
    )
    assert proc.returncode == 2


def test_drift_baseline_replaces_broken_symlink(tmp_path: Path) -> None:
    target = tmp_path / "missing-target.env"
    baseline = tmp_path / "drift-baseline.env"
    baseline.symlink_to(target)
    assert plan_review.drift_baseline_write_once(tmp_path, "10", "20") == 0
    assert baseline.is_file()
    assert baseline.read_text(encoding="utf-8") == (
        "BASELINE_PLAN_LINES=10\nBASELINE_DIFF_LINES=20\n"
    )


def test_drift_baseline_rejects_invalid_line_counts(tmp_path: Path) -> None:
    assert plan_review.drift_baseline_write_once(tmp_path, "10\n", "20") == 1
    assert plan_review.drift_baseline_write_once(tmp_path, "10", "bad") == 1
    assert not (tmp_path / "drift-baseline.env").exists()


def test_drift_baseline_cli_rejects_invalid_counts(tmp_path: Path) -> None:
    proc = run_cli(
        "plan-review",
        "drift-baseline",
        "write-once",
        "--design-tmpdir",
        str(tmp_path),
        "--plan-lines",
        "1\n2",
        "--diff-lines",
        "3",
    )
    assert proc.returncode == 1
    assert not (tmp_path / "drift-baseline.env").exists()


def test_scope_anchor_relay_allowed_cli() -> None:
    proc = run_cli(
        "scope-anchor",
        "relay-allowed",
        "--tally-plan-review-status",
        "ok",
        "--loop-status",
        "complete",
    )
    assert proc.returncode == 0, proc.stderr


def test_scope_anchor_relay_denied_on_tally_error() -> None:
    proc = run_cli(
        "scope-anchor",
        "relay-allowed",
        "--tally-plan-review-status",
        "tally-error",
        "--loop-status",
        "complete",
    )
    assert proc.returncode == 1


def _write_loop_stub(tmp_path: Path, body: str) -> Path:
    stub = tmp_path / "plan-review-loop-stub.sh"
    _ = stub.write_text(f"#!/usr/bin/env bash\nset -euo pipefail\n{body}\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _write_run_params(tmp_path: Path) -> None:
    _ = (tmp_path / "run-params.json").write_text(
        '{"schema_version":2,"design_classification":"feature","workflow_path":"feature","partition_requested":false,"brainstorm_requested":false}',
        encoding="utf-8",
    )
    _ = (tmp_path / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (tmp_path / "feature-description.txt").write_text("feature\n", encoding="utf-8")


def test_cap_reached_short_circuit(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("5\n", encoding="utf-8")
    stub = _write_loop_stub(
        tmp_path,
        "printf 'LOOP_STATUS=complete\\n'; exit 0",
    )
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--no-preview",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(stub),
        },
    )
    assert proc.returncode == 0, proc.stderr
    assert "LOOP_STATUS=cap-reached" in proc.stdout
    assert "TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached" in proc.stdout
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "5\n"
    assert (tmp_path / ".completed" / "step-3").is_file()


def test_tally_error_rollback_review_round_count(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    stub = _write_loop_stub(
        tmp_path,
        (
            "printf 'STEP3_REVIEW_LOOP_STATUS=tally-error\\n"
            "LOOP_STATUS=tally-error\\n"
            "ACCEPTED_COUNT=0\\nDEGRADED_PANEL=0\\n"
            "ROUNDS_COMPLETED=3\\nTALLY_PLAN_REVIEW_STATUS=tally-error\\n"
            "AGGREGATOR_STATUS=ok\\nVOTING_TALLY_FILE=\\n'; exit 2"
        ),
    )
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(stub),
        },
    )
    assert "STEP3_REVIEW_LOOP_STATUS=tally-error" in proc.stdout
    assert "LOOP_STATUS=tally-error" in proc.stdout
    assert "TALLY_PLAN_REVIEW_STATUS=tally-error" in proc.stdout
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "2\n"
    result_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "STEP3_REVIEW_LOOP_STATUS=tally-error" in result_env
    assert "LOOP_STATUS=tally-error" in result_env


def test_degraded_empty_collector_rollback_review_round_count(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    stub = _write_loop_stub(
        tmp_path,
        (
            "printf 'STEP3_REVIEW_LOOP_STATUS=degraded-empty-collector\\n"
            "LOOP_STATUS=degraded-empty-collector\\n"
            "ACCEPTED_COUNT=0\\nDEGRADED_PANEL=1\\n"
            "ROUNDS_COMPLETED=2\\nTALLY_PLAN_REVIEW_STATUS=ok\\n"
            "AGGREGATOR_STATUS=ok\\nVOTING_TALLY_FILE=\\n'; exit 0"
        ),
    )
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(stub),
        },
    )
    assert "STEP3_REVIEW_LOOP_STATUS=degraded-empty-collector" in proc.stdout
    assert "LOOP_STATUS=degraded-empty-collector" in proc.stdout
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "2\n"


def _write_gate_b_plan(tmp_path: Path, body: str) -> None:
    _ = (tmp_path / "plan.txt").write_text(body, encoding="utf-8")


def test_gate_b_dedup_snapshot_and_fail_closed_without_snapshot(tmp_path: Path) -> None:
    _write_gate_b_plan(
        tmp_path,
        "body\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n",
    )
    proc = run_cli(
        "plan-review",
        "gate-b-dedup",
        "--design-tmpdir",
        str(tmp_path),
        "--snapshot-trailers",
    )
    assert proc.returncode == 0, proc.stderr
    keys = (tmp_path / ".gate-b-optional-trailer-keys").read_text(encoding="utf-8")
    values = (tmp_path / ".gate-b-optional-trailer-keys.values").read_text(encoding="utf-8")
    assert "diff_added" in keys
    assert "diff_added=100" in values

    bare = tmp_path / "no-snapshot"
    bare.mkdir()
    _write_gate_b_plan(bare, "body\ndiff_lines: 1\n")
    proc = run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(bare), "--dedup")
    assert proc.returncode == 3


def test_gate_b_dedup_preserves_trailers_and_rejects_new_keys(tmp_path: Path) -> None:
    _write_gate_b_plan(
        tmp_path,
        "body\nbody\ndiff_added: 100\ndiff_deleted: 50\nmechanical_churn: true\ndiff_lines: 200\n",
    )
    assert (
        run_cli(
            "plan-review",
            "gate-b-dedup",
            "--design-tmpdir",
            str(tmp_path),
            "--snapshot-trailers",
        ).returncode
        == 0
    )
    proc = run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(tmp_path), "--dedup")
    assert proc.returncode == 0, proc.stderr
    assert "dedup-sweep: removed 1 duplicate" in proc.stdout
    plan_text = (tmp_path / "plan.txt").read_text(encoding="utf-8")
    assert "diff_added: 100" in plan_text
    assert "mechanical_churn: true" in plan_text

    empty_snapshot = tmp_path / "reject-new"
    empty_snapshot.mkdir()
    _write_gate_b_plan(empty_snapshot, "line\nline\ndiff_lines: 10\n")
    assert (
        run_cli(
            "plan-review",
            "gate-b-dedup",
            "--design-tmpdir",
            str(empty_snapshot),
            "--snapshot-trailers",
        ).returncode
        == 0
    )
    _ = (empty_snapshot / "plan.txt").write_text(
        "line\nline\nmechanical_churn: true\ndiff_lines: 10\n",
        encoding="utf-8",
    )
    proc = run_cli(
        "plan-review",
        "gate-b-dedup",
        "--design-tmpdir",
        str(empty_snapshot),
        "--dedup",
    )
    assert proc.returncode == 1


def test_gate_b_dedup_allows_value_recompute_and_rejects_key_loss(tmp_path: Path) -> None:
    _write_gate_b_plan(tmp_path, "body\ndiff_added: 100\ndiff_lines: 200\n")
    assert (
        run_cli(
            "plan-review",
            "gate-b-dedup",
            "--design-tmpdir",
            str(tmp_path),
            "--snapshot-trailers",
        ).returncode
        == 0
    )
    _ = (tmp_path / "plan.txt").write_text("body\ndiff_added: 999\ndiff_lines: 200\n", encoding="utf-8")
    proc = run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(tmp_path), "--dedup")
    assert proc.returncode == 0, proc.stderr
    assert "diff_added: 999" in (tmp_path / "plan.txt").read_text(encoding="utf-8")

    key_loss = tmp_path / "key-loss"
    key_loss.mkdir()
    _write_gate_b_plan(key_loss, "body\ndiff_added: 100\ndiff_lines: 200\n")
    assert (
        run_cli(
            "plan-review",
            "gate-b-dedup",
            "--design-tmpdir",
            str(key_loss),
            "--snapshot-trailers",
        ).returncode
        == 0
    )
    _ = (key_loss / "plan.txt").write_text("body\ndiff_lines: 200\n", encoding="utf-8")
    proc = run_cli("plan-review", "gate-b-dedup", "--design-tmpdir", str(key_loss), "--dedup")
    assert proc.returncode == 1


def test_persist_retally_tally_error_omits_scope_anchor(tmp_path: Path) -> None:
    _ = (tmp_path / "plan-review-scope-anchor.txt").write_text("anchor body\n", encoding="utf-8")
    stale_anchor = tmp_path / "stale-scope-anchor.txt"
    _ = stale_anchor.write_text("stale anchor\n", encoding="utf-8")
    plan_env = "\n".join(
        [
            "LOOP_STATUS=main-agent-vote-required",
            "TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required",
            f"SCOPE_ANCHOR_FILE={stale_anchor}",
            "ACCEPTED_COUNT=3",
            "IMPORTANT_ACCEPTED_COUNT=2",
            "NIT_ACCEPTED_COUNT=0",
            "NON_NIT_ACCEPTED_COUNT=3",
            "",
        ]
    )
    _ = (tmp_path / ".step3-plan-review-result.env").write_text(plan_env, encoding="utf-8")
    _ = (tmp_path / ".step3-review-result.env").write_text(plan_env, encoding="utf-8")
    _ = (tmp_path / "accepted-plan-findings.md").write_text(
        "### FINDING_99: Partial failed re-tally accepted\n- **Concern**: should be cleared\n",
        encoding="utf-8",
    )
    retally_stdout = tmp_path / "retally-stdout.txt"
    _ = retally_stdout.write_text(
        f"TALLY_PLAN_REVIEW_STATUS=tally-error\nVOTING_TALLY_FILE={tmp_path}/voting-tally.md\n",
        encoding="utf-8",
    )
    proc = run_cli(
        "plan-review",
        "persist-retally-env",
        "--design-tmpdir",
        str(tmp_path),
        "--retally-stdout-file",
        str(retally_stdout),
        "--retally-input-anchor",
        str(stale_anchor),
        "--tally-plan-review-status",
        "tally-error",
        "--loop-status",
        "complete",
    )
    assert proc.returncode == 0, proc.stderr
    plan_review_env = (tmp_path / ".step3-plan-review-result.env").read_text(encoding="utf-8")
    review_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "SCOPE_ANCHOR_FILE=" not in plan_review_env
    assert "SCOPE_ANCHOR_FILE=" not in review_env
    assert "TALLY_PLAN_REVIEW_STATUS=tally-error" in plan_review_env
    assert "LOOP_STATUS=complete" in review_env
    assert not (tmp_path / "accepted-plan-findings.md").read_text(encoding="utf-8").strip()
    assert "ACCEPTED_COUNT=0" in plan_review_env
    assert "IMPORTANT_ACCEPTED_COUNT=0" in review_env


def test_persist_retally_ok_persists_scope_anchor(tmp_path: Path) -> None:
    design_canon = str(tmp_path.resolve())
    anchor = tmp_path / "plan-review-scope-anchor.txt"
    _ = anchor.write_text("anchor body\n", encoding="utf-8")
    stale_anchor = tmp_path / "stale-scope-anchor.txt"
    _ = stale_anchor.write_text("stale anchor\n", encoding="utf-8")
    _ = (tmp_path / ".step3-plan-review-result.env").write_text(
        "LOOP_STATUS=main-agent-vote-required\nTALLY_PLAN_REVIEW_STATUS=main-agent-vote-required\nACCEPTED_COUNT=0\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".step3-review-result.env").write_text(
        (tmp_path / ".step3-plan-review-result.env").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    retally_stdout = tmp_path / "retally-ok.txt"
    _ = retally_stdout.write_text(
        f"TALLY_PLAN_REVIEW_STATUS=ok\nSCOPE_ANCHOR_FILE={design_canon}/plan-review-scope-anchor.txt\n",
        encoding="utf-8",
    )
    proc = run_cli(
        "plan-review",
        "persist-retally-env",
        "--design-tmpdir",
        str(tmp_path),
        "--retally-stdout-file",
        str(retally_stdout),
        "--retally-input-anchor",
        str(stale_anchor),
        "--tally-plan-review-status",
        "ok",
        "--loop-status",
        "complete",
    )
    assert proc.returncode == 0, proc.stderr
    expected = f"SCOPE_ANCHOR_FILE={design_canon}/plan-review-scope-anchor.txt"
    plan_review_env = (tmp_path / ".step3-plan-review-result.env").read_text(encoding="utf-8")
    review_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert expected in plan_review_env
    assert expected in review_env


def _write_tally_ballot(path: Path) -> None:
    _ = path.write_text(
        """### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- focus-area = correctness
- Concern: parser misses bad input.

### FINDING_2: Optional cleanup
- **Reviewer**: Codex-Pragmatic
- focus-area = code-quality
- Concern: cleanup could be smaller.

### OOS_1: Follow-up docs
- **Reviewer**: Cursor-Arch
- focus-area = documentation
- Concern: docs follow-up.

### OOS_2: Token leak audit
- **Reviewer**: Codex-Security
- focus-area = security
- Concern: security-sensitive follow-up.
""",
        encoding="utf-8",
    )


def test_tally_plan_review_mixed_votes_and_artifacts(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    _ = v1.write_text("FINDING_1: YES\nFINDING_2: NO\nOOS_1: YES\nOOS_2: YES\n", encoding="utf-8")
    _ = v2.write_text("FINDING_1: YES\nFINDING_2: YES\nOOS_1: NO\nOOS_2: YES\n", encoding="utf-8")
    _ = v3.write_text("FINDING_1: YES\nFINDING_2: NO\nOOS_1: YES\nOOS_2: YES\n", encoding="utf-8")
    design = tmp_path / "design"
    design.mkdir()
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(v1),
        str(v2),
        str(v3),
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "TALLY_PLAN_REVIEW_STATUS=ok" in proc.stdout
    accepted = (design / "accepted-plan-findings.md").read_text(encoding="utf-8")
    rejected = (design / "rejected-findings.md").read_text(encoding="utf-8")
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "FINDING_1" in accepted
    assert "FINDING_2" in rejected
    assert "OOS_1" in (design / "oos.md").read_text(encoding="utf-8")
    assert "OOS_2" not in (design / "oos.md").read_text(encoding="utf-8")
    assert "| Cursor-Arch | 1 | 1 | 0 | 0 | 1 | 1 | 0 | 0 | 2 |" in tally


def test_tally_plan_review_zero_voters_requires_main_agent(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    design = tmp_path / "design-zero"
    design.mkdir()
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required" in proc.stdout
    assert not (design / "accepted-plan-findings.md").read_text(encoding="utf-8").strip()


def test_tally_plan_review_single_yes_and_single_no(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    yes_voter = tmp_path / "yes.txt"
    no_voter = tmp_path / "no.txt"
    _ = yes_voter.write_text("FINDING_1: YES\n", encoding="utf-8")
    _ = no_voter.write_text("FINDING_1: NO\n", encoding="utf-8")
    design_yes = tmp_path / "design-one-yes"
    design_yes.mkdir()
    proc_yes = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(yes_voter),
        "--design-tmpdir",
        str(design_yes),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc_yes.returncode == 0, proc_yes.stderr
    assert "FINDING_1" in (design_yes / "accepted-plan-findings.md").read_text(encoding="utf-8")
    design_no = tmp_path / "design-one-no"
    design_no.mkdir()
    proc_no = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(no_voter),
        "--design-tmpdir",
        str(design_no),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc_no.returncode == 0, proc_no.stderr
    assert "FINDING_1" in (design_no / "rejected-findings.md").read_text(encoding="utf-8")


def test_loop_dedup_failure_restores_plan_snapshot(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    original = "# Plan\n\ndiff_lines: 1\n"
    _ = (tmp_path / "plan.txt").write_text(original, encoding="utf-8")
    dedup_stub = tmp_path / "dedup-stub.sh"
    _ = dedup_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
case " $* " in
  *' --snapshot-trailers '*) exit 0 ;;
  *' --dedup '*) exit 2 ;;
  *) exit 0 ;;
esac
""",
        encoding="utf-8",
    )
    dedup_stub.chmod(0o755)
    revise_stub = tmp_path / "revise-stub.sh"
    _ = revise_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
plan=""
while [[ $# -gt 0 ]]; do
  case "$1" in --plan-file) plan="${2:?}"; shift 2 ;; *) shift ;; esac
done
printf '\\n# revised\\n' >>"$plan"
printf 'REVISE_STATUS=ok\\n'
""",
        encoding="utf-8",
    )
    revise_stub.chmod(0o755)
    round_stub = _write_loop_stub(
        tmp_path,
        (
            f"cat >\"{tmp_path}/accepted-plan-findings.md\" <<'FINDINGS'\n"
            "### FINDING_1: Important\n- **Severity**: important\n- **Concern**: issue\n"
            "FINDINGS\n"
            "printf 'LOOP_STATUS=complete\\nACCEPTED_COUNT=1\\nIMPORTANT_ACCEPTED_COUNT=1\\n"
            "DEGRADED_PANEL=0\\nROUNDS_COMPLETED=1\\nTALLY_PLAN_REVIEW_STATUS=ok\\n"
            "AGGREGATOR_STATUS=ok\\nVOTING_TALLY_FILE=\\n'"
        ),
    )
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(round_stub),
            "RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH": str(revise_stub),
            "RUN_STEP3_DEDUP_PLAN_SH": str(dedup_stub),
        },
    )
    assert "STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required" in proc.stdout
    assert "DEDUP_RC=2" in proc.stdout
    snapshot = tmp_path / "plan-pre-apply-round-1.txt"
    assert snapshot.is_file()
    assert (tmp_path / "plan.txt").read_text(encoding="utf-8") == snapshot.read_text(encoding="utf-8")


def test_terminal_zero_accepted_round_writes_round_meta(tmp_path: Path) -> None:
    # Regression for #4811: a plan-review run that stops on a 0-accepted final
    # round must still write round-meta.json for that round, so the Review Phase
    # Detail table includes it and the table row count matches the header count.
    _write_run_params(tmp_path)
    meta_stub = tmp_path / "write-meta-stub.sh"
    _ = meta_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
round_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in --round-dir) round_dir="${2:?}"; shift 2 ;; *) shift ;; esac
done
mkdir -p "$round_dir"
printf '{"tally":{"ACCEPTED_COUNT":0}}\\n' >"$round_dir/round-meta.json"
""",
        encoding="utf-8",
    )
    meta_stub.chmod(0o755)
    continuation_stub = tmp_path / "continuation-stub.sh"
    _ = continuation_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
printf 'PLAN_REVIEW_CONTINUE=false\\nPLAN_REVIEW_CONTINUE_REASON=small-clean\\n'
""",
        encoding="utf-8",
    )
    continuation_stub.chmod(0o755)
    round_stub = _write_loop_stub(
        tmp_path,
        (
            "printf 'LOOP_STATUS=complete\\nACCEPTED_COUNT=0\\nDEGRADED_PANEL=0\\n"
            "ROUNDS_COMPLETED=1\\nTALLY_PLAN_REVIEW_STATUS=ok\\n"
            "AGGREGATOR_STATUS=ok\\nVOTING_TALLY_FILE=\\n'"
        ),
    )
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(round_stub),
            "RUN_STEP3_CONTINUATION_SH": str(continuation_stub),
            "WRITE_DESIGN_ROUND_META_SH": str(meta_stub),
        },
    )
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    # The terminal 0-accepted round now has round-meta.json, so _completed_round_dirs
    # (the Review Phase Detail source set) includes it. Before the fix it was absent.
    assert (tmp_path / "plan-review" / "round-1" / "round-meta.json").is_file(), proc.stdout


def test_record_round_timing_idempotent_and_round_snapshot_counts(tmp_path: Path) -> None:
    _ = (tmp_path / "accepted-plan-findings.md").write_text("### FINDING_1:\n### FINDING_2:\n", encoding="utf-8")
    _ = (tmp_path / "rejected-findings.md").write_text("### [Plan Review] FINDING_1\n", encoding="utf-8")
    _ = (tmp_path / "voting-tally.md").write_text(
        "## Findings\n| Item | YES | NO | JERR | Result |\n| --- | --- | --- | --- | --- |\n"
        "| OOS_1 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )
    proc = run_cli(
        "plan-review",
        "record-round-timing",
        "--design-tmpdir",
        str(tmp_path),
        "--round",
        "1",
        "--start-s",
        "100",
        "--end-s",
        "110",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    ledger = (tmp_path / "timing-ledger.tsv").read_text(encoding="utf-8")
    assert "design Step 3 — plan review" in ledger
    proc_dup = run_cli(
        "plan-review",
        "record-round-timing",
        "--design-tmpdir",
        str(tmp_path),
        "--round",
        "1",
        "--start-s",
        "100",
        "--end-s",
        "110",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc_dup.returncode == 0, proc_dup.stderr
    round_rows = [line for line in ledger.splitlines() if "\tround\t" in line and "\tdesign\t" in line]
    assert len(round_rows) >= 1
    snap = tmp_path / "plan-review" / "round-4"
    snap.mkdir(parents=True)
    _ = (snap / "accepted-plan-findings.md").write_text("### FINDING_1:\n### FINDING_2:\n### FINDING_3:\n", encoding="utf-8")
    proc_snap = run_cli(
        "plan-review",
        "record-round-timing",
        "--design-tmpdir",
        str(tmp_path),
        "--round",
        "4",
        "--start-s",
        "400",
        "--end-s",
        "410",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc_snap.returncode == 0, proc_snap.stderr
    assert (tmp_path / "timing-ledger.tsv").exists()


def test_preview_gatec_header_and_invalid_threshold(tmp_path: Path) -> None:
    body = "# Gate\n" + "\n".join(f"line {i}" for i in range(130)) + "\n"
    _ = (tmp_path / "plan.txt").write_text(body, encoding="utf-8")
    proc = run_cli("plan-review", "preview", "--design-tmpdir", str(tmp_path), "--variant", "gatec")
    assert proc.returncode == 0, proc.stderr
    assert "## Final Design Plan" in proc.stdout
    proc_thresh = run_cli(
        "plan-review",
        "preview",
        "--design-tmpdir",
        str(tmp_path),
        "--variant",
        "step3",
        env={"LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD": "abc"},
    )
    assert proc_thresh.returncode == 0
    assert "very large" in proc_thresh.stdout


def test_preview_empty_and_disallowed_tmpdir_warn_exit_zero() -> None:
    proc_empty = run_cli("plan-review", "preview", "--design-tmpdir", "", "--variant", "step3")
    assert proc_empty.returncode == 0
    assert "DESIGN_TMPDIR missing or invalid" in proc_empty.stdout
    disallowed = ROOT / "python" / ".preview-disallowed-test-dir"
    disallowed.mkdir(exist_ok=True)
    try:
        proc_bad = run_cli("plan-review", "preview", "--design-tmpdir", str(disallowed), "--variant", "step3")
        assert proc_bad.returncode == 0
        assert "DESIGN_TMPDIR not under allowlist" in proc_bad.stdout
        assert not (disallowed / ".step3-entry-plan-printed").exists()
    finally:
        if disallowed.exists():
            disallowed.rmdir()


def test_preview_small_plan_full_body_without_large_note(tmp_path: Path) -> None:
    _ = (tmp_path / "plan.txt").write_text("# Small\n\nHello\n\ndiff_lines: 1\n", encoding="utf-8")
    proc = run_cli("plan-review", "preview", "--design-tmpdir", str(tmp_path), "--variant", "step3")
    assert proc.returncode == 0
    assert "Hello" in proc.stdout
    assert "very large" not in proc.stdout


def _high_finding_block(num: int, *, severity: str, location: str, concern: str) -> str:
    return (
        f"### FINDING_{num}:\n"
        f"- **Reviewer(s)**: Cursor-arch\n"
        f"- **Severity**: {severity}\n"
        f"- **Focus area**: architecture\n"
        f"- **Location**: {location}\n"
        f"- **Concern**: {concern}\n"
        f"- **Proposed resolution**: dedupe across rounds\n\n"
    )


def test_continuation_converges_when_round_reraises_applied_findings(tmp_path: Path) -> None:
    # Regression for the non-converging plan-review loop (#4808): a finding
    # accepted and applied in a prior round, when re-raised and re-accepted,
    # must not keep the loop going.
    findings = (
        _high_finding_block(
            1,
            severity="important",
            location="python/plan_review.py:1039",
            concern="continuation re-triggers on duplicate findings. Scenario: round 2 re-raises round 1.",
        )
        + _high_finding_block(
            2,
            severity="blocking",
            location="python/plan_review_round.py:144",
            concern="collector re-emits identical findings. Scenario: stable reviewer output.",
        )
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(findings, encoding="utf-8")

    # Round 1: both findings are genuinely new -> loop continues.
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc1 = run_cli(
        "plan-review",
        "continuation",
        "--design-tmpdir",
        str(tmp_path),
        "--approve-requested",
        "false",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc1.returncode == 0, proc1.stderr
    assert "PLAN_REVIEW_CONTINUE=true" in proc1.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=high-accepted" in proc1.stdout

    # Round 2: re-raises the same findings byte-for-byte -> nothing new -> stop.
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    proc2 = run_cli(
        "plan-review",
        "continuation",
        "--design-tmpdir",
        str(tmp_path),
        "--approve-requested",
        "false",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc2.returncode == 0, proc2.stderr
    assert "PLAN_REVIEW_CONTINUE=false" in proc2.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=converged-no-new-findings" in proc2.stdout
    assert "DUPLICATE_ACCEPTED_COUNT=2" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=0" in proc2.stdout
    # Totals stay reported for backward compatibility.
    assert "HIGH_ACCEPTED_COUNT=2" in proc2.stdout


def test_continuation_continues_when_a_new_finding_appears(tmp_path: Path) -> None:
    round1 = _high_finding_block(
        1, severity="important", location="a.py:1", concern="alpha. Scenario: x."
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(round1, encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc1 = run_cli(
        "plan-review", "continuation", "--design-tmpdir", str(tmp_path),
        "--approve-requested", "false", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "PLAN_REVIEW_CONTINUE=true" in proc1.stdout

    # Round 2: re-raises round-1 finding (duplicate) plus a brand-new high one.
    round2 = round1 + _high_finding_block(
        2, severity="blocking", location="b.py:2", concern="beta. Scenario: y."
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(round2, encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    proc2 = run_cli(
        "plan-review", "continuation", "--design-tmpdir", str(tmp_path),
        "--approve-requested", "false", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "PLAN_REVIEW_CONTINUE=true" in proc2.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=high-accepted" in proc2.stdout
    assert "DUPLICATE_ACCEPTED_COUNT=1" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=1" in proc2.stdout


def test_continuation_degraded_panel_converges_on_duplicate_findings(tmp_path: Path) -> None:
    # Degraded-panel continuation must not bypass cross-round dedup (#4808).
    findings = _high_finding_block(
        1,
        severity="important",
        location="python/plan_review.py:1163",
        concern="degraded panel re-triggers on duplicates. Scenario: round 2 re-raises round 1.",
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(findings, encoding="utf-8")
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "DEGRADED_PANEL=1\nTALLY_PLAN_REVIEW_STATUS=ok\n",
        encoding="utf-8",
    )

    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc1 = run_cli(
        "plan-review",
        "continuation",
        "--design-tmpdir",
        str(tmp_path),
        "--approve-requested",
        "false",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc1.returncode == 0, proc1.stderr
    assert "PLAN_REVIEW_CONTINUE=true" in proc1.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=degraded-panel" in proc1.stdout

    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    proc2 = run_cli(
        "plan-review",
        "continuation",
        "--design-tmpdir",
        str(tmp_path),
        "--approve-requested",
        "false",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc2.returncode == 0, proc2.stderr
    assert "PLAN_REVIEW_CONTINUE=false" in proc2.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=converged-no-new-findings" in proc2.stdout
    assert "DUPLICATE_ACCEPTED_COUNT=1" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=0" in proc2.stdout


def test_step3_state_direct_review_entry_resets_applied_finding_ledger(tmp_path: Path) -> None:
    ledger = tmp_path / ".step3-applied-finding-keys.tsv"
    _ = ledger.write_text("1\tpython/plan_review.py:1039\x1fconcern\n", encoding="utf-8")
    _ = (tmp_path / ".step3-reentry").write_text("1\n", encoding="utf-8")
    proc = run_cli(
        "plan-review", "step3-state", "--design-tmpdir", str(tmp_path),
        "--direct-review-entry", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=direct-review-entry" in proc.stdout
    assert not ledger.exists()


def test_compose_attributed_ballot_uses_post_aggregate_findings_not_stale_ballot(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "findings-in-scope.md").write_text(
        "### FINDING_2: fresh\n- **Reviewer**: Codex\n- **Concern**: c\n",
        encoding="utf-8",
    )
    _ = (design / "ballot.txt").write_text(
        "### FINDING_1: stale\n- **Reviewer**: anonymous\n- **Concern**: old\n",
        encoding="utf-8",
    )
    text = plan_review_round._compose_attributed_ballot(design, "")  # pyright: ignore[reportPrivateUsage]
    assert "FINDING_2" in text
    assert "FINDING_1" not in text


def test_plan_review_ballot_neutralization_writes_sidecar_and_anonymous_ballot(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    in_scope = """### FINDING_1: Bug
- **Reviewer**: Codex-Plan
- **Concern**: concern
"""
    oos = """### OOS_1: [OUT_OF_SCOPE] drift
- **Reviewer**: cursor-pragmatic
- **Concern**: oos concern
"""
    _ = (design / "findings-in-scope.md").write_text(in_scope, encoding="utf-8")
    ballot_text = plan_review_round._compose_attributed_ballot(design, oos)  # pyright: ignore[reportPrivateUsage]
    ballot = design / "ballot.txt"
    _ = ballot.write_text(ballot_text, encoding="utf-8")
    proposer_map = design / "proposer-map.tsv"
    voting.write_proposer_map(ballot, proposer_map)
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(ballot_text), encoding="utf-8")
    neutral = ballot.read_text(encoding="utf-8")
    assert "anonymous" in neutral
    assert "Codex-Plan" not in neutral
    rows = voting.read_proposer_map(proposer_map)
    assert rows["FINDING_1"][0] == "Codex-Plan"
    assert rows["OOS_1"][0] == "cursor-pragmatic"


def test_tally_plan_review_neutralized_ballot_auto_binds_sidecar(tmp_path: Path) -> None:
    attributed = """### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- **Concern**: parser misses bad input.
"""
    design = tmp_path / "design"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text(attributed, encoding="utf-8")
    voting.write_proposer_map(ballot, design / "proposer-map.tsv")
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(attributed), encoding="utf-8")
    voter = tmp_path / "v1.txt"
    _ = voter.write_text("FINDING_1: YES\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(voter),
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    accepted = (design / "accepted-plan-findings.md").read_text(encoding="utf-8")
    assert "- **Reviewer**: Cursor-Arch" in accepted
    assert "anonymous" not in accepted
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Cursor-Arch |" in tally


def test_tally_plan_review_missing_sidecar_entry_fails_closed(tmp_path: Path) -> None:
    attributed = """### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- **Concern**: parser misses bad input.

### FINDING_2: Optional cleanup
- **Reviewer**: Codex-Pragmatic
- **Concern**: cleanup could be smaller.
"""
    design = tmp_path / "design-missing-map"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text(attributed, encoding="utf-8")
    map_file = design / "proposer-map.tsv"
    voting.write_proposer_map(ballot, map_file)
    rows = map_file.read_text(encoding="utf-8").splitlines()
    _ = map_file.write_text("\n".join(rows[:2]) + "\n", encoding="utf-8")
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(attributed), encoding="utf-8")
    voter = tmp_path / "v1.txt"
    _ = voter.write_text("FINDING_1: YES\nFINDING_2: YES\n", encoding="utf-8")
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(voter),
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode != 0
    assert "missing proposer map entry" in proc.stderr
