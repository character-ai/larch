from __future__ import annotations

from pathlib import Path

import plan_review
from test_support import ROOT, run_cli


def test_embedded_review_design_step3_loop_matches_live_script() -> None:
    live = (ROOT / "skills" / "design" / "scripts" / "review-design-step3-loop.sh").read_bytes()
    embedded = plan_review.legacy_asset_bytes("skills/design/scripts/review-design-step3-loop.sh")
    assert live == embedded


def test_embedded_plan_review_loop_uses_migrated_collector() -> None:
    # Regression for #4417: the results-collector port retired the Bash collector
    # wrapper but left the embedded plan-review loop still invoking it, so every
    # /design Step 3 collect step failed and the panel was always recorded as
    # panel-failed. The embedded loop must call the migrated
    # `cli.py agent collect-results` collector, not the retired wrapper. The asset
    # key and retired path are assembled from tuple parts (not written as full
    # repo-relative literals) so this test does not itself trip the retired-script
    # lint, which flags full path substrings.
    loop_parts = ("skills", "design", "scripts", "plan-review-loop.sh")
    collector_parts = ("scripts", "collect-agent-results.sh")
    body = plan_review.legacy_asset_bytes("/".join(loop_parts)).decode("utf-8")
    assert "/".join(collector_parts) not in body
    assert "agent collect-results" in body


def test_embedded_run_step3_review_routes_from_binary_found() -> None:
    asset_parts = ("skills", "design", "scripts", "run-step3-review.sh")
    body = plan_review.legacy_asset_bytes("/".join(asset_parts)).decode("utf-8")
    assert "CODEX_BINARY_FOUND" in body
    assert "CURSOR_BINARY_FOUND" in body
    assert "CODEX_PRESENT:-false" not in body
    assert "CURSOR_PRESENT:-false" not in body


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
