from __future__ import annotations

import contextlib
import csv
import io
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from larch.core import logging_util
from larch.review import plan_review
from larch.review import plan_review_round
from larch.report import progress_report
import pytest
from larch.review import voting
from test_support import ROOT, make_zero_findings_plan_review_fake_cli, run_cli


def _read_tsv(path: Path) -> dict[str, dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return {row["finding_id"]: row for row in csv.DictReader(fh, delimiter="\t")}


def _read_tsv_list(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh, delimiter="\t"))


def test_legacy_assets_removed_from_plan_review_module() -> None:
    assert not hasattr(plan_review, "_LEGACY_ASSETS")
    assert not hasattr(plan_review, "run_legacy_script")


def test_new_process_group_calls_setsid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[None] = []

    def fake_setsid() -> None:
        calls.append(None)

    monkeypatch.setattr(plan_review.os, "setsid", fake_setsid)  # type: ignore[arg-type]
    _ = (tmp_path / "plan-review-scope-anchor.txt").write_text("anchor\n", encoding="utf-8")
    review_cap_env = tmp_path / ".step3-review-cap.env"
    _ = review_cap_env.write_text("LOOP_STATUS=cap-reached\nTALLY_PLAN_REVIEW_STATUS=skipped-cap-reached\n", encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text(f"{plan_review.ROUND_CAP}\n", encoding="utf-8")
    result = plan_review.run_step3_review(["--design-tmpdir", str(tmp_path), "--new-process-group"])
    assert result == 0
    assert len(calls) == 1


def test_new_process_group_absent_does_not_call_setsid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_setsid() -> None:
        raise AssertionError("setsid must not be called without --new-process-group")

    monkeypatch.setattr(plan_review.os, "setsid", forbidden_setsid)  # type: ignore[arg-type]
    _ = (tmp_path / "plan-review-scope-anchor.txt").write_text("anchor\n", encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text(f"{plan_review.ROUND_CAP}\n", encoding="utf-8")
    result = plan_review.run_step3_review(["--design-tmpdir", str(tmp_path)])
    assert result == 0


def test_new_process_group_oserror_exits_2(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_setsid() -> None:
        raise OSError("boom")

    monkeypatch.setattr(plan_review.os, "setsid", failing_setsid)  # type: ignore[arg-type]
    stderr_buf = io.StringIO()
    monkeypatch.setattr(sys, "stderr", stderr_buf)
    with pytest.raises(SystemExit) as exc_info:
        _ = plan_review.run_step3_review(["--design-tmpdir", str(tmp_path), "--new-process-group"])
    assert exc_info.value.code == 2
    assert "--new-process-group" in stderr_buf.getvalue()


def _run_step3_normalizer(tmp_path: Path, stdout_text: str = "", loop_rc: int = 0) -> subprocess.CompletedProcess[str]:
    stdout_file = tmp_path / "plan-review.stdout"
    _ = stdout_file.write_text(stdout_text, encoding="utf-8")
    return run_cli(
        "plan-review",
        "normalize-status",
        "--design-tmpdir",
        str(tmp_path),
        "--stdout-file",
        str(stdout_file),
        "--loop-rc",
        str(loop_rc),
    )


def test_step3_normalize_read_result_env_present_missing_and_symlink(tmp_path: Path) -> None:
    result_env = tmp_path / ".step3-review-result.env"
    _ = result_env.write_text(
        "STEP3_REVIEW_LOOP_STATUS=tally-error\n"
        "LOOP_STATUS=tally-error\n"
        "ROUNDS_COMPLETED=1\n"
        "FINAL_ROUND_NUM=2\n"
        "ACCEPTED_COUNT=3\n"
        "DEGRADED_PANEL_WARNING=panel degraded\n"
        "INVALID_SLOT_PANEL_WARNING=invalid slot dropped\n",
        encoding="utf-8",
    )
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=ok",
        "NEXT_ACTION=step3b-bypass",
        "STEP3_REVIEW_LOOP_STATUS=tally-error",
        "LOOP_STATUS=tally-error",
        "ROUNDS_COMPLETED=1",
        "FINAL_ROUND_NUM=2",
        "ACCEPTED_COUNT=3",
        "DEGRADED_PANEL_WARNING=panel degraded",
        "INVALID_SLOT_PANEL_WARNING=invalid slot dropped",
    ]

    result_env.unlink()
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=missing",
        "NEXT_ACTION=",
        "STEP3_REVIEW_LOOP_STATUS=",
        "LOOP_STATUS=",
        "ROUNDS_COMPLETED=",
        "FINAL_ROUND_NUM=",
        "ACCEPTED_COUNT=",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
    ]

    target = tmp_path / "target.env"
    _ = target.write_text("STEP3_REVIEW_LOOP_STATUS=complete\n", encoding="utf-8")
    result_env.symlink_to(target)
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert "READ_RESULT_ENV_STATUS=missing" in proc.stdout
    assert "WARN=" not in proc.stdout


def test_step3_read_result_env_quiet_suppresses_internal_replay(tmp_path: Path) -> None:
    result_env = tmp_path / ".step3-review-result.env"
    _ = result_env.write_text("WARN=selected-warning\nLOOP_STATUS=complete\n", encoding="utf-8")
    output = tmp_path / "quoted.env"
    out = io.StringIO()
    argv = [
        "--input",
        str(result_env),
        "--allow",
        "LOOP_STATUS",
        "--output",
        str(output),
    ]
    with contextlib.redirect_stdout(out):
        rc, selected, primary_regular = plan_review._step3_read_result_env_quiet(argv)  # pyright: ignore[reportPrivateUsage]
    assert rc == 0
    assert selected == result_env
    assert primary_regular is True
    assert out.getvalue() == ""


def test_step3_normalizer_primary_warn_only_replays_primary_before_overlay(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "WARN=primary-only-warning\nLOOP_STATUS=complete\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(tmp_path, "WARN=overlay-warning\nLOOP_STATUS=complete\n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[:2] == ["WARN=primary-only-warning", "WARN=overlay-warning"]


def test_step3_normalizer_warn_replay_skips_duplicate_stdout_overlay_on_recovery(tmp_path: Path) -> None:
    result_env = tmp_path / ".step3-review-result.env"
    result_env.symlink_to("/nonexistent/step3-review-result.env")
    proc = _run_step3_normalizer(tmp_path, "WARN=fallback-warning\nLOOP_STATUS=complete\n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.count("WARN=fallback-warning") == 1


def test_step3_normalizer_escalation_evidence_failure_contract(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "plan-review" / "round-1").mkdir(parents=True)
    _ = (tmp_path / "plan-review" / "round-1" / "reviewer-output.txt").write_text("x\n", encoding="utf-8")
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=tally-error\nLOOP_STATUS=tally-error\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n",
        encoding="utf-8",
    )
    stdout_file = tmp_path / "plan-review.stdout"
    _ = stdout_file.write_text("", encoding="utf-8")

    def fake_record_report_evidence(*_args: object, **_kwargs: object) -> int:
        logging_util.emit_kv(key="WARN", value="Step 3: failed to record design escalation evidence for tally-error")
        return 1

    monkeypatch.setattr(plan_review, "step3_record_report_evidence", fake_record_report_evidence)
    out = io.StringIO()
    stderr = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(stderr):
        rc = plan_review.normalize_step3_status_main(  # pyright: ignore[reportPrivateUsage]
            ["--design-tmpdir", str(tmp_path), "--stdout-file", str(stdout_file), "--loop-rc", "0"]
        )
    stdout_text = out.getvalue()
    stderr_text = stderr.getvalue()
    assert rc == 0
    assert "WARN=" not in stdout_text
    assert "STEP3_REVIEW_LOOP_STATUS=tally-error" in stdout_text
    assert "**⚠ Step 3: failed to record escalation evidence for tally-error**" in stderr_text


def test_step3_normalize_mkstemp_allocation_failure_aborts(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stdout_file = tmp_path / "plan-review.stdout"
    _ = stdout_file.write_text("LOOP_STATUS=complete\n", encoding="utf-8")
    real_mkstemp = tempfile.mkstemp

    def failing_mkstemp(*args: object, **kwargs: object) -> tuple[int, str]:
        if kwargs.get("prefix") == "larch-step3-review-env.":
            raise OSError("no space left on device")
        return real_mkstemp(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(plan_review.tempfile, "mkstemp", failing_mkstemp)
    stderr = io.StringIO()
    with contextlib.redirect_stderr(stderr):
        rc = plan_review.normalize_step3_status_main(  # pyright: ignore[reportPrivateUsage]
            ["--design-tmpdir", str(tmp_path), "--stdout-file", str(stdout_file), "--loop-rc", "0"]
        )
    assert rc == 1
    assert "could not allocate safe step3 review result env" in stderr.getvalue()


def test_step3_normalizer_warn_replay_and_overlay_contract(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text("WARN=selected-warning\nLOOP_STATUS=complete\n", encoding="utf-8")
    proc = _run_step3_normalizer(tmp_path, "WARN=overlay-warning\n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[:2] == ["WARN=selected-warning", "WARN=overlay-warning"]
    assert proc.stdout.count("WARN=selected-warning") == 1

    other = tmp_path / "missing-primary"
    other.mkdir()
    proc = _run_step3_normalizer(other, "WARN=fallback-warning\nLOOP_STATUS=complete\n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.count("WARN=fallback-warning") == 1


def test_step3_normalizer_loads_quoted_env_and_overlays_spaced_values(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "LOOP_STATUS=complete\nDEGRADED_PANEL_WARNING=primary warning with spaces\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(tmp_path, "INVALID_SLOT_PANEL_WARNING=overlay warning with spaces\n")
    assert proc.returncode == 0, proc.stderr
    assert "DEGRADED_PANEL_WARNING=primary warning with spaces" in proc.stdout
    assert "INVALID_SLOT_PANEL_WARNING=overlay warning with spaces" in proc.stdout


def test_step3_normalizer_status_mapping_and_panel_init_identity(tmp_path: Path) -> None:
    (tmp_path / "plan-review" / "round-1").mkdir(parents=True)
    _ = (tmp_path / "plan-review" / "round-1" / "reviewer-output.txt").write_text("x\n", encoding="utf-8")
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=panel-failed\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n")
    assert "NEXT_ACTION=step3b-bypass" in proc.stdout
    assert "STEP3_REVIEW_LOOP_STATUS=panel-failed" in proc.stdout
    assert "LOOP_STATUS=panel-failed" in proc.stdout

    zfdp = tmp_path / "zfdp"
    zfdp.mkdir()
    proc = _run_step3_normalizer(zfdp, "LOOP_STATUS=zero-findings-degraded-panel\n")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "NEXT_ACTION=step3b"
    assert "LOOP_STATUS=zero-findings-degraded-panel" in proc.stdout
    assert "STEP3_REVIEW_LOOP_STATUS=" not in proc.stdout
    assert "result env missing" not in proc.stderr

    persisted = tmp_path / "persisted"
    persisted.mkdir()
    _ = (persisted / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=panel-init-failed\nLOOP_STATUS=complete\nROUNDS_COMPLETED=1\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(persisted)
    assert proc.returncode == 1
    assert proc.stdout.splitlines()[0] == "NEXT_ACTION=final-summary:failed-judge-panel"
    assert "STEP3_REVIEW_LOOP_STATUS=panel-init-failed" in proc.stdout
    assert "LOOP_STATUS=panel-init-failed" in proc.stdout
    assert "SUMMARY_OUTCOME=failed-judge-panel" in proc.stdout


def test_step3_normalizer_zero_round_and_synthesis_paths(tmp_path: Path) -> None:
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=panel-failed\nROUNDS_COMPLETED=0\nREVIEW_ROUND_COUNT=0\n")
    assert proc.returncode == 1
    assert "STEP3_REVIEW_LOOP_STATUS=panel-init-failed" in proc.stdout
    assert "SUMMARY_OUTCOME=failed-judge-panel" in proc.stdout
    result_text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "STEP3_REVIEW_CAP_REACHED=false" in result_text
    assert "ROUNDS_COMPLETED=0" in result_text

    launched = tmp_path / "launched"
    (launched / "plan-review" / "round-1").mkdir(parents=True)
    _ = (launched / "plan-review" / "round-1" / "reviewer-output.txt").write_text("x\n", encoding="utf-8")
    proc = _run_step3_normalizer(launched, "LOOP_STATUS=tally-error\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n")
    assert proc.returncode == 0
    result_text = (launched / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "STEP3_REVIEW_LOOP_STATUS=tally-error" in result_text
    assert "STEP3_REVIEW_CAP_REACHED=false" in result_text
    assert (launched / ".step3-terminal-persisted-this-run").is_file()


def test_step3_normalizer_writes_terminal_sentinel_on_normal_complete_path(tmp_path: Path) -> None:
    # #5418 Fix A: sentinel written before emit; sidecar NOT written so EXIT
    # trap cannot mint step-3 (deferred Gate B milestone).
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert not (tmp_path / ".step3-terminal-persisted-this-run").exists()


def test_step3_normalizer_writes_sentinel_from_stdout_status_without_result_env(tmp_path: Path) -> None:
    # #5418 Fix A: even with no result env (e.g., cleared by auto-continuation
    # before the loop was killed), normalize writes step-3-terminal when the
    # merged status resolves to a terminal value from the stdout content.
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert not (tmp_path / ".step3-terminal-persisted-this-run").exists()


def test_step3_normalizer_no_sentinel_for_interactive_status(tmp_path: Path) -> None:
    # #5418 Fix A guard: interactive mid-loop statuses must NOT trigger sentinel write.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nLOOP_STATUS=main-agent-vote-required\nROUNDS_COMPLETED=1\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=main-agent-vote-required\nROUNDS_COMPLETED=1\n")
    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / ".completed" / "step-3-terminal").exists()
    assert not (tmp_path / ".step3-terminal-persisted-this-run").exists()


def test_step3_normalizer_sentinel_before_kv_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # #5418: reordering sentinel write after emit would pass post-exit checks but
    # restore premature-notification WAIT loops; pin ordering at emit entry.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n",
        encoding="utf-8",
    )
    stdout_file = tmp_path / "plan-review.stdout"
    _ = stdout_file.write_text("LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    sentinel_seen = False
    original = plan_review._step3_emit_normalize_envelope_with_next_action  # pyright: ignore[reportPrivateUsage]

    def _assert_sentinel_before_emit(tmpdir: Path, *, values: dict[str, str]) -> None:
        nonlocal sentinel_seen
        sentinel_seen = (tmpdir / ".completed" / "step-3-terminal").is_file()
        original(tmpdir=tmpdir, values=values)

    monkeypatch.setattr(plan_review, "_step3_emit_normalize_envelope_with_next_action", _assert_sentinel_before_emit)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = plan_review.normalize_step3_status_main(
            ["--design-tmpdir", str(tmp_path), "--stdout-file", str(stdout_file), "--loop-rc", "0"]
        )
    assert rc == 0
    assert sentinel_seen


def test_step3_normalizer_empty_primary_replays_stdout_fallback_warn_error(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_bytes(b"")
    proc = _run_step3_normalizer(
        tmp_path,
        "WARN=fallback-warning\nERROR=fallback-error\nLOOP_STATUS=complete\n",
    )
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert lines[0] == "WARN=fallback-warning"
    assert "ERROR=fallback-error" in lines[:3]
    assert proc.stdout.count("WARN=fallback-warning") == 1


def test_step3_normalizer_missing_result_kv_only_stderr(tmp_path: Path) -> None:
    proc = _run_step3_normalizer(tmp_path, "")
    assert proc.returncode == 1
    assert "**⚠ Step 3:" not in proc.stdout
    assert "**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**" in proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=panel-init-failed" in proc.stdout
    assert "SUMMARY_OUTCOME=failed-judge-panel" in proc.stdout


def test_step3_normalizer_postplan_invalid_and_kv_only_stderr(tmp_path: Path) -> None:
    postplan = tmp_path / "postplan"
    postplan.mkdir()
    proc = _run_step3_normalizer(postplan, "STEP3_REVIEW_LOOP_STATUS=postplan-failed\nPOSTPLAN_RC=1\nLOOP_STATUS=postplan-failed\n")
    assert proc.returncode == 1
    assert proc.stdout.splitlines()[0] == "NEXT_ACTION=final-summary:failed-postplan"
    assert "SUMMARY_OUTCOME=failed-postplan" in proc.stdout

    invalid = tmp_path / "invalid"
    invalid.mkdir()
    proc = _run_step3_normalizer(invalid, "STEP3_REVIEW_LOOP_STATUS=not-a-status\n")
    assert proc.returncode == 1
    assert "**⚠ Step 3:" not in proc.stdout
    assert "**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS" in proc.stderr


def test_step3_normalizer_next_action_map_persists(tmp_path: Path) -> None:
    cases = {
        "complete": "step3b",
        "cap-hit": "step3b-bypass",
        "main-agent-vote-required": "mav",
        "main-agent-apply-required": "gate-b",
        "per-round-approval-required": "gate-b",
        "postplan-operator-required": "postplan-operator",
        "panel-failed": "step3b-bypass",
        "tally-error": "step3b-bypass",
        "degraded-empty-collector": "step3b-bypass",
    }
    for status, expected in cases.items():
        design = tmp_path / status
        design.mkdir(parents=True)
        env_file = design / ".step3-review-result.env"
        _ = env_file.write_text(
            f"STEP3_REVIEW_LOOP_STATUS={status}\nLOOP_STATUS={status}\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n",
            encoding="utf-8",
        )
        action = plan_review._step3_next_action(status)  # pyright: ignore[reportPrivateUsage]
        assert action == expected
        plan_review._step3_persist_next_action(design, action=action)  # pyright: ignore[reportPrivateUsage]
        assert env_file.read_text(encoding="utf-8").splitlines()[0] == f"NEXT_ACTION={expected}"


def test_step3_normalizer_static_contract_pins() -> None:
    body = (ROOT / "python" / "larch" / "review" / "plan_review.py").read_text(encoding="utf-8")
    assert "SUMMARY_OUTCOME=failed-postplan" in body
    assert "SUMMARY_OUTCOME=failed-judge-panel" in body
    assert "load_bash_quoted_env" in body
    assert "_step3_read_result_env_quiet" in body
    assert "_step3_next_action" in body
    assert "file=sys.stderr" in body

def test_step3_loop_persist_envelope_merges_and_strips_reason(tmp_path: Path) -> None:
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "TALLY_PLAN_REVIEW_STATUS=ok\nAGGREGATOR_STATUS=ok\nPLAN_REVIEW_CONTINUE_REASON=again\r\n",
        encoding="utf-8",
    )
    plan_review.step3_loop_persist_envelope(
        design_tmpdir=tmp_path, status="main-agent-vote-required", round_num=2, rounds_completed=2, final_round=2,
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
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values=values)
    text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in text

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        plan_review.step3_loop_emit_envelope(tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values=values)

    assert "DEGRADED_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in out.getvalue()


def test_step3_loop_persist_envelope_persists_and_emits_invalid_slot_panel_warning(tmp_path: Path) -> None:
    values = {
        "LOOP_STATUS": "complete",
        "INVALID_SLOT_PANEL_WARNING": "**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**",
    }
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values=values)
    text = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "INVALID_SLOT_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in text

    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        plan_review.step3_loop_emit_envelope(tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values=values)

    assert "INVALID_SLOT_PANEL_WARNING=**⚠ Degraded plan-review panel: 1 invalid slot row(s) dropped.**" in out.getvalue()


def test_step3_loop_persist_envelope_writes_terminal_sentinels(tmp_path: Path) -> None:
    # #4688 hook-release contract: persisting the result env writes the
    # step-3-terminal sentinel pair so hook-bg-poll-guard.sh releases the marker.
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values={})
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert (tmp_path / ".step3-terminal-persisted-this-run").is_file()


def test_step3_loop_persist_envelope_terminal_without_step3_on_midloop_bail(tmp_path: Path) -> None:
    # Mid-loop bail-outs write step-3-terminal (hook release) but not step-3
    # (the pause / Gate B milestone), per the split-sentinel contract.
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="main-agent-apply-required", round_num=2, rounds_completed=2, final_round=2, values={})
    assert (tmp_path / ".completed" / "step-3-terminal").is_file()
    assert (tmp_path / ".step3-terminal-persisted-this-run").is_file()
    assert not (tmp_path / ".completed" / "step-3").exists()


def test_phase_driver_write_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / ".step3-review-result.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="symlink"):
        plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values={})


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
    assert plan_review.drift_baseline_write_once(design_tmpdir=tmp_path, plan_lines="10", diff_lines="20") == 0
    assert (tmp_path / "drift-baseline.env").read_text(encoding="utf-8") == (
        "BASELINE_PLAN_LINES=10\nBASELINE_DIFF_LINES=20\n"
    )
    assert plan_review.drift_baseline_write_once(design_tmpdir=tmp_path, plan_lines="99", diff_lines="99") == 0
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
        assert plan_review.persist_design_round_start_s(design_tmpdir=disallowed, round_num=1, start_s=100) == 1
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
    assert plan_review.drift_baseline_write_once(design_tmpdir=tmp_path, plan_lines="10", diff_lines="20") == 0
    assert baseline.is_file()
    assert baseline.read_text(encoding="utf-8") == (
        "BASELINE_PLAN_LINES=10\nBASELINE_DIFF_LINES=20\n"
    )


def test_drift_baseline_rejects_invalid_line_counts(tmp_path: Path) -> None:
    assert plan_review.drift_baseline_write_once(design_tmpdir=tmp_path, plan_lines="10\n", diff_lines="20") == 1
    assert plan_review.drift_baseline_write_once(design_tmpdir=tmp_path, plan_lines="10", diff_lines="bad") == 1
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


def test_run_round_body_subprocess_materializes_reviewer_status(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subprocess stub omitting reviewer-status.tsv still materializes per-round + latest (#4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_file = round_dir / "cursor-plan-arch-output.txt"
    _ = (design / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
        + str(reviewer_file)
        + '","prompt_file":"'
        + str(design / "cursor-plan-arch.prompt")
        + '"}\n',
        encoding="utf-8",
    )
    _ = (design / "collector-results.env").write_text(
        f"REVIEWER_FILE={reviewer_file}\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    stub = _write_loop_stub(
        design,
        "printf 'LOOP_STATUS=complete\\nTALLY_PLAN_REVIEW_STATUS=ok\\nAGGREGATOR_STATUS=ok\\n'; exit 0",
    )
    monkeypatch.setenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", str(stub))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")

    body_rc, _values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    round_status = round_dir / "reviewer-status.tsv"
    latest = design / "latest-reviewer-status.tsv"
    stable_table = design / "reviewer-status-table.txt"
    assert body_rc == 0
    assert round_status.is_file()
    assert latest.is_file()
    assert stable_table.is_file()
    lines = round_status.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "slot\tstatus\telapsed"
    assert lines[1] == "Cursor-Arch\tdone\t"
    assert stable_table.read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ |"


def test_run_round_body_subprocess_pre_collection_ignores_stale_collector(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Pre-collection subprocess stub must not reuse stale collector-results.env (#4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_file = round_dir / "cursor-plan-arch-output.txt"
    _ = (design / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
        + str(reviewer_file)
        + '","prompt_file":"'
        + str(design / "cursor-plan-arch.prompt")
        + '"}\n',
        encoding="utf-8",
    )
    _ = (design / "collector-results.env").write_text(
        f"REVIEWER_FILE={reviewer_file}\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    stub = _write_loop_stub(
        design,
        (
            "printf 'LOOP_STATUS=panel-failed\\nTALLY_PLAN_REVIEW_STATUS=panel-failed\\n"
            "AGGREGATOR_STATUS=skipped\\nDEGRADED_PANEL=1\\n'; exit 1"
        ),
    )
    monkeypatch.setenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", str(stub))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")

    body_rc, _values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    round_status = round_dir / "reviewer-status.tsv"
    assert body_rc == 1
    assert round_status.is_file()
    assert round_status.read_text(encoding="utf-8").splitlines()[1] == "Cursor-Arch\tskipped\t"


def test_run_round_body_subprocess_unlinks_dangling_status_symlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Dangling reviewer-status.tsv symlink must not block subprocess materialization (#4848)."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_file = round_dir / "cursor-plan-arch-output.txt"
    _ = (design / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
        + str(reviewer_file)
        + '","prompt_file":"'
        + str(design / "cursor-plan-arch.prompt")
        + '"}\n',
        encoding="utf-8",
    )
    _ = (round_dir / "reviewer-status.tsv").symlink_to("/nonexistent/reviewer-status.tsv")
    stub = _write_loop_stub(
        design,
        (
            "printf 'LOOP_STATUS=panel-failed\\nTALLY_PLAN_REVIEW_STATUS=panel-failed\\n"
            "AGGREGATOR_STATUS=skipped\\nDEGRADED_PANEL=1\\n'; exit 1"
        ),
    )
    monkeypatch.setenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", str(stub))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")

    body_rc, _values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    round_status = round_dir / "reviewer-status.tsv"
    latest = design / "latest-reviewer-status.tsv"
    stable_table = design / "reviewer-status-table.txt"
    assert body_rc == 1
    assert round_status.is_file()
    assert not round_status.is_symlink()
    assert latest.is_file()
    assert latest.read_text(encoding="utf-8").splitlines()[0] == "slot\tstatus\telapsed"
    assert stable_table.is_file()
    assert stable_table.read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ⊘ |"


def test_run_round_body_subprocess_refreshes_stale_stable_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Subprocess-written reviewer-status.tsv refreshes prior-round stable table."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-2"
    round_dir.mkdir(parents=True)
    _ = (design / "reviewer-status-table.txt").write_text("📊 Reviewers: | Cursor-Old: ✅ |\n", encoding="utf-8")
    _ = (design / ".step3-review-result.env").write_text("FINAL_ROUND_NUM=1\n", encoding="utf-8")
    status = round_dir / "reviewer-status.tsv"
    stub = _write_loop_stub(
        design,
        (
            "cat > "
            + str(status)
            + " <<'EOF'\nslot\tstatus\telapsed\nCodex-Arch\tfailed\t2m\nEOF\n"
            "printf 'LOOP_STATUS=complete\\nTALLY_PLAN_REVIEW_STATUS=ok\\nAGGREGATOR_STATUS=ok\\n'; exit 0"
        ),
    )
    monkeypatch.setenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", str(stub))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")

    body_rc, _values = plan_review._run_round_body(tmpdir=design, round_num=2)  # pyright: ignore[reportPrivateUsage]

    assert body_rc == 0
    assert (design / "reviewer-status-table.txt").read_text(encoding="utf-8").strip() == "📊 Reviewers: | Codex-Arch: ❌ 2m |"


def test_run_round_body_subprocess_symlinked_round_tsv_clears_stale_stable_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Symlinked per-round reviewer-status.tsv must not leave a stale stable table."""
    design = tmp_path
    round_dir = design / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    reviewer_file = round_dir / "cursor-plan-arch-output.txt"
    _ = (design / "plan-review-slots.ndjson").write_text(
        '{"slot":"cursor-plan-arch","tool":"cursor","output":"'
        + str(reviewer_file)
        + '","prompt_file":"'
        + str(design / "cursor-plan-arch.prompt")
        + '"}\n',
        encoding="utf-8",
    )
    _ = (design / "collector-results.env").write_text(
        f"REVIEWER_FILE={reviewer_file}\nTOOL=cursor\nSTATUS=OK\nEXIT_CODE=0\n\n",
        encoding="utf-8",
    )
    _ = (design / "reviewer-status-table.txt").write_text("📊 Reviewers: | Cursor-Old: ✅ |\n", encoding="utf-8")
    external = tmp_path / "external-status.tsv"
    _ = external.write_text("slot\tstatus\telapsed\nCursor-Arch\tdone\t\n", encoding="utf-8")
    _ = (round_dir / "reviewer-status.tsv").symlink_to(external)
    stub = _write_loop_stub(
        design,
        "printf 'LOOP_STATUS=complete\\nTALLY_PLAN_REVIEW_STATUS=ok\\nAGGREGATOR_STATUS=ok\\n'; exit 0",
    )
    monkeypatch.setenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", str(stub))
    monkeypatch.setenv("LARCH_QUIET_DISABLE", "1")

    body_rc, _values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    round_status = round_dir / "reviewer-status.tsv"
    stable_table = design / "reviewer-status-table.txt"
    assert body_rc == 0
    assert round_status.is_file()
    assert not round_status.is_symlink()
    assert stable_table.is_file()
    assert stable_table.read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ |"


def test_run_round_body_in_process_tail_refreshes_stale_stable_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In-process round body tail re-materializes when a stale stable table remains."""
    design = tmp_path
    _ = (design / "reviewer-status-table.txt").write_text("📊 Reviewers: | Cursor-Old: ✅ |\n", encoding="utf-8")

    def fake_run_plan_review_round(_argv: list[str]) -> int:
        round_dir = design / "plan-review" / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        _ = (round_dir / "reviewer-status.tsv").write_text(
            "slot\tstatus\telapsed\nCursor-Arch\tdone\t3m\n",
            encoding="utf-8",
        )
        print("LOOP_STATUS=complete")
        print("TALLY_PLAN_REVIEW_STATUS=ok")
        return 0

    monkeypatch.delenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", raising=False)
    monkeypatch.setattr(plan_review, "run_plan_review_round", fake_run_plan_review_round)

    body_rc, values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    assert body_rc == 0
    assert values["LOOP_STATUS"] == "complete"
    assert (design / "reviewer-status-table.txt").read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ 3m |"


def test_run_round_body_in_process_tail_materializes_missing_stable_table(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """In-process round body tail materializes the stable table from an existing round TSV."""
    design = tmp_path

    def fake_run_plan_review_round(_argv: list[str]) -> int:
        round_dir = design / "plan-review" / "round-1"
        round_dir.mkdir(parents=True, exist_ok=True)
        _ = (round_dir / "reviewer-status.tsv").write_text(
            "slot\tstatus\telapsed\nCursor-Arch\tdone\t3m\n",
            encoding="utf-8",
        )
        print("LOOP_STATUS=complete")
        print("TALLY_PLAN_REVIEW_STATUS=ok")
        return 0

    monkeypatch.delenv("RUN_STEP3_PLAN_REVIEW_LOOP_SH", raising=False)
    monkeypatch.setattr(plan_review, "run_plan_review_round", fake_run_plan_review_round)

    body_rc, values = plan_review._run_round_body(tmpdir=design, round_num=1)  # pyright: ignore[reportPrivateUsage]

    assert body_rc == 0
    assert values["LOOP_STATUS"] == "complete"
    assert (design / "reviewer-status-table.txt").read_text(encoding="utf-8").strip() == "📊 Reviewers: | Cursor-Arch: ✅ 3m |"


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
    assert "NEXT_ACTION=step3b-bypass" in proc.stdout
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
    assert "NEXT_ACTION=step3b-bypass" in proc.stdout
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
    assert "NEXT_ACTION=step3b-bypass" in proc.stdout
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
    assert plan_review_env.splitlines()[0] == "NEXT_ACTION=step3b-bypass"
    assert review_env.splitlines()[0] == "NEXT_ACTION=step3b-bypass"
    assert "TALLY_PLAN_REVIEW_STATUS=tally-error" in plan_review_env
    assert "LOOP_STATUS=complete" in review_env
    assert not (tmp_path / "accepted-plan-findings.md").read_text(encoding="utf-8").strip()
    assert "ACCEPTED_COUNT=0" in plan_review_env
    assert "IMPORTANT_ACCEPTED_COUNT=0" in review_env


def test_step3_normalize_preserves_mav_tally_error_bypass(tmp_path: Path) -> None:
    """Re-normalizing a MAV tally-error persisted env must keep NEXT_ACTION=step3b-bypass."""
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
        "--tally-plan-review-status",
        "tally-error",
        "--loop-status",
        "complete",
    )
    assert proc.returncode == 0, proc.stderr
    proc = _run_step3_normalizer(tmp_path)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines()[0] == "NEXT_ACTION=step3b-bypass"
    assert "LOOP_STATUS=complete" in proc.stdout
    assert "TALLY_PLAN_REVIEW_STATUS=tally-error" in proc.stdout
    result_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert result_env.splitlines()[0] == "NEXT_ACTION=step3b-bypass"


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
    assert "NEXT_ACTION=" not in plan_review_env
    assert "NEXT_ACTION=" not in review_env


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


def test_tally_plan_review_unique_finder_bonus_with_neutralized_attribution(tmp_path: Path) -> None:
    attributed_text = """### FINDING_1: Sole in-scope
- **Reviewer**: Cursor-Arch
- focus-area = correctness
- Concern: parser misses bad input.

### FINDING_2: Shared in-scope
- **Reviewer(s)**: Codex-Arch, Cursor-Testing
- focus-area = correctness
- Concern: shared issue.

### OOS_1: Future docs
- **Reviewer**: Codex-OOS
- focus-area = documentation
- Concern: docs follow-up.
"""
    attributed = tmp_path / "attributed.md"
    _ = attributed.write_text(attributed_text, encoding="utf-8")
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(attributed_text, encoding="utf-8")
    proposer_map = tmp_path / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=ballot, map_file=proposer_map)
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed_text), encoding="utf-8")

    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    votes = "FINDING_1: YES SEVERITY=minor\nFINDING_2: YES SEVERITY=minor\nOOS_1: YES SEVERITY=major\n"
    for voter in (v1, v2, v3):
        _ = voter.write_text(votes, encoding="utf-8")

    design_default = tmp_path / "design-default"
    design_default.mkdir()
    default_proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(v1),
        str(v2),
        str(v3),
        "--design-tmpdir",
        str(design_default),
        "--proposer-map-file",
        str(proposer_map),
        env={"LARCH_QUIET_DISABLE": "1", "LARCH_UNIQUE_FINDER_BONUS": ""},
    )
    assert default_proc.returncode == 0, default_proc.stderr
    default_tally = (design_default / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Cursor-Arch | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in default_tally
    assert "Unique finder bonus active" not in default_tally

    design_active = tmp_path / "design-active"
    design_active.mkdir()
    active_proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(v1),
        str(v2),
        str(v3),
        "--design-tmpdir",
        str(design_active),
        "--proposer-map-file",
        str(proposer_map),
        env={"LARCH_QUIET_DISABLE": "1", "LARCH_UNIQUE_FINDER_BONUS": "0.25"},
    )
    assert active_proc.returncode == 0, active_proc.stderr
    tally = (design_active / "voting-tally.md").read_text(encoding="utf-8")
    assert "| Cursor-Arch | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1.25 |" in tally
    assert "| Codex-Arch | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in tally
    assert "| Cursor-Testing | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 1 |" in tally
    assert "| Codex-OOS | 0 | 0 | 0 | 0 | 1 | 1 | 0 | 0 | 1 |" in tally
    assert "**Unique finder bonus active:** 1 accepted in-scope sole-finder finding(s) received +0.25 each." in tally
    accepted = (design_active / "accepted-plan-findings.md").read_text(encoding="utf-8")
    assert "- **Reviewer**: Cursor-Arch" in accepted
    assert "anonymous" not in accepted


def test_tally_plan_review_mixed_votes_and_artifacts(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    _ = ballot.write_text(
        ballot.read_text(encoding="utf-8")
        + """
### FINDING_3: Consensus high impact
- **Reviewer**: Codex-High
- focus-area = correctness
- Concern: consensus high case.
""",
        encoding="utf-8",
    )
    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    _ = v1.write_text("FINDING_1: YES SEVERITY=major\nFINDING_2: NO SEVERITY=major\nFINDING_3: YES SEVERITY=major\nOOS_1: YES SEVERITY=major\nOOS_2: YES SEVERITY=major\n", encoding="utf-8")
    _ = v2.write_text("FINDING_1: YES SEVERITY=minor\nFINDING_2: YES SEVERITY=minor\nFINDING_3: YES SEVERITY=blocker\nOOS_1: NO SEVERITY=major\nOOS_2: YES SEVERITY=major\n", encoding="utf-8")
    _ = v3.write_text("FINDING_1: YES SEVERITY=minor\nFINDING_2: NO SEVERITY=blocker\nFINDING_3: YES SEVERITY=major\nOOS_1: YES SEVERITY=major\nOOS_2: YES SEVERITY=major\n", encoding="utf-8")
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
    assert "| Codex-High | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 2 |" in tally
    assert "| Codex-Pragmatic | 1 | 0 | 1 | 0 | 0 | 0 | 0 | 0 | -0.25 |" in tally
    class_rows = _read_tsv(design / "plan-review" / "round-1" / "findings-classification.tsv") if (design / "plan-review" / "round-1" / "findings-classification.tsv").is_file() else _read_tsv(design / "findings-classification.tsv")
    assert class_rows["FINDING_1"]["scope"] == "in_scope"
    assert class_rows["OOS_1"]["scope"] == "oos"
    ledger_rows = _read_tsv(design / "findings-ledger.tsv")
    assert ledger_rows["FINDING_1"]["outcome"] == "accepted"
    assert ledger_rows["FINDING_2"]["outcome"] == "neutral"
    assert ledger_rows["OOS_1"]["outcome"] == "oos"
    assert "proposer" not in (design / "findings-ledger.tsv").read_text(encoding="utf-8").splitlines()[0]
    class_tsv = design / "plan-review" / "round-1" / "findings-classification.tsv"
    tsv_records = voting.compute_voter_agreement(
        voting.voter_agreement_rows_from_tsv(class_tsv.read_text(encoding="utf-8"), panel_kind="design").rows
    )
    assert "## Voter Agreement Scoreboard" in tally
    for record in tsv_records:
        rate = "n/a" if record["agreement_rate"] is None else f"{float(record['agreement_rate']):.3f}"  # pyright: ignore[reportArgumentType]
        line = (
            f"| design | {record['voter']} | {record['eligible']} | {record['agree']} | "
            f"{record['disagree']} | {record['missing']} | {rate} | "
            f"{str(bool(record['outlier'])).lower()} |"
        )
        assert line in tally
    severity_records = voting.compute_voter_severity_distribution(
        voting.voter_agreement_rows_from_tsv(class_tsv.read_text(encoding="utf-8"), panel_kind="design").rows
    )
    assert voting.render_voter_severity_scoreboard(severity_records) in tally


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
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "fake agreement" not in tally
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")
    assert "| undefined | n/a | 0 | 0 | 0 | 0 | n/a | false |" in tally
    assert not (design / "findings-ledger.tsv").exists()


def test_tally_plan_review_main_agent_sole_voter_severity_scoreboard(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    main_vote = tmp_path / "main-agent-vote.txt"
    _ = main_vote.write_text("FINDING_1: YES SEVERITY=major\n", encoding="utf-8")
    design = tmp_path / "design-main-agent"
    design.mkdir()
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter",
        f"MainAgent:{main_vote}",
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "TALLY_PLAN_REVIEW_STATUS=ok" in proc.stdout
    assert "ValueError" not in proc.stderr
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")


def test_tally_plan_review_rescues_high_severity_neutral_findings_to_oos(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(
        """### FINDING_1: High severity neutral
- **Reviewer**: Codex-Correctness
- focus-area = correctness
- Concern: High severity single-YES concern.

### FINDING_2: Nit neutral
- **Reviewer**: Cursor-Testing
- focus-area = testing
- Concern: Low severity single-YES concern.
""",
        encoding="utf-8",
    )
    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    _ = v1.write_text(
        "FINDING_1: YES SEVERITY=major\n"
        "FINDING_2: YES SEVERITY=nit\n",
        encoding="utf-8",
    )
    for voter in (v2, v3):
        _ = voter.write_text(
            "FINDING_1: NO SEVERITY=nit\n"
            "FINDING_2: NO SEVERITY=nit\n",
            encoding="utf-8",
        )
    design = tmp_path / "design-neutral-rescue"
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
    oos = (design / "oos.md").read_text(encoding="utf-8")
    rejected = (design / "rejected-findings.md").read_text(encoding="utf-8")
    accepted = (design / "accepted-plan-findings.md").read_text(encoding="utf-8")
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "FINDING_1" in oos
    assert "neutral-rescued" in oos
    assert "FINDING_1" not in rejected
    assert "FINDING_2" in rejected
    assert accepted == ""
    assert "| FINDING_1 | 1 | 2 | 0 | neutral |" in tally
    assert "| FINDING_2 | 1 | 2 | 0 | neutral |" in tally
    rows = _read_tsv(design / "plan-review" / "round-1" / "findings-classification.tsv")
    assert rows["FINDING_1"]["scope"] == "oos"
    assert rows["FINDING_1"]["voting_result"] == "neutral"
    assert rows["FINDING_2"]["scope"] == "in_scope"
    assert rows["FINDING_2"]["voting_result"] == "neutral"
    ledger_rows = _read_tsv(design / "findings-ledger.tsv")
    assert ledger_rows["FINDING_1"]["outcome"] == "oos"


def test_tally_plan_review_rejected_latent_ledger_outcome_is_oos(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _ = ballot.write_text(
        """### FINDING_1: Latent deferred item
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- Concern: Real but latent concern.
""",
        encoding="utf-8",
    )
    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    for voter in (v1, v2, v3):
        _ = voter.write_text("FINDING_1: NO\n", encoding="utf-8")
    design = tmp_path / "design-latent"
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
    ledger_rows = _read_tsv(design / "findings-ledger.tsv")
    assert ledger_rows["FINDING_1"]["outcome"] == "oos"
    oos = (design / "oos.md").read_text(encoding="utf-8")
    rejected = (design / "rejected-findings.md").read_text(encoding="utf-8")
    assert "FINDING_1" in oos
    assert "latent-rerouted" in oos
    assert "FINDING_1" not in rejected


def test_tally_plan_review_ledger_appends_and_replaces_round(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    v1 = tmp_path / "v1.txt"
    v2 = tmp_path / "v2.txt"
    v3 = tmp_path / "v3.txt"
    for voter in (v1, v2, v3):
        _ = voter.write_text("FINDING_1: YES\nFINDING_2: NO\nOOS_1: YES\nOOS_2: NO\n", encoding="utf-8")
    design = tmp_path / "design-ledger"
    design.mkdir()

    for round_num in (1, 2):
        out = design / "plan-review" / f"round-{round_num}" / "findings-classification.tsv"
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
            "--findings-classification-out",
            str(out),
            env={"LARCH_QUIET_DISABLE": "1"},
        )
        assert proc.returncode == 0, proc.stderr

    rows = _read_tsv_list(design / "findings-ledger.tsv")
    assert [row["round"] for row in rows] == ["1", "1", "1", "1", "2", "2", "2", "2"]

    _ = v1.write_text("FINDING_1: NO\nFINDING_2: NO\nOOS_1: NO\nOOS_2: NO\n", encoding="utf-8")
    out = design / "plan-review" / "round-2" / "findings-classification.tsv"
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
        "--findings-classification-out",
        str(out),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    rows = _read_tsv_list(design / "findings-ledger.tsv")
    assert [row["round"] for row in rows] == ["1", "1", "1", "1", "2", "2", "2", "2"]


def test_tally_plan_review_degraded_two_judge_voter_agreement_parity(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    v1 = tmp_path / "claude-vote-output.txt"
    v2 = tmp_path / "codex-vote-output.txt"
    _ = v1.write_text("FINDING_1: YES\nFINDING_2: NO\nOOS_1: YES\nOOS_2: YES\n", encoding="utf-8")
    _ = v2.write_text("FINDING_1: YES\nFINDING_2: YES\nOOS_1: NO\nOOS_2: YES\n", encoding="utf-8")
    design = tmp_path / "design-two-judge"
    design.mkdir()
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter-files",
        str(v1),
        str(v2),
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    class_tsv = design / "plan-review" / "round-1" / "findings-classification.tsv"
    records = voting.compute_voter_agreement(
        voting.voter_agreement_rows_from_tsv(class_tsv.read_text(encoding="utf-8"), panel_kind="design").rows
    )
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    cursor = next(record for record in records if record["voter"] == "Cursor")
    assert cursor["missing"] > 0  # type: ignore[reportOperatorIssue]
    assert (
        f"| design | Cursor | {cursor['eligible']} | {cursor['agree']} | "
        f"{cursor['disagree']} | {cursor['missing']} |"
    ) in tally
    severity_records = voting.compute_voter_severity_distribution(
        voting.voter_agreement_rows_from_tsv(class_tsv.read_text(encoding="utf-8"), panel_kind="design").rows
    )
    assert voting.render_voter_severity_scoreboard(severity_records) in tally


def test_tally_plan_review_missing_middle_slot_severity_alignment(tmp_path: Path) -> None:
    ballot = tmp_path / "ballot.md"
    _write_tally_ballot(ballot)
    v1 = tmp_path / "slot1.txt"
    v3 = tmp_path / "slot3.txt"
    _ = v1.write_text("FINDING_1: YES SEVERITY=major\nFINDING_2: NO SEVERITY=nit\nOOS_1: YES SEVERITY=major\nOOS_2: YES SEVERITY=major\n", encoding="utf-8")
    _ = v3.write_text("FINDING_1: YES SEVERITY=minor\nFINDING_2: NO SEVERITY=nit\nOOS_1: YES SEVERITY=minor\nOOS_2: YES SEVERITY=minor\n", encoding="utf-8")
    design = tmp_path / "design-missing-middle"
    design.mkdir()
    proc = run_cli(
        "plan-review",
        "tally",
        "--ballot-file",
        str(ballot),
        "--voter",
        f"1:Claude:{v1}",
        "--voter",
        f"3:Cursor:{v3}",
        "--design-tmpdir",
        str(design),
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    class_tsv = design / "plan-review" / "round-1" / "findings-classification.tsv"
    parsed_rows = voting.voter_agreement_rows_from_tsv(class_tsv.read_text(encoding="utf-8"), panel_kind="design").rows
    first_voters = cast("list[dict[str, object]]", parsed_rows[0]["voters"])
    assert [(voter["voter"], voter["severity"]) for voter in first_voters] == [
        ("Claude", "major"),
        ("Codex", ""),
        ("Cursor", "minor"),
    ]
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "| design | Codex | 0 | 0 | 0 | 0 | 0 | 0 | 0 | n/a | n/a | false |" in tally


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


def test_step3_continuation_preserves_warning_keys_across_rounds(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    round_stub = tmp_path / "round-stub.sh"
    _ = round_stub.write_text(
        """#!/usr/bin/env bash
set -euo pipefail
round=""
while [[ $# -gt 0 ]]; do
  case "$1" in --round-num) round="${2:?}"; shift 2 ;; *) shift ;; esac
done
if [[ "$round" == "1" ]]; then
  printf 'LOOP_STATUS=complete\\nACCEPTED_COUNT=0\\nDEGRADED_PANEL=1\\n'
  printf 'DEGRADED_PANEL_WARNING=first degraded warning\\n'
  printf 'INVALID_SLOT_PANEL_WARNING=first invalid warning\\n'
  printf 'TALLY_PLAN_REVIEW_STATUS=ok\\nAGGREGATOR_STATUS=ok\\n'
else
  printf 'LOOP_STATUS=complete\\nACCEPTED_COUNT=0\\nDEGRADED_PANEL=0\\n'
  printf 'TALLY_PLAN_REVIEW_STATUS=ok\\nAGGREGATOR_STATUS=ok\\n'
fi
""",
        encoding="utf-8",
    )
    round_stub.chmod(0o755)
    continuation_stub = tmp_path / "continuation-stub.sh"
    count_file = tmp_path / "continuation-count"
    _ = continuation_stub.write_text(
        f"""#!/usr/bin/env bash
set -euo pipefail
count=0
if [[ -f "{count_file}" ]]; then count=$(cat "{count_file}"); fi
count=$((count + 1))
printf '%s\\n' "$count" >"{count_file}"
if [[ "$count" == "1" ]]; then
  printf 'PLAN_REVIEW_CONTINUE=true\\nPLAN_REVIEW_CONTINUE_REASON=high-accepted\\n'
else
  printf 'PLAN_REVIEW_CONTINUE=false\\nPLAN_REVIEW_CONTINUE_REASON=small-clean\\n'
fi
""",
        encoding="utf-8",
    )
    continuation_stub.chmod(0o755)

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
        },
    )

    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    assert proc.stdout.count("DEGRADED_PANEL_WARNING=first degraded warning") >= 2
    assert proc.stdout.count("INVALID_SLOT_PANEL_WARNING=first invalid warning") >= 2
    result_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "DEGRADED_PANEL_WARNING=first degraded warning" in result_env
    assert "INVALID_SLOT_PANEL_WARNING=first invalid warning" in result_env


def test_write_design_round_meta_production_invokes_progress_cli(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[list[str]] = []

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        calls.append(argv)
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.delenv("WRITE_DESIGN_ROUND_META_SH", raising=False)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=2)  # pyright: ignore[reportPrivateUsage]

    assert calls == [
        [
            plan_review.sys.executable,
            str(plan_review._plugin_root() / "python" / "cli.py"),  # pyright: ignore[reportPrivateUsage]
            "progress",
            "write-design-round-meta",
            "--round-dir",
            str(tmp_path / "plan-review" / "round-2"),
        ]
    ]


def test_run_apply_zero_accepted_ignores_round_meta_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_run_params(tmp_path)

    def failed_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", "boom")

    monkeypatch.delenv("WRITE_DESIGN_ROUND_META_SH", raising=False)
    monkeypatch.setattr(plan_review, "_run_command", failed_run_command)
    values: dict[str, str] = {}

    rc = plan_review._run_apply(tmpdir=tmp_path, round_num=1, values=values)  # pyright: ignore[reportPrivateUsage]

    assert rc == 0
    assert values["ACCEPTED_COUNT"] == "0"
    assert (tmp_path / ".step3-round-1.phase").read_text(encoding="utf-8") == "awaiting-continuation\n"


def test_record_round_timing_writes_canonical_v1_row_idempotently(tmp_path: Path) -> None:
    def _record(round_num: str, start_s: str, end_s: str) -> subprocess.CompletedProcess[str]:
        return run_cli(
            "plan-review",
            "record-round-timing",
            "--design-tmpdir",
            str(tmp_path),
            "--round",
            round_num,
            "--start-s",
            start_s,
            "--end-s",
            end_s,
            env={"LARCH_QUIET_DISABLE": "1"},
        )

    def _window(round_num: int) -> tuple[int, int] | None:
        return progress_report._timing_round_windows(  # pyright: ignore[reportPrivateUsage]
            tmp_path / "timing-ledger.tsv", skill="design", round_num=round_num, skill_filtered=True
        )

    proc = _record("1", "100", "110")
    assert proc.returncode == 0, proc.stderr
    ledger = tmp_path / "timing-ledger.tsv"

    # The recorded row must parse through the renderer's canonical gate so the
    # Review Phase Detail Time/Cost columns populate (issue #5444).
    assert _window(1) == (100, 110)
    rows = [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("v1\tround\t")]
    assert len(rows) == 1
    assert rows[0][3] == "design"
    assert rows[0][5] == "1"
    assert len(rows[0]) >= 8

    # Re-recording the same round is idempotent: no duplicate v1 round row.
    proc_dup = _record("1", "100", "110")
    assert proc_dup.returncode == 0, proc_dup.stderr
    rows_after = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("v1\tround\t")]
    assert len(rows_after) == 1

    # A second round records its own canonical window plus the round-summary.env side effect.
    snap = tmp_path / "plan-review" / "round-4"
    snap.mkdir(parents=True)
    proc_snap = _record("4", "400", "410")
    assert proc_snap.returncode == 0, proc_snap.stderr
    assert _window(4) == (400, 410)
    assert (snap / "round-summary.env").read_text(encoding="utf-8") == "ROUND_NUM=4\n"


def test_write_design_round_meta_records_round_timing_from_start_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-start-s").write_text("1000\n", encoding="utf-8")

    # Isolate the timing side effect from the round-meta subprocess and freeze the end clock.
    monkeypatch.delenv("WRITE_DESIGN_ROUND_META_SH", raising=False)
    monkeypatch.setattr(plan_review, "_run_command", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(plan_review.time, "time", lambda: 1200)  # type: ignore[arg-type]

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=1)  # pyright: ignore[reportPrivateUsage]

    window = progress_report._timing_round_windows(  # pyright: ignore[reportPrivateUsage]
        tmp_path / "timing-ledger.tsv", skill="design", round_num=1, skill_filtered=True
    )
    assert window == (1000, 1200)


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


def _write_gate_b_findings(tmp_path: Path, body: str) -> None:
    _ = (tmp_path / "accepted-plan-findings.md").write_text(body, encoding="utf-8")


def test_gate_b_dedup_counts_structured_mode_and_document_order_ids(tmp_path: Path) -> None:
    _write_gate_b_findings(
        tmp_path,
        """### FINDING_1: Blocking
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: primary concern

### FINDING_3: Important
- **Reviewer**: Codex-Correctness
- **Severity**: important
- **Concern**: second concern

### FINDING_7: Latent
- **Reviewer**: Codex-Edge
- **Severity**: latent
- **Concern**: third concern

### FINDING_9: Nit
- **Reviewer**: Cursor-Style
- **Severity**: nit
- **Concern**: fourth concern
""",
    )
    proc = run_cli("plan-review", "gate-b-counts", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert "ACCEPTED_COUNT=4" in lines
    assert "HIGH_ACCEPTED_COUNT=2" in lines
    assert "MEDIUM_ACCEPTED_COUNT=1" in lines
    assert "LOW_ACCEPTED_COUNT=1" in lines
    assert "CRITICAL_ACCEPTED_COUNT=0" in lines
    assert "GATE_B_SEVERITY_MODE=structured" in lines
    assert "FINDING_IDS=1,3,7,9" in lines


def test_gate_b_dedup_fallback_counts_prefer_lower_and_empty_concern(tmp_path: Path) -> None:
    _write_gate_b_findings(
        tmp_path,
        """### FINDING_1: Low fallback
- **Reviewer**: Cursor-Style
- **Severity**: unknown
- **Concern**: style naming, no functional change implied.

### FINDING_2: Medium fallback
- Reviewer(s): Codex-Edge
- Concern: improves robustness and clarity in a secondary path.

### FINDING_3: High fallback
- **Reviewer**: Codex-Correctness
- **Concern**: functional incorrectness in a primary code path violates a stated invariant.

### FINDING_4: Critical fallback
- **Reviewer**: Cursor-Risk
- **Concern**: would cause data loss and build/CI breakage on landing.

### FINDING_5: Prefer lower
- **Reviewer**: Cursor-Mixed
- **Concern**: functional incorrectness in a primary code path, but only a style naming issue with no functional change implied.

### FINDING_6: Empty
- **Reviewer**: Cursor-Blank
- **Concern**:
""",
    )
    proc = run_cli("plan-review", "gate-b-counts", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    lines = proc.stdout.splitlines()
    assert "ACCEPTED_COUNT=6" in lines
    assert "GATE_B_SEVERITY_MODE=fallback" in lines
    assert "CRITICAL_ACCEPTED_COUNT=1" in lines
    assert "HIGH_ACCEPTED_COUNT=1" in lines
    assert "MEDIUM_ACCEPTED_COUNT=1" in lines
    assert "LOW_ACCEPTED_COUNT=3" in lines

    expected = {1: "Low", 2: "Medium", 3: "High", 4: "Critical", 5: "Low", 6: "Low"}
    empty_concern_stdout = ""
    for finding_id, label in expected.items():
        line = run_cli(
            "plan-review",
            "gate-b-finding-line",
            "--design-tmpdir",
            str(tmp_path),
            "--finding-id",
            str(finding_id),
        )
        assert line.returncode == 0, line.stderr
        assert f"DISPLAY_SEVERITY={label}" in line.stdout
        if finding_id == 6:
            empty_concern_stdout = line.stdout
    assert "CONCERN_EXCERPT=\n" in empty_concern_stdout


def test_gate_b_dedup_non_contiguous_ids_and_one_by_one_ordinals(tmp_path: Path) -> None:
    _write_gate_b_findings(
        tmp_path,
        """### FINDING_1: First
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Concern**: first concern

### FINDING_3: Third
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: third concern
""",
    )
    proc = run_cli("plan-review", "gate-b-counts", "--design-tmpdir", str(tmp_path))
    assert proc.returncode == 0, proc.stderr
    assert "ACCEPTED_COUNT=2" in proc.stdout
    assert "FINDING_IDS=1,3" in proc.stdout

    line = run_cli("plan-review", "gate-b-finding-line", "--design-tmpdir", str(tmp_path), "--finding-id", "3")
    assert line.returncode == 0, line.stderr
    assert "ONE_BY_ONE_ORDINAL=2" in line.stdout
    assert "ONE_BY_ONE_TOTAL=2" in line.stdout
    assert "ONE_BY_ONE_HEADER=Finding 2/2" in line.stdout
    assert "ONE_BY_ONE_PROMPT_LINE=FINDING_3 [Medium] — Codex-Arch: third concern. Apply this finding to the plan?" in line.stdout

    missing = run_cli("plan-review", "gate-b-finding-line", "--design-tmpdir", str(tmp_path), "--finding-id", "2")
    assert missing.returncode != 0
    assert "unknown finding id FINDING_2" in missing.stderr


def test_preview_gate_b_rows_context_truncation_and_no_plan_body(tmp_path: Path) -> None:
    long_concern = "x" * 240
    _write_gate_b_findings(
        tmp_path,
        f"""### FINDING_1: Long
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: {long_concern}

### FINDING_3: Non-contiguous
- **Reviewer**: Codex-Arch
- **Severity**: nit
- **Concern**: short concern
""",
    )
    _ = (tmp_path / "plan.txt").write_text("SHOULD_NOT_PRINT\n", encoding="utf-8")
    _ = (tmp_path / "rejected-findings.md").write_text("rejected context\n", encoding="utf-8")
    _ = (tmp_path / "oos.md").write_text("oos context\n", encoding="utf-8")
    proc = run_cli("plan-review", "preview", "--design-tmpdir", str(tmp_path), "--variant", "gate-b")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.startswith("## Plan Review Findings — Review\n\n")
    assert "FINDING_1 | High | Cursor-Arch | " + ("x" * 200) in proc.stdout
    assert "FINDING_3 | Low | Codex-Arch | short concern" in proc.stdout
    assert "SHOULD_NOT_PRINT" not in proc.stdout
    assert not (tmp_path / ".step3-entry-plan-printed").exists()
    assert proc.stdout.count("rejected context") == 1
    assert proc.stdout.count("oos context") == 1

    invalid = run_cli("plan-review", "preview", "--design-tmpdir", "", "--variant", "gate-b")
    assert invalid.returncode == 0
    assert invalid.stdout.startswith("**⚠ 3.5: DESIGN_TMPDIR missing or invalid")


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
    text = plan_review_round._compose_attributed_ballot(design=design, oos_md="")  # pyright: ignore[reportPrivateUsage]
    assert "FINDING_2" in text
    assert "FINDING_1" not in text


def test_compose_attributed_ballot_ignores_stale_findings_oos_md(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "findings-in-scope.md").write_text(
        "### FINDING_1: in scope\n- **Reviewer**: Codex\n- **Concern**: c\n",
        encoding="utf-8",
    )
    _ = (design / "findings-oos.md").write_text(
        "### OOS_1: [OUT_OF_SCOPE] stale\n- **Reviewer**: stale-reviewer\n- **Concern**: old\n",
        encoding="utf-8",
    )
    current_oos = """### OOS_2: [OUT_OF_SCOPE] current
- **Reviewer**: cursor-pragmatic
- **Concern**: fresh oos
"""
    text = plan_review_round._compose_attributed_ballot(design=design, oos_md=current_oos)  # pyright: ignore[reportPrivateUsage]
    assert "OOS_2" in text
    assert "cursor-pragmatic" in text
    assert "OOS_1" not in text
    assert "stale-reviewer" not in text


def test_aggregation_ok_for_voting_accepts_ok_and_intentional_skips() -> None:
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "ok", "AGGREGATED": "true"})  # pyright: ignore[reportPrivateUsage]
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "insufficient-input", "AGGREGATED": "false"})  # pyright: ignore[reportPrivateUsage]
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "disabled", "AGGREGATED": "false"})  # pyright: ignore[reportPrivateUsage]
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "validation-failed", "AGGREGATED": "false"}, returncode=0)  # pyright: ignore[reportPrivateUsage]
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "validation-exhausted", "AGGREGATED": "false"}, returncode=0)  # pyright: ignore[reportPrivateUsage]
    assert plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "dispatch-failed", "AGGREGATED": "false"}, returncode=0)  # pyright: ignore[reportPrivateUsage]
    assert not plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "validation-failed", "AGGREGATED": "false"}, returncode=1)  # pyright: ignore[reportPrivateUsage]
    assert not plan_review_round._aggregation_ok_for_voting(agg_kv={"REASON": "ok", "AGGREGATED": "false"})  # pyright: ignore[reportPrivateUsage]


def test_aggregator_status_from_kv_records_failed_merge() -> None:
    assert (
        plan_review_round._aggregator_status_from_kv(  # pyright: ignore[reportPrivateUsage]
            agg_kv={"REASON": "validation-failed", "AGGREGATED": "false"},
            returncode=0,
        )
        == "validation-failed"
    )
    assert (
        plan_review_round._aggregator_status_from_kv(  # pyright: ignore[reportPrivateUsage]
            agg_kv={"REASON": "ok", "AGGREGATED": "true"},
            returncode=0,
        )
        == "ok"
    )


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
    ballot_text = plan_review_round._compose_attributed_ballot(design=design, oos_md=oos)  # pyright: ignore[reportPrivateUsage]
    ballot = design / "ballot.txt"
    _ = ballot.write_text(ballot_text, encoding="utf-8")
    proposer_map = design / "proposer-map.tsv"
    voting.write_proposer_map(ballot_file=ballot, map_file=proposer_map)
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=ballot_text), encoding="utf-8")
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
    voting.write_proposer_map(ballot_file=ballot, map_file=design / "proposer-map.tsv")
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed), encoding="utf-8")
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
    voting.write_proposer_map(ballot_file=ballot, map_file=map_file)
    rows = map_file.read_text(encoding="utf-8").splitlines()
    header_idx = next(i for i, row in enumerate(rows) if row.startswith("item_id\t"))
    _ = map_file.write_text("\n".join(rows[: header_idx + 1]) + "\n", encoding="utf-8")
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed), encoding="utf-8")
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
    assert "missing proposer map entry" in proc.stderr or "proposer map item mismatch" in proc.stderr


def test_tally_plan_review_neutralized_without_sidecar_fails_closed(tmp_path: Path) -> None:
    attributed = """### FINDING_1: Fix parser
- **Reviewer**: Cursor-Arch
- **Concern**: parser misses bad input.
"""
    design = tmp_path / "design-neutral-no-sidecar"
    design.mkdir()
    ballot = design / "ballot.txt"
    _ = ballot.write_text(voting.neutralize_reviewer_attribution(text=attributed), encoding="utf-8")
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
    assert proc.returncode != 0
    assert "missing proposer map entry" in proc.stderr


def _make_rejected_block(item_id: str, location: str, concern: str, title: str) -> str:
    """A rejected-findings.md block in the tally's emitted shape (issue #4849 tests)."""
    return (
        f"### [Plan Review] {item_id}\n\n"
        f"### {item_id}: {title}\n"
        f"- **Location**: {location}\n"
        f"- **Concern**: {concern}\n"
        f"- **Severity**: important\n\n"
    )


def _emit_rejected(design: Path, *, report_framing: bool = False) -> subprocess.CompletedProcess[str]:
    args = [
        "plan-review",
        "emit-rejected",
        "--design-tmpdir",
        str(design),
    ]
    if report_framing:
        args.append("--report-framing")
    return run_cli(*args, env={"LARCH_QUIET_DISABLE": "1"})


def test_emit_rejected_excludes_already_applied_findings(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    applied = _make_rejected_block("FINDING_1", "alpha.py:10-20", "Off-by-one in loop bound", "Loop bound")
    fresh = _make_rejected_block("FINDING_3", "beta.py:5", "Missing nil guard", "Nil guard")
    body = applied + fresh
    _ = (design / "rejected-findings.md").write_text(body, encoding="utf-8")
    # Record FINDING_1's dedup key as applied in round 1 (what plan_review_continuation does).
    applied_key = plan_review._finding_dedup_key(applied)  # pyright: ignore[reportPrivateUsage]
    _ = (design / ".step3-applied-finding-keys.tsv").write_text(f"1\t{applied_key}\n", encoding="utf-8")

    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    # FINDING_1 was applied in round 1 -> excluded; FINDING_3 was never applied -> kept.
    assert "FINDING_1" not in proc.stdout
    assert "Off-by-one in loop bound" not in proc.stdout
    assert proc.stdout == fresh
    # The on-disk file is never mutated (still committed to the run log for audit).
    assert (design / "rejected-findings.md").read_text(encoding="utf-8") == body


def test_emit_rejected_without_ledger_emits_verbatim(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    body = _make_rejected_block("FINDING_1", "alpha.py:10", "Concern A", "Title A")
    _ = (design / "rejected-findings.md").write_text(body, encoding="utf-8")
    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == body


def test_emit_rejected_all_applied_emits_empty(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    block = _make_rejected_block("FINDING_1", "alpha.py:10", "Concern A", "Title A")
    _ = (design / "rejected-findings.md").write_text(block, encoding="utf-8")
    key = plan_review._finding_dedup_key(block)  # pyright: ignore[reportPrivateUsage]
    _ = (design / ".step3-applied-finding-keys.tsv").write_text(f"2\t{key}\n", encoding="utf-8")
    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def test_emit_rejected_report_framing_wraps_operator_output(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    body = _make_rejected_block("FINDING_1", "alpha.py:10", "Concern A", "Title A")
    _ = (design / "rejected-findings.md").write_text(body, encoding="utf-8")

    proc = _emit_rejected(design, report_framing=True)

    assert proc.returncode == 0, proc.stderr
    assert plan_review.REJECTED_FINDINGS_REPORT_HEADING in proc.stdout
    assert plan_review.REJECTED_FINDINGS_REPORT_ANNOTATION in proc.stdout
    assert "Unimplemented Plan Review Suggestions" not in proc.stdout
    assert body in proc.stdout
    assert (design / "rejected-findings.md").read_text(encoding="utf-8") == body


def test_emit_rejected_report_framing_all_applied_emits_empty(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    block = _make_rejected_block("FINDING_1", "alpha.py:10", "Concern A", "Title A")
    _ = (design / "rejected-findings.md").write_text(block, encoding="utf-8")
    key = plan_review._finding_dedup_key(block)  # pyright: ignore[reportPrivateUsage]
    _ = (design / ".step3-applied-finding-keys.tsv").write_text(f"1\t{key}\n", encoding="utf-8")

    proc = _emit_rejected(design, report_framing=True)

    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def test_emit_rejected_missing_file_emits_nothing(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""


def _make_finding_only_rejected_block(item_id: str, location: str, concern: str, title: str) -> str:
    """Rejected block without the ``[Plan Review]`` wrapper (marker drift / hand edit)."""
    return (
        f"### {item_id}: {title}\n"
        f"- **Location**: {location}\n"
        f"- **Concern**: {concern}\n"
        f"- **Severity**: important\n\n"
    )


def test_emit_rejected_filters_finding_blocks_without_plan_review_markers(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    applied = _make_finding_only_rejected_block(
        "FINDING_1", "alpha.py:10-20", "Off-by-one in loop bound", "Loop bound"
    )
    fresh = _make_finding_only_rejected_block("FINDING_3", "beta.py:5", "Missing nil guard", "Nil guard")
    body = applied + fresh
    _ = (design / "rejected-findings.md").write_text(body, encoding="utf-8")
    applied_key = plan_review._finding_dedup_key(applied)  # pyright: ignore[reportPrivateUsage]
    _ = (design / ".step3-applied-finding-keys.tsv").write_text(f"1\t{applied_key}\n", encoding="utf-8")

    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert "FINDING_1" not in proc.stdout
    assert proc.stdout == fresh


def test_emit_rejected_ledger_without_recognizable_blocks_emits_empty(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "rejected-findings.md").write_text(
        "Stale rejected prose with no FINDING blocks.\n", encoding="utf-8"
    )
    _ = (design / ".step3-applied-finding-keys.tsv").write_text("1\tsome-applied-key\n", encoding="utf-8")

    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout == ""
    assert "WARN=emit-rejected: applied-finding ledger present" in proc.stderr


def test_emit_rejected_drops_already_addressed_tagged_block(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    tagged = _make_rejected_block(
        "FINDING_1", "alpha.py:10", "[ALREADY_ADDRESSED] plan already covers this", "Already covered"
    )
    fresh = _make_rejected_block("FINDING_2", "beta.py:5", "Missing nil guard", "Nil guard")
    _ = (design / "rejected-findings.md").write_text(tagged + fresh, encoding="utf-8")

    # No ledger present: the [ALREADY_ADDRESSED] tag alone suppresses the block.
    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert "FINDING_1" not in proc.stdout
    assert "ALREADY_ADDRESSED" not in proc.stdout
    assert proc.stdout == fresh


def test_emit_rejected_drops_already_addressed_from_ledger(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    # A later round re-raises the same concern WITHOUT the tag; the cross-round
    # ledger (written when an earlier round flagged it) still suppresses it.
    reraised = _make_rejected_block("FINDING_3", "gamma.py:7", "Concern re-raised untagged", "Reraised")
    fresh = _make_rejected_block("FINDING_4", "delta.py:2", "Genuinely new concern", "New")
    _ = (design / "rejected-findings.md").write_text(reraised + fresh, encoding="utf-8")
    key = plan_review._finding_dedup_key(reraised)  # pyright: ignore[reportPrivateUsage]
    _ = (design / ".step3-already-addressed-finding-keys.tsv").write_text(f"{key}\n", encoding="utf-8")

    proc = _emit_rejected(design)
    assert proc.returncode == 0, proc.stderr
    assert "FINDING_3" not in proc.stdout
    assert proc.stdout == fresh


def test_emit_rejected_already_addressed_ledger_extracts_records_and_dedups(tmp_path: Path) -> None:
    design = tmp_path / "design"
    design.mkdir()
    tagged = _make_rejected_block(
        "FINDING_1", "alpha.py:10", "[ALREADY_ADDRESSED] plan covers it", "Covered"
    )
    untagged = _make_rejected_block("FINDING_2", "beta.py:5", "Real concern", "Real")
    _ = (design / "rejected-findings.md").write_text(tagged + untagged, encoding="utf-8")

    # The extracted key is the canonical (tag-stripped) concern key, so it matches
    # an untagged re-raise of the same concern in a later round.
    untagged_same = _make_rejected_block("FINDING_9", "alpha.py:10", "plan covers it", "Covered")
    canonical_key = plan_review._finding_dedup_key(untagged_same)  # pyright: ignore[reportPrivateUsage]
    keys = plan_review._already_addressed_keys_in_rejected(design)  # pyright: ignore[reportPrivateUsage]
    assert keys == [canonical_key]

    # Recording is idempotent and the on-disk ledger holds only the canonical key.
    plan_review._record_already_addressed_finding_keys(tmpdir=design, keys=keys)  # pyright: ignore[reportPrivateUsage]
    plan_review._record_already_addressed_finding_keys(tmpdir=design, keys=keys)  # pyright: ignore[reportPrivateUsage]
    ledger = (design / ".step3-already-addressed-finding-keys.tsv").read_text(encoding="utf-8")
    assert ledger == f"{canonical_key}\n"
    assert plan_review._read_already_addressed_finding_keys(design) == {canonical_key}  # pyright: ignore[reportPrivateUsage]


def test_step3_loop_zero_findings_clears_stale_accepted_and_awaits_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-round converged zero-findings must not re-enter Gate B apply via stale tally artifacts (#5032)."""
    design = tmp_path
    _write_run_params(design)
    _ = (design / "review-round-count.txt").write_text("4\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 4\n- **Concern**: already applied\n",
        encoding="utf-8",
    )
    _ = (design / "voting-tally.md").write_text(
        "## Findings\n| FINDING_1 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )
    reviewer_file = design / "cursor-plan-arch-output.txt"

    fake_run_cli = make_zero_findings_plan_review_fake_cli(design, reviewer_file)

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "5"])

    assert rc == 0
    assert (design / ".step3-round-5.phase").read_text(encoding="utf-8") == "awaiting-continuation\n"
    result_env = dict(
        line.split("=", 1)
        for line in (design / ".step3-review-result.env").read_text(encoding="utf-8").splitlines()
        if "=" in line
    )
    assert result_env["LOOP_STATUS"] == "zero-findings-degraded-panel"
    assert result_env["NEXT_ACTION"] == "step3b"
    assert result_env["ACCEPTED_COUNT"] == "0"
    # #5194: the degraded-panel terminal env must carry numeric round provenance so
    # design_publish.review_provenance() does not read rounds=0 and refuse to publish.
    assert result_env["ROUNDS_COMPLETED"] == "5", result_env
    assert result_env["REVIEW_ROUND_COUNT"] == "5", result_env
    assert not (design / "accepted-plan-findings.md").read_text(encoding="utf-8").strip()
    tally = (design / "voting-tally.md").read_text(encoding="utf-8")
    assert "## Voter Agreement Scoreboard" in tally
    assert "## Voter Severity Scoreboard" in tally
    assert tally.index("## Voter Agreement Scoreboard") < tally.index("## Voter Severity Scoreboard")


def test_step3_loop_zero_findings_degraded_emits_round_provenance_to_stdout(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """#5210: the terminal degraded-panel stdout envelope must carry numeric round
    provenance (ROUNDS_COMPLETED/REVIEW_ROUND_COUNT) so the Step 5c overlay never
    reconstructs rounds=0 from it, mirroring the durable .step3-review-result.env write.
    """
    design = tmp_path
    _write_run_params(design)
    _ = (design / "review-round-count.txt").write_text("4\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 4\n- **Concern**: already applied\n",
        encoding="utf-8",
    )
    _ = (design / "voting-tally.md").write_text(
        "## Findings\n| FINDING_1 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )
    reviewer_file = design / "cursor-plan-arch-output.txt"

    fake_run_cli = make_zero_findings_plan_review_fake_cli(design, reviewer_file)

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "5"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "LOOP_STATUS=zero-findings-degraded-panel" in out, out
    assert "NEXT_ACTION=step3b" in out, out
    assert "ROUNDS_COMPLETED=5" in out, out
    assert "REVIEW_ROUND_COUNT=5" in out, out


def test_step3_loop_zero_findings_degraded_stop_writes_sentinels(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final zero-findings-degraded-panel stop path must write step-3 sentinels."""
    design = tmp_path
    _write_run_params(design)
    _ = (design / "review-round-count.txt").write_text("4\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 4\n- **Concern**: already applied\n",
        encoding="utf-8",
    )
    _ = (design / "voting-tally.md").write_text(
        "## Findings\n| FINDING_1 | 3 | 0 | 0 | accepted |\n",
        encoding="utf-8",
    )
    reviewer_file = design / "cursor-plan-arch-output.txt"
    continuation_stub = design / "continuation-stub.sh"
    _ = continuation_stub.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "printf 'PLAN_REVIEW_CONTINUE=false\\nPLAN_REVIEW_CONTINUE_REASON=converged-no-new-findings\\n'\n",
        encoding="utf-8",
    )
    continuation_stub.chmod(0o755)

    fake_run_cli = make_zero_findings_plan_review_fake_cli(design, reviewer_file)

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_round, "_run_cli", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setenv("RUN_STEP3_CONTINUATION_SH", str(continuation_stub))

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "5"])

    assert rc == 0
    assert (design / ".completed" / "step-3").is_file()
    assert (design / ".completed" / "step-3-terminal").is_file()


def test_step3_loop_postplan_validator_runs_from_consumer_cwd(tmp_path: Path) -> None:
    # #4847: the Step 3 plan-review loop must invoke `design postplan-emit` from
    # the consumer-repo cwd (not the plugin cache that `_run_command` otherwise
    # forces), so the validator derives the consumer repo and consumer-only
    # plan-command scripts are not false-flagged missing-script. End-to-end check
    # mirroring the #4490 postplan test in test_design_postplan.py.
    plugin_root = tmp_path / "plugin"
    plugin_root.joinpath("python").mkdir(parents=True)
    fake_cli = plugin_root / "python" / "cli.py"
    _ = fake_cli.write_text(
        """#!/usr/bin/env python3
import os
import sys
args = sys.argv[1:]
if args[:2] == ["design", "postplan-emit"]:
    with open(os.environ["RECORD_FILE"], "w", encoding="utf-8") as fh:
        print("POSTPLAN_CWD=" + os.getcwd(), file=fh)
    print("POSTPLAN_EMIT_STATUS=ok")
    raise SystemExit(0)
if args[:2] == ["plan-review", "continuation"]:
    print("PLAN_REVIEW_CONTINUE=false")
    print("PLAN_REVIEW_CONTINUE_REASON=small-clean")
    raise SystemExit(0)
raise SystemExit(0)
""",
        encoding="utf-8",
    )
    fake_cli.chmod(fake_cli.stat().st_mode | stat.S_IXUSR)
    recorder = tmp_path / "postplan-invocation.env"

    consumer = tmp_path / "consumer"
    consumer.mkdir()
    _ = subprocess.run(["git", "init", "-q", str(consumer)], check=True)

    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "plan.txt").write_text("# Plan\n\ndiff_lines: 1\n", encoding="utf-8")
    _ = (design / "run-params.json").write_text('{"approve_requested": false}\n', encoding="utf-8")
    _ = (design / ".step3-round-1.phase").write_text("awaiting-post-apply\n", encoding="utf-8")
    (design / ".gate-b-postapply-ready-1").touch()

    cli_py = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(plugin_root)
    env["RECORD_FILE"] = str(recorder)
    result = subprocess.run(
        [sys.executable, str(cli_py), "plan-review", "run", "--design-tmpdir", str(design), "--mode", "loop"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
        cwd=str(consumer),
    )

    assert result.returncode == 0, result.stderr
    assert recorder.is_file(), f"postplan-emit not invoked; stdout={result.stdout!r} stderr={result.stderr!r}"
    recorded = dict(
        line.split("=", 1) for line in recorder.read_text(encoding="utf-8").splitlines() if "=" in line
    )
    assert Path(recorded["POSTPLAN_CWD"]).resolve() == consumer.resolve()


def test_write_atomic_does_not_create_missing_parent(tmp_path: Path) -> None:
    missing_parent = tmp_path / "missing" / "sidecar.env"
    with pytest.raises(FileNotFoundError):
        plan_review._write_atomic(path=missing_parent, content="A=1\n")  # pyright: ignore[reportPrivateUsage]
    assert not missing_parent.exists()
