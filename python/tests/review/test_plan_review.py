# pyright: reportUnknownArgumentType=false, reportUnknownLambdaType=false

from __future__ import annotations

import contextlib
import json
import io
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import cast

from larch.calibration import difficulty
from larch.core import logging_util
from larch.design import design_terminal
from larch.review import plan_review
from larch.review import plan_review_common
from larch.review import plan_review_loop
from larch.review import plan_review_normalize
from larch.review import plan_review_round
import pytest
from larch.review import voting
from test_support import ROOT, make_zero_findings_plan_review_fake_cli, run_cli


def _timing_round_window(
    ledger: Path,
    *,
    skill: str,
    round_num: int,
    skill_filtered: bool,
) -> tuple[int, int] | None:
    starts: list[int] = []
    ends: list[int] = []
    for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines():
        cols = line.split("\t")
        if len(cols) < 8 or cols[:2] != ["v1", "round"]:
            continue
        if skill_filtered and cols[3] != skill:
            continue
        if cols[5] != str(round_num):
            continue
        try:
            starts.append(int(cols[6]))
            ends.append(int(cols[7]))
        except ValueError:
            continue
    return (min(starts), max(ends)) if starts and ends else None


def _install_rust_timing_stubs(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    """Exercise review timing consumers without reimplementing a Python owner."""
    calls: list[dict[str, object]] = []

    def fake_round(_runner: object, **kwargs: object) -> bool:
        calls.append({"verb": "record-round", **kwargs})
        ledger = Path(str(kwargs["ledger"]))
        ledger.parent.mkdir(parents=True, exist_ok=True)
        skill = str(kwargs["skill"])
        round_num = int(cast("int | float | str", kwargs["round_num"]))
        if kwargs.get("if_round_exists") and ledger.exists() and any(
            (cols := line.split("\t"))[:2] == ["v1", "round"]
            and len(cols) == 13
            and cols[3] == skill
            and cols[5] == str(round_num)
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines()
        ):
            return True
        prior = 1 + sum(
            1
            for line in ledger.read_text(encoding="utf-8", errors="replace").splitlines()
            if (cols := line.split("\t"))[:2] == ["v1", "round"]
            and len(cols) == 13
            and cols[3] == skill
            and cols[5] == str(round_num)
        ) if ledger.exists() else 1
        start_s = int(cast("int | float | str", kwargs["start_s"]))
        end_s = int(cast("int | float | str", kwargs["end_s"]))
        row = [
            "v1", "round", str(end_s), skill, str(kwargs["step"]), str(round_num),
            str(start_s), str(end_s), str(max(end_s - start_s, 0)),
            str(kwargs["accepted"]), str(kwargs["rejected"]), "-", str(prior),
        ]
        with ledger.open("a", encoding="utf-8") as handle:
            _ = handle.write("\t".join(row) + "\n")
        return True

    def fake_vendor(_runner: object, **kwargs: object) -> bool:
        calls.append({"verb": "record-vendor-task", **kwargs})
        ledger = Path(str(kwargs["ledger"]))
        ledger.parent.mkdir(parents=True, exist_ok=True)
        start_s = int(cast("int | float | str", kwargs["start_s"]))
        end_s = int(cast("int | float | str", kwargs["end_s"]))
        row = [
            "v1", "vendor", str(end_s), str(kwargs["skill"]), "-", str(kwargs["vendor"]),
            str(kwargs["task_kind"]), str(start_s), str(end_s), str(max(end_s - start_s, 0)),
            Path(str(kwargs["output"])).name, str(kwargs.get("exit_code", 0)), str(kwargs["status"]),
        ]
        with ledger.open("a", encoding="utf-8") as handle:
            _ = handle.write("\t".join(row) + "\n")
        return True

    monkeypatch.setattr(plan_review_loop.rust_runtime, "timing_record_round", fake_round)
    monkeypatch.setattr(plan_review_loop.rust_runtime, "timing_record_vendor_task", fake_vendor)
    return calls


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
    _ = (tmp_path / "review-round-count.txt").write_text(f"{plan_review_common.ROUND_CAP}\n", encoding="utf-8")
    result = plan_review.run_step3_review(["--design-tmpdir", str(tmp_path), "--new-process-group"])
    assert result == 0
    assert len(calls) == 1


def test_new_process_group_absent_does_not_call_setsid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_setsid() -> None:
        raise AssertionError("setsid must not be called without --new-process-group")

    monkeypatch.setattr(plan_review.os, "setsid", forbidden_setsid)  # type: ignore[arg-type]
    _ = (tmp_path / "plan-review-scope-anchor.txt").write_text("anchor\n", encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text(f"{plan_review_common.ROUND_CAP}\n", encoding="utf-8")
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


def test_step3_normalize_read_result_env_prefers_bgjob_and_falls_back_to_legacy(tmp_path: Path) -> None:
    legacy_result_env = tmp_path / ".step3-review-result.env"
    _ = legacy_result_env.write_text(
        "BGJOB_RC=0\n"
        "STEP3_REVIEW_LOOP_STATUS=tally-error\n"
        "LOOP_STATUS=tally-error\n"
        "ROUNDS_COMPLETED=1\n"
        "FINAL_ROUND_NUM=2\n"
        "ACCEPTED_COUNT=3\n"
        "DEGRADED_PANEL_WARNING=panel degraded\n"
        "INVALID_SLOT_PANEL_WARNING=invalid slot dropped\n",
        encoding="utf-8",
    )
    bgjob_result_env = tmp_path / "bgjob" / "design-step3-review.result.env"
    bgjob_result_env.parent.mkdir()
    _ = bgjob_result_env.write_text(
        "BGJOB_RC=0\n"
        "STEP3_REVIEW_LOOP_STATUS=complete\n"
        "LOOP_STATUS=complete\n"
        "ROUNDS_COMPLETED=4\n",
        encoding="utf-8",
    )

    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=ok",
        "BGJOB_RC=0",
        "NEXT_ACTION=step3b",
        "STEP3_REVIEW_LOOP_STATUS=complete",
        "LOOP_STATUS=complete",
        "ROUNDS_COMPLETED=4",
        "FINAL_ROUND_NUM=",
        "ACCEPTED_COUNT=",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
        "REASON=",
    ]

    _ = bgjob_result_env.write_text("", encoding="utf-8")
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 1, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=missing",
        "BGJOB_RC=",
        "NEXT_ACTION=",
        "STEP3_REVIEW_LOOP_STATUS=",
        "LOOP_STATUS=",
        "ROUNDS_COMPLETED=",
        "FINAL_ROUND_NUM=",
        "ACCEPTED_COUNT=",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
        "REASON=",
    ]

    _ = bgjob_result_env.write_text(
        "BGJOB_RC=timeout\n"
        "STEP3_REVIEW_LOOP_STATUS=complete\n"
        "LOOP_STATUS=complete\n"
        "ROUNDS_COMPLETED=4\n"
        "FINAL_ROUND_NUM=3\n"
        "ACCEPTED_COUNT=9\n",
        encoding="utf-8",
    )
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 1, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=invalid",
        "BGJOB_RC=timeout",
        "NEXT_ACTION=",
        "STEP3_REVIEW_LOOP_STATUS=complete",
        "LOOP_STATUS=complete",
        "ROUNDS_COMPLETED=4",
        "FINAL_ROUND_NUM=3",
        "ACCEPTED_COUNT=9",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
        "REASON=",
    ]

    bgjob_result_env.unlink()
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=ok",
        "BGJOB_RC=0",
        "NEXT_ACTION=step3b-bypass",
        "STEP3_REVIEW_LOOP_STATUS=tally-error",
        "LOOP_STATUS=tally-error",
        "ROUNDS_COMPLETED=1",
        "FINAL_ROUND_NUM=2",
        "ACCEPTED_COUNT=3",
        "DEGRADED_PANEL_WARNING=panel degraded",
        "INVALID_SLOT_PANEL_WARNING=invalid slot dropped",
        "REASON=",
    ]

    legacy_result_env.unlink()
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 1, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=missing",
        "BGJOB_RC=",
        "NEXT_ACTION=",
        "STEP3_REVIEW_LOOP_STATUS=",
        "LOOP_STATUS=",
        "ROUNDS_COMPLETED=",
        "FINAL_ROUND_NUM=",
        "ACCEPTED_COUNT=",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
        "REASON=",
    ]

    target = tmp_path / "target.env"
    _ = target.write_text("STEP3_REVIEW_LOOP_STATUS=complete\n", encoding="utf-8")
    legacy_result_env.symlink_to(target)
    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 1, proc.stderr
    assert "READ_RESULT_ENV_STATUS=missing" in proc.stdout
    assert "WARN=" not in proc.stdout


def test_step3_normalize_read_result_env_preserves_terminal_failure_next_action_on_nonzero_rc(
    tmp_path: Path,
) -> None:
    bgjob_result_env = tmp_path / "bgjob" / "design-step3-review.result.env"
    bgjob_result_env.parent.mkdir(parents=True)
    _ = bgjob_result_env.write_text(
        "BGJOB_RC=1\n"
        "NEXT_ACTION=final-summary:failed-postplan\n"
        "STEP3_REVIEW_LOOP_STATUS=postplan-failed\n"
        "LOOP_STATUS=postplan-failed\n",
        encoding="utf-8",
    )

    proc = run_cli("plan-review", "normalize-status", "--design-tmpdir", str(tmp_path), "--read-result-env")
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.splitlines() == [
        "READ_RESULT_ENV_STATUS=ok",
        "BGJOB_RC=1",
        "NEXT_ACTION=final-summary:failed-postplan",
        "STEP3_REVIEW_LOOP_STATUS=postplan-failed",
        "LOOP_STATUS=postplan-failed",
        "ROUNDS_COMPLETED=",
        "FINAL_ROUND_NUM=",
        "ACCEPTED_COUNT=",
        "DEGRADED_PANEL_WARNING=",
        "INVALID_SLOT_PANEL_WARNING=",
        "REASON=",
    ]


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

    monkeypatch.setattr(plan_review_normalize, "step3_record_report_evidence", fake_record_report_evidence)
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
    assert (tmp_path / ".completed" / "step-3").is_file()


def test_step3_normalizer_records_completion_from_stdout_status_without_result_env(tmp_path: Path) -> None:
    # #5418 Fix A: even with no result env (e.g., cleared by auto-continuation
    # before the loop was killed), normalize writes step-3 when the
    # merged status resolves to a terminal value from the stdout content.
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    assert (tmp_path / ".completed" / "step-3").is_file()


def test_step3_normalizer_no_completion_for_interactive_status(tmp_path: Path) -> None:
    # #5418 Fix A guard: interactive mid-loop statuses must NOT trigger sentinel write.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=main-agent-vote-required\nLOOP_STATUS=main-agent-vote-required\nROUNDS_COMPLETED=1\n",
        encoding="utf-8",
    )
    proc = _run_step3_normalizer(tmp_path, "LOOP_STATUS=main-agent-vote-required\nROUNDS_COMPLETED=1\n")
    assert proc.returncode == 0, proc.stderr
    assert not (tmp_path / ".completed" / "step-3").exists()


def test_step3_normalizer_completion_before_kv_emit(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # #5418: reordering sentinel write after emit would pass post-exit checks but
    # hide result-env ordering regressions; pin completion before emit entry.
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "STEP3_REVIEW_LOOP_STATUS=complete\nLOOP_STATUS=complete\nROUNDS_COMPLETED=1\nREVIEW_ROUND_COUNT=1\n",
        encoding="utf-8",
    )
    stdout_file = tmp_path / "plan-review.stdout"
    _ = stdout_file.write_text("LOOP_STATUS=complete\nROUNDS_COMPLETED=1\n", encoding="utf-8")
    completion_seen = False
    original = plan_review_normalize._step3_emit_normalize_envelope_with_next_action  # pyright: ignore[reportPrivateUsage]

    def _assert_sentinel_before_emit(tmpdir: Path, *, values: dict[str, str]) -> None:
        nonlocal completion_seen
        completion_seen = (tmpdir / ".completed" / "step-3").is_file()
        original(tmpdir=tmpdir, values=values)

    monkeypatch.setattr(plan_review_normalize, "_step3_emit_normalize_envelope_with_next_action", _assert_sentinel_before_emit)
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        rc = plan_review.normalize_step3_status_main(
            ["--design-tmpdir", str(tmp_path), "--stdout-file", str(stdout_file), "--loop-rc", "0"]
        )
    assert rc == 0
    assert completion_seen


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
    body = (ROOT / "python" / "larch" / "review" / "plan_review_normalize.py").read_text(encoding="utf-8")
    assert "SUMMARY_OUTCOME=failed-postplan" in body
    assert "SUMMARY_OUTCOME=failed-judge-panel" in body
    assert "load_bash_quoted_env" in body
    assert "_step3_read_result_env_quiet" in body
    assert "_step3_next_action" in body
    assert "file=sys.stderr" in body


@pytest.mark.parametrize(
    ("reason", "evidence_ref"),
    [
        ("strip-body-failure", "prelaunch-strip-body-failure"),
        ("scope-anchor-empty", "prelaunch-scope-anchor-empty"),
        ("snapshot-pre-review-failure", "prelaunch-snapshot-pre-review-failure"),
        ("unexpected reason", "prelaunch-unexpected-reason"),
    ],
)
def test_stage_panel_init_failed_records_canonical_tokens_for_prelaunch_reason(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, reason: str, evidence_ref: str
) -> None:
    def rust_validation_ok(**_kwargs: object) -> int:
        return 0

    monkeypatch.setattr(design_terminal, "_run_stall_rust", rust_validation_ok)  # pyright: ignore[reportPrivateUsage]
    assert plan_review_normalize.stage_panel_init_failed(design_tmpdir=tmp_path, trigger=reason) == 0
    state = (tmp_path / "design-failure-terminal-state.env").read_text(encoding="utf-8")
    assert "TRIGGER=panel-init-failed" in state
    assert "BAIL_REASON=panel-init-failed" in state
    assert f"EVIDENCE_REF={evidence_ref}" in state

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


def test_step3_loop_persist_envelope_writes_mergeable_completion_kvs(tmp_path: Path) -> None:
    plan_review.step3_loop_persist_envelope(
        design_tmpdir=tmp_path,
        status="complete",
        round_num=1,
        rounds_completed=1,
        final_round=1,
        values={
            "ACCEPTED_COUNT": "2",
            "IMPORTANT_ACCEPTED_COUNT": "1",
            "TALLY_PLAN_REVIEW_STATUS": "ok",
            "AGGREGATOR_STATUS": "ok",
        },
    )

    result_lines = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8").splitlines()
    result = dict(line.split("=", 1) for line in result_lines)

    assert result["STEP3_REVIEW_LOOP_STATUS"] == "complete"
    assert result["LOOP_STATUS"] == "complete"
    assert result["ROUNDS_COMPLETED"] == "1"
    assert result["FINAL_ROUND_NUM"] == "1"
    assert result["ACCEPTED_COUNT"] == "2"
    assert result["IMPORTANT_ACCEPTED_COUNT"] == "1"
    assert result["TALLY_PLAN_REVIEW_STATUS"] == "ok"
    assert result["AGGREGATOR_STATUS"] == "ok"
    assert all("=" in line for line in result_lines)
    assert not any(line.startswith(">") or ("review" in line.lower() and "=" not in line) for line in result_lines)


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


def test_step3_loop_persist_envelope_writes_result_env(tmp_path: Path) -> None:
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values={})
    assert (tmp_path / ".step3-review-result.env").is_file()


def test_step3_loop_persist_envelope_midloop_bail_writes_result_env_only(tmp_path: Path) -> None:
    plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="main-agent-apply-required", round_num=2, rounds_completed=2, final_round=2, values={})
    assert (tmp_path / ".step3-review-result.env").is_file()
    assert not (tmp_path / ".completed" / "step-3").exists()


def test_phase_driver_write_result_env_refuses_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target.env"
    _ = target.write_text("", encoding="utf-8")
    link = tmp_path / ".step3-review-result.env"
    link.symlink_to(target)
    with pytest.raises(OSError, match="symlink"):
        plan_review.step3_loop_persist_envelope(design_tmpdir=tmp_path, status="complete", round_num=1, rounds_completed=1, final_round=1, values={})


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
    bgjob = tmp_path / "bgjob"
    completed.mkdir(parents=True, exist_ok=True)
    bgjob.mkdir(parents=True, exist_ok=True)
    for name in ("step-3", "step-3.5", "step-3", "step-3b", "step-4", "step-4b"):
        (completed / name).touch()
    _ = (bgjob / "design-step3-review.result.env").write_text("BGJOB_RC=0\nNEXT_ACTION=step3b\n", encoding="utf-8")
    _ = (bgjob / "design-step4-tail.result.env").write_text(
        "BGJOB_RC=0\nSKIP_APPROVE_REQUESTED_GATEC=false\n",
        encoding="utf-8",
    )
    (tmp_path / ".gate-b-postapply-ready-1").touch()
    (tmp_path / ".gate-b-postapply-ready-2").touch()


def _step3_bgjob_result_envs(tmp_path: Path) -> tuple[Path, Path]:
    return (
        tmp_path / "bgjob" / "design-step3-review.result.env",
        tmp_path / "bgjob" / "design-step4-tail.result.env",
    )


def test_step3_state_direct_review_entry_noop_without_reentry(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    proc = run_cli("plan-review", "step3-state", "--design-tmpdir", str(tmp_path), "--direct-review-entry")
    assert proc.returncode == 0, proc.stderr
    assert "STEP3_STATE=noop" in proc.stdout
    assert "REVIEW_ROUND_COUNT=0" in proc.stdout
    # No .step3-reentry breadcrumb -> nothing cleared.
    assert (tmp_path / ".completed" / "step-3").is_file()
    assert (tmp_path / ".completed" / "step-3").is_file()
    assert (tmp_path / ".gate-b-postapply-ready-1").is_file()
    for result_env in _step3_bgjob_result_envs(tmp_path):
        assert result_env.is_file()


def test_step3_state_direct_review_entry_clears_restores_and_consumes(tmp_path: Path) -> None:
    _seed_step3_downstream(tmp_path)
    (tmp_path / ".step3-reentry").touch()
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    # Settled round artifacts (<= round 2) plus a future round-3 artifact that must survive.
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
    for name in ("step-3", "step-3.5", "step-3", "step-3b", "step-4", "step-4b"):
        assert not (tmp_path / ".completed" / name).exists()
    assert not (tmp_path / ".gate-b-postapply-ready-1").exists()
    assert not (tmp_path / ".gate-b-postapply-ready-2").exists()
    for result_env in _step3_bgjob_result_envs(tmp_path):
        assert not result_env.exists()
    # Upstream package restored.
    for name in ("step-1e", "step-2a", "step-2b", "step-2b.5"):
        assert (tmp_path / ".completed" / name).is_file()
    # Settled rounds (<= 2) dropped, future round-3 artifact preserved.
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
    for result_env in _step3_bgjob_result_envs(tmp_path):
        assert not result_env.exists()
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
    for name in ("step-3", "step-3.5", "step-3", "step-3b", "step-4", "step-4b"):
        assert not (tmp_path / ".completed" / name).exists()
    assert not (tmp_path / ".gate-b-postapply-ready-1").exists()
    for result_env in _step3_bgjob_result_envs(tmp_path):
        assert not result_env.exists()
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


def test_record_report_evidence_writes_escalation_ledger(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "design-failure-escalation-ledger.tsv"

    def fake_run(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        assert argv[0].endswith("/scripts/larch.sh")
        assert argv[1:3] == ["stall-recovery", "record-escalation"]
        _ = ledger.write_text("utc=test\ttrigger=tally-error\tphase=validation\n", encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review_normalize.subprocess, "run", fake_run)
    rc = plan_review_normalize.step3_record_report_evidence(
        status="tally-error",
        design_tmpdir=tmp_path,
        cli_surface=True,
    )

    assert rc == 0
    assert ledger.exists()
    text = ledger.read_text(encoding="utf-8")
    assert "trigger=tally-error" in text
    assert "phase=validation" in text


@pytest.mark.parametrize(
    "status",
    ["main-agent-apply-required", "main-agent-vote-required", "postplan-operator-required"],
)
def test_record_report_evidence_skips_normal_handoffs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    status: str,
) -> None:
    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[object]:
        raise AssertionError("normal Step 3 handoffs must not call record-escalation")

    monkeypatch.setattr(plan_review_normalize.subprocess, "run", fail_run)
    assert plan_review_normalize.step3_record_report_evidence(status=status, design_tmpdir=tmp_path) == 0
    assert not (tmp_path / "design-failure-escalation-ledger.tsv").exists()
    assert not (tmp_path / "design-failure-escalation-fallback.tsv").exists()
    assert not (tmp_path / "design-failure-escalation-record-failure.env").exists()
    assert not list(tmp_path.glob(".step3-report-*.recorded"))


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


def _write_revise_ok_stub(tmp_path: Path) -> Path:
    """A revise-waterfall stub that rewrites the plan and reports success."""
    stub = tmp_path / "revise-stub.sh"
    _ = stub.write_text(
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
    stub.chmod(0o755)
    return stub


def _write_exit0_stub(tmp_path: Path, name: str) -> Path:
    stub = tmp_path / name
    _ = stub.write_text("#!/usr/bin/env bash\nset -euo pipefail\nexit 0\n", encoding="utf-8")
    stub.chmod(0o755)
    return stub


def _write_continuation_stop_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "continuation-stub.sh"
    _ = stub.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\n"
        "printf 'PLAN_REVIEW_CONTINUE=false\\nPLAN_REVIEW_CONTINUE_REASON=small-clean\\n'\n",
        encoding="utf-8",
    )
    stub.chmod(0o755)
    return stub


def test_loop_accepted_findings_autonomously_revised_via_waterfall(tmp_path: Path) -> None:
    # Default (approve_requested=false): accepted findings are applied autonomously by
    # the revise-waterfall inside the background loop. The main agent is NOT pulled in
    # for the routine apply; it only sees a terminal status.
    _write_run_params(tmp_path)
    original = (tmp_path / "plan.txt").read_text(encoding="utf-8")
    round_stub = _write_loop_stub(
        tmp_path,
        (
            f"cat >\"{tmp_path}/accepted-plan-findings.md\" <<'FINDINGS'\n"
            "### FINDING_1: Important\n- **Severity**: major\n- **Concern**: issue\n"
            "FINDINGS\n"
            "printf 'LOOP_STATUS=complete\\nACCEPTED_COUNT=1\\nIMPORTANT_ACCEPTED_COUNT=1\\n"
            "DEGRADED_PANEL=0\\nROUNDS_COMPLETED=1\\nTALLY_PLAN_REVIEW_STATUS=ok\\n"
            "AGGREGATOR_STATUS=ok\\nVOTING_TALLY_FILE=\\n'"
        ),
    )
    revise_stub = _write_revise_ok_stub(tmp_path)
    dedup_stub = _write_exit0_stub(tmp_path, "dedup-stub.sh")
    postplan_stub = _write_exit0_stub(tmp_path, "postplan-stub.sh")
    continuation_stub = _write_continuation_stop_stub(tmp_path)

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
            "RUN_STEP3_POSTPLAN_EMIT_SH": str(postplan_stub),
            "RUN_STEP3_CONTINUATION_SH": str(continuation_stub),
        },
    )

    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in proc.stdout
    assert "main-agent-apply-required" not in proc.stdout
    revised = (tmp_path / "plan.txt").read_text(encoding="utf-8")
    assert revised != original
    assert "# revised" in revised


def test_loop_resume_awaiting_apply_rebails_to_inline_gate_b(tmp_path: Path) -> None:
    # awaiting-apply is the main-agent Gate B resume point (per-round-approval, or a
    # prior waterfall failure). With no post-apply marker it re-bails to the main agent.
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-1.phase").write_text("awaiting-apply\n", encoding="utf-8")
    _ = (tmp_path / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Important\n- **Severity**: major\n- **Concern**: issue\n",
        encoding="utf-8",
    )
    forbidden_round_stub = _write_loop_stub(tmp_path, "exit 99")

    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        "--starting-round",
        "1",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(forbidden_round_stub),
        },
    )

    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required" in proc.stdout
    assert "NEXT_ACTION=gate-b" in proc.stdout
    assert (tmp_path / ".step3-round-1.phase").read_text(encoding="utf-8") == "awaiting-apply\n"


def test_loop_resume_awaiting_revise_reruns_waterfall_and_bails_only_on_failure(tmp_path: Path) -> None:
    # awaiting-revise re-runs the autonomous waterfall on resume. Only an irreconcilable
    # revision failure bails to the main-agent Gate B path, leaving phase at awaiting-apply.
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-1.phase").write_text("awaiting-revise\n", encoding="utf-8")
    _ = (tmp_path / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Important\n- **Severity**: major\n- **Concern**: issue\n",
        encoding="utf-8",
    )
    forbidden_round_stub = _write_loop_stub(tmp_path, "exit 99")
    revise_fail_stub = tmp_path / "revise-fail-stub.sh"
    _ = revise_fail_stub.write_text(
        "#!/usr/bin/env bash\nset -euo pipefail\nprintf 'REVISE_STATUS=failed-no-patch\\n'\n",
        encoding="utf-8",
    )
    revise_fail_stub.chmod(0o755)

    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        "--starting-round",
        "1",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_PLAN_REVIEW_LOOP_SH": str(forbidden_round_stub),
            "RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH": str(revise_fail_stub),
        },
    )

    assert proc.returncode == 0, proc.stderr
    assert "STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required" in proc.stdout
    assert "NEXT_ACTION=gate-b" in proc.stdout
    assert (tmp_path / ".step3-round-1.phase").read_text(encoding="utf-8").strip() == "awaiting-apply"


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
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
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
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "2\n"
    assert (tmp_path / ".completed" / "step-3").is_file()


def test_tally_error_rollback_review_round_count(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
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
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "1\n"
    result_env = (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert "STEP3_REVIEW_LOOP_STATUS=tally-error" in result_env
    assert "LOOP_STATUS=tally-error" in result_env


def test_degraded_empty_collector_rollback_review_round_count(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
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
    assert "LOOP_STATUS=panel-failed" not in proc.stdout
    assert "LOOP_STATUS=tally-error" not in proc.stdout
    assert (tmp_path / "review-round-count.txt").read_text(encoding="utf-8") == "1\n"


def test_orphan_timeout_uses_detached_epoch_not_marker_mtime(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "plan-review-scope-anchor.txt").write_text("anchor\n", encoding="utf-8")
    marker = tmp_path / ".step3-wrapper-detached"
    _ = marker.write_text(
        "PID=123\nSIGNAL=TERM\nSTDOUT_FILE=/tmp/out\nDETACHED_AT_EPOCH=1\n",
        encoding="utf-8",
    )
    future_mtime = 2_000_000_000
    os.utime(marker, (future_mtime, future_mtime))
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        "--orphan-timeout-s",
        "1",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc.returncode == 0, proc.stderr
    assert "REASON=orphan-timeout" in proc.stdout
    assert "STEP3_REVIEW_LOOP_STATUS=panel-failed" in proc.stdout
    assert "NEXT_ACTION=step3b-bypass" in proc.stdout


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


def test_loop_dedup_failure_restores_plan_snapshot(tmp_path: Path) -> None:
    _write_run_params(tmp_path)
    original = "# Plan\n\ndiff_lines: 1\n"
    _ = (tmp_path / "plan.txt").write_text("# Plan\n\nmutated\ndiff_lines: 2\n", encoding="utf-8")
    snapshot = tmp_path / "plan-pre-apply-round-1.txt"
    _ = snapshot.write_text(original, encoding="utf-8")
    _ = (tmp_path / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Important\n- **Severity**: major\n- **Concern**: issue\n",
        encoding="utf-8",
    )
    _ = (tmp_path / ".step3-round-1.phase").write_text("awaiting-post-apply\n", encoding="utf-8")
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
    proc = run_cli(
        "plan-review",
        "run",
        "--design-tmpdir",
        str(tmp_path),
        "--mode",
        "loop",
        env={
            "LARCH_QUIET_DISABLE": "1",
            "RUN_STEP3_DEDUP_PLAN_SH": str(dedup_stub),
        },
    )
    assert "STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required" in proc.stdout
    assert "DEDUP_RC=2" in proc.stdout
    assert snapshot.is_file()
    assert (tmp_path / "plan.txt").read_text(encoding="utf-8") == snapshot.read_text(encoding="utf-8")


def test_terminal_zero_accepted_round_writes_round_meta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Regression for #4811: a plan-review run that stops on a 0-accepted final
    # round must still write round-meta.json for that round, so the Review Phase
    # Detail table includes it and the table row count matches the header count.
    _write_run_params(tmp_path)
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)

    def fake_round(_argv: list[str]) -> int:
        print("LOOP_STATUS=complete")
        print("ACCEPTED_COUNT=0")
        print("DEGRADED_PANEL=0")
        print("TALLY_PLAN_REVIEW_STATUS=ok")
        return 0

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["progress", "write-design-round-meta"]:
            target = Path(argv[argv.index("--round-dir") + 1])
            _ = (target / "round-meta.json").write_text('{"tally":{"ACCEPTED_COUNT":0}}\n', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review, "run_plan_review_round", fake_round)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setattr(
        plan_review,
        "_run_continuation",
        lambda *_args, **_kwargs: {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "small-clean"},
    )

    assert plan_review.run_step3_review(["--design-tmpdir", str(tmp_path), "--mode", "loop"]) == 0
    # The terminal 0-accepted round now has round-meta.json, so _completed_round_dirs
    # (the Review Phase Detail source set) includes it. Before the fix it was absent.
    assert (round_dir / "round-meta.json").is_file()


def test_inline_gate_b_postapply_writes_round_meta(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_run_params(tmp_path)
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (tmp_path / ".step3-round-1.phase").write_text("awaiting-post-apply\n", encoding="utf-8")
    (tmp_path / ".gate-b-postapply-ready-1").touch()
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        if argv[1:3] == ["progress", "write-design-round-meta"]:
            target = Path(argv[argv.index("--round-dir") + 1])
            _ = (target / "round-meta.json").write_text('{"tally":{"ACCEPTED_COUNT":1}}\n', encoding="utf-8")
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setattr(
        plan_review,
        "_run_post_apply",
        lambda *, tmpdir, round_num, values: (
            values,
            plan_review._write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation") or 0,  # pyright: ignore[reportPrivateUsage]
        )[1],
    )
    monkeypatch.setattr(
        plan_review,
        "_run_continuation",
        lambda *_args, **_kwargs: {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "small-clean"},
    )

    assert plan_review.run_step3_review(
        ["--design-tmpdir", str(tmp_path), "--mode", "loop", "--starting-round", "1"]
    ) == 0
    assert (round_dir / "round-meta.json").is_file()


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

    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=2)  # pyright: ignore[reportPrivateUsage]

    assert calls == [
        [
            str(plan_review.larch_entrypoint(plan_review._plugin_root())),  # pyright: ignore[reportPrivateUsage]
            "progress",
            "write-design-round-meta",
            "--round-dir",
            str(tmp_path / "plan-review" / "round-2"),
        ]
    ]


def test_zero_accepted_round_ignores_round_meta_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _write_run_params(tmp_path)

    def failed_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 1, "", "boom")

    def fake_run_plan_review_round(_argv: list[str]) -> int:
        print("LOOP_STATUS=complete")
        print("ACCEPTED_COUNT=0")
        print("DEGRADED_PANEL=0")
        print("ROUNDS_COMPLETED=1")
        print("TALLY_PLAN_REVIEW_STATUS=ok")
        print("AGGREGATOR_STATUS=ok")
        return 0

    monkeypatch.setattr(plan_review, "_run_command", failed_run_command)
    monkeypatch.setattr(plan_review, "run_plan_review_round", fake_run_plan_review_round)

    rc = plan_review.run_step3_review(["--design-tmpdir", str(tmp_path)])

    assert rc == 0
    assert "STEP3_REVIEW_LOOP_STATUS=complete" in (tmp_path / ".step3-review-result.env").read_text(encoding="utf-8")
    assert (tmp_path / ".step3-round-1.phase").read_text(encoding="utf-8") == "awaiting-continuation\n"


def test_design_round_timing_uses_rust_owner_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = _install_rust_timing_stubs(monkeypatch)
    def _window(round_num: int) -> tuple[int, int] | None:
        return _timing_round_window(
            tmp_path / "timing-ledger.tsv", skill="design", round_num=round_num, skill_filtered=True
        )

    plan_review_loop._append_canonical_round_timing(  # pyright: ignore[reportPrivateUsage]
        tmpdir=tmp_path,
        round_num=1,
        start_s=100,
        end_s=110,
    )
    ledger = tmp_path / "timing-ledger.tsv"

    assert _window(1) == (100, 110)
    rows = [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("v1\tround\t")]
    assert len(rows) == 1
    assert rows[0][3] == "design"
    assert rows[0][5] == "1"
    assert len(rows[0]) >= 8

    plan_review_loop._append_canonical_round_timing(  # pyright: ignore[reportPrivateUsage]
        tmpdir=tmp_path,
        round_num=1,
        start_s=100,
        end_s=110,
    )
    rows_after = [line for line in ledger.read_text(encoding="utf-8").splitlines() if line.startswith("v1\tround\t")]
    assert len(rows_after) == 1

    plan_review_loop._append_canonical_round_timing(  # pyright: ignore[reportPrivateUsage]
        tmpdir=tmp_path,
        round_num=4,
        start_s=400,
        end_s=410,
    )
    assert _window(4) == (400, 410)
    assert [call["verb"] for call in calls] == ["record-round", "record-round", "record-round"]
    assert calls[0]["if_round_exists"] is True
    assert calls[1]["if_round_exists"] is True
    assert calls[0]["environment"] == {"DESIGN_TMPDIR": str(tmp_path)}


def test_write_design_round_meta_records_round_timing_from_start_file(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-start-s").write_text("1000\n", encoding="utf-8")
    _ = _install_rust_timing_stubs(monkeypatch)

    # Isolate the timing side effect from the round-meta subprocess and freeze the end clock.
    monkeypatch.setattr(plan_review, "_run_command", lambda *_a, **_k: None)  # type: ignore[arg-type]
    monkeypatch.setattr(plan_review.time, "time", lambda: 1200)  # type: ignore[arg-type]

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=1)  # pyright: ignore[reportPrivateUsage]

    window = _timing_round_window(
        tmp_path / "timing-ledger.tsv", skill="design", round_num=1, skill_filtered=True
    )
    assert window == (1000, 1200)
    assert "gate-b-apply" not in (tmp_path / "timing-ledger.tsv").read_text(encoding="utf-8")


def _write_design_vendor_timing(
    ledger: Path,
    *,
    kind: str,
    start_s: int,
    end_s: int,
    output: str = "reviewer.out",
    vendor: str = "codex",
    skill: str = "design",
) -> None:
    duration = max(0, end_s - start_s)
    with ledger.open("a", encoding="utf-8") as handle:
        _ = handle.write(
            f"v1\tvendor\t{end_s}\t{skill}\t-\t{vendor}\t{kind}\t"
            f"{start_s}\t{end_s}\t{duration}\t{output}\t0\tcomplete\n"
        )


def test_gate_b_apply_start_s_missing_or_empty_ledger_returns_none(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"

    assert (
        plan_review_loop._gate_b_apply_start_s(  # pyright: ignore[reportPrivateUsage]
            ledger=ledger,
            round_start_s=1000,
            end_s=1200,
            output_basename="gate-b-apply-round-1.out",
        )
        is None
    )

    _ = ledger.write_text("", encoding="utf-8")
    assert (
        plan_review_loop._gate_b_apply_start_s(  # pyright: ignore[reportPrivateUsage]
            ledger=ledger,
            round_start_s=1000,
            end_s=1200,
            output_basename="gate-b-apply-round-1.out",
        )
        is None
    )


@pytest.mark.parametrize("latest_end_s", [1200, 1201])
def test_gate_b_apply_start_s_rejects_boundary_and_after_end(
    tmp_path: Path,
    latest_end_s: int,
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_design_vendor_timing(
        ledger,
        kind="codex-plan-requirements",
        start_s=1010,
        end_s=latest_end_s,
    )

    assert (
        plan_review_loop._gate_b_apply_start_s(  # pyright: ignore[reportPrivateUsage]
            ledger=ledger,
            round_start_s=1000,
            end_s=1200,
            output_basename="gate-b-apply-round-1.out",
        )
        is None
    )


def test_gate_b_apply_start_s_unreadable_ledger_returns_none(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_design_vendor_timing(
        ledger,
        kind="codex-plan-requirements",
        start_s=1010,
        end_s=1100,
    )
    real_read_text = Path.read_text

    def fail_target_read_text(self: Path, encoding: str | None = None, errors: str | None = None) -> str:
        if self == ledger:
            raise OSError("blocked ledger")
        return real_read_text(self, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", fail_target_read_text)

    assert (
        plan_review_loop._gate_b_apply_start_s(  # pyright: ignore[reportPrivateUsage]
            ledger=ledger,
            round_start_s=1000,
            end_s=1200,
            output_basename="gate-b-apply-round-1.out",
        )
        is None
    )


def test_gate_b_apply_start_s_existing_output_basename_returns_none(tmp_path: Path) -> None:
    ledger = tmp_path / "timing-ledger.tsv"
    _write_design_vendor_timing(
        ledger,
        kind="codex-plan-requirements",
        start_s=1010,
        end_s=1100,
    )
    _write_design_vendor_timing(
        ledger,
        kind="gate-b-apply",
        start_s=1100,
        end_s=1200,
        output="gate-b-apply-round-1.out",
        vendor="claude",
    )

    assert (
        plan_review_loop._gate_b_apply_start_s(  # pyright: ignore[reportPrivateUsage]
            ledger=ledger,
            round_start_s=1000,
            end_s=1250,
            output_basename="gate-b-apply-round-1.out",
        )
        is None
    )


def test_write_design_round_meta_with_gate_b_apply_ready_marker_without_vendor_rows(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-start-s").write_text("1000\n", encoding="utf-8")
    (tmp_path / ".gate-b-postapply-ready-1").touch()
    _ = _install_rust_timing_stubs(monkeypatch)

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setattr(plan_review.time, "time", lambda: 1200)  # type: ignore[arg-type]

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=1)  # pyright: ignore[reportPrivateUsage]

    ledger_text = (tmp_path / "timing-ledger.tsv").read_text(encoding="utf-8")
    assert "gate-b-apply" not in ledger_text
    window = _timing_round_window(
        tmp_path / "timing-ledger.tsv", skill="design", round_num=1, skill_filtered=True
    )
    assert window == (1000, 1200)


@pytest.mark.parametrize("vendor_skill", ["design", "implement"])
def test_write_design_round_meta_records_gate_b_apply_timing_idempotently(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    vendor_skill: str,
) -> None:
    round_dir = tmp_path / "plan-review" / "round-1"
    round_dir.mkdir(parents=True)
    _ = (round_dir / "round-start-s").write_text("1000\n", encoding="utf-8")
    (tmp_path / ".gate-b-postapply-ready-1").touch()
    ledger = tmp_path / "timing-ledger.tsv"
    _write_design_vendor_timing(
        ledger,
        kind="codex-plan-requirements",
        start_s=1010,
        end_s=1050,
        output="codex.out",
        vendor="codex",
        skill=vendor_skill,
    )
    _ = _install_rust_timing_stubs(monkeypatch)
    _write_design_vendor_timing(
        ledger,
        kind="claude-plan-voter",
        start_s=1060,
        end_s=1125,
        output="claude-vote.out",
        vendor="claude",
        skill=vendor_skill,
    )

    def fake_run_command(argv: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(argv, 0, "", "")

    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setattr(plan_review.time, "time", lambda: 1200)  # type: ignore[arg-type]

    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=1)  # pyright: ignore[reportPrivateUsage]
    plan_review._write_design_round_meta(tmpdir=tmp_path, round_num=1)  # pyright: ignore[reportPrivateUsage]

    rows = [line.split("\t") for line in ledger.read_text(encoding="utf-8").splitlines()]
    gate_b_rows = [row for row in rows if len(row) >= 13 and row[1] == "vendor" and row[6] == "gate-b-apply"]
    assert len(gate_b_rows) == 1
    assert gate_b_rows[0][3] == "design"
    assert gate_b_rows[0][5] == "claude"
    assert gate_b_rows[0][7] == "1125"
    assert gate_b_rows[0][8] == "1200"
    assert gate_b_rows[0][10] == "gate-b-apply-round-1.out"

    window = _timing_round_window(ledger, skill="design", round_num=1, skill_filtered=True)
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
            severity="major",
            location="python/plan_review.py:1039",
            concern="continuation re-triggers on duplicate findings. Scenario: round 2 re-raises round 1.",
        )
        + _high_finding_block(
            2,
            severity="major",
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
    # Both findings are high-severity and new -> round-total escalates to HARD.
    assert "PLAN_REVIEW_CONTINUE_REASON=escalated-high-accepted" in proc1.stdout

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
    assert "PLAN_REVIEW_CONTINUE_REASON=cap-reached" in proc2.stdout
    assert "DUPLICATE_ACCEPTED_COUNT=2" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=0" in proc2.stdout
    # Totals stay reported for backward compatibility.
    assert "HIGH_ACCEPTED_COUNT=2" in proc2.stdout


def test_continuation_escalates_on_cumulative_highs_with_one_new_finding(tmp_path: Path) -> None:
    finding1 = _high_finding_block(
        1,
        severity="major",
        location="a.py:1",
        concern="alpha. Scenario: x.",
    )
    finding2 = _high_finding_block(
        2,
        severity="major",
        location="b.py:2",
        concern="beta. Scenario: y.",
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(finding1, encoding="utf-8")
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
    assert "PLAN_REVIEW_CONTINUE_REASON=high-accepted" in proc1.stdout

    round1_escalation = tmp_path / "round1-escalation"
    round1_escalation.mkdir()
    _ = (round1_escalation / "accepted-plan-findings.md").write_text(finding1 + finding2, encoding="utf-8")
    _ = (round1_escalation / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc_escalation = run_cli(
        "plan-review",
        "continuation",
        "--design-tmpdir",
        str(round1_escalation),
        "--approve-requested",
        "false",
        env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert proc_escalation.returncode == 0, proc_escalation.stderr
    assert "PLAN_REVIEW_CONTINUE=true" in proc_escalation.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=escalated-high-accepted" in proc_escalation.stdout
    assert "REVIEW_ROUND_CAP=2" in proc_escalation.stdout
    escalated_record = json.loads((round1_escalation / difficulty.DIFFICULTY_RECORD_BASENAME).read_text(encoding="utf-8"))
    assert escalated_record["round_cap"] == 2

    _ = (tmp_path / "accepted-plan-findings.md").write_text(finding1 + finding2, encoding="utf-8")
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
    assert "PLAN_REVIEW_CONTINUE_REASON=cap-reached" in proc2.stdout
    assert "REVIEW_ROUND_CAP=2" in proc2.stdout
    assert "HIGH_ACCEPTED_COUNT=2" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=1" in proc2.stdout


def test_continuation_continues_when_a_new_finding_appears(tmp_path: Path) -> None:
    round1 = _high_finding_block(
        1, severity="major", location="a.py:1", concern="alpha. Scenario: x."
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(round1, encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc1 = run_cli(
        "plan-review", "continuation", "--design-tmpdir", str(tmp_path),
        "--approve-requested", "false", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "PLAN_REVIEW_CONTINUE=true" in proc1.stdout

    round1_escalation = tmp_path / "round1-escalation"
    round1_escalation.mkdir()
    _ = (round1_escalation / "accepted-plan-findings.md").write_text(
        round1 + _high_finding_block(2, severity="major", location="b.py:2", concern="beta. Scenario: y."),
        encoding="utf-8",
    )
    _ = (round1_escalation / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    proc_escalation = run_cli(
        "plan-review", "continuation", "--design-tmpdir", str(round1_escalation),
        "--approve-requested", "false", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "PLAN_REVIEW_CONTINUE=true" in proc_escalation.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=escalated-high-accepted" in proc_escalation.stdout
    assert "REVIEW_ROUND_CAP=2" in proc_escalation.stdout

    # Round 2: re-raises round-1 finding (duplicate) plus a brand-new high one.
    round2 = round1 + _high_finding_block(
        2, severity="major", location="b.py:2", concern="beta. Scenario: y."
    )
    _ = (tmp_path / "accepted-plan-findings.md").write_text(round2, encoding="utf-8")
    _ = (tmp_path / "review-round-count.txt").write_text("2\n", encoding="utf-8")
    proc2 = run_cli(
        "plan-review", "continuation", "--design-tmpdir", str(tmp_path),
        "--approve-requested", "false", env={"LARCH_QUIET_DISABLE": "1"},
    )
    assert "PLAN_REVIEW_CONTINUE=false" in proc2.stdout
    assert "PLAN_REVIEW_CONTINUE_REASON=cap-reached" in proc2.stdout
    assert "REVIEW_ROUND_CAP=2" in proc2.stdout
    assert "DUPLICATE_ACCEPTED_COUNT=1" in proc2.stdout
    assert "NEW_HIGH_ACCEPTED_COUNT=1" in proc2.stdout


def test_resolve_plan_review_tier_seeds_plan_metadata_hard(tmp_path: Path) -> None:
    record = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "bootstrap"}
        ),
    )
    difficulty.write_record(tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME, record)
    _ = (tmp_path / "plan.txt").write_text("## Plan\nbody\n\ndifficulty: HARD\ndiff_lines: 1\n", encoding="utf-8")

    resolution = plan_review_common.resolve_plan_review_tier(tmp_path)
    data = json.loads((tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME).read_text(encoding="utf-8"))

    assert resolution.panel_tier == difficulty.HARD
    assert data["panel_tier"] == difficulty.HARD


def test_resolve_plan_review_tier_seeds_raw_sidecar_hard(tmp_path: Path) -> None:
    record = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "bootstrap"}
        ),
    )
    difficulty.write_record(tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME, record)
    _ = (tmp_path / difficulty.DESIGN_RAW_RATING_BASENAME).write_text(
        '{"predicted_tier":"HARD","confidence":"high","rationale":"raw"}\n',
        encoding="utf-8",
    )
    _ = (tmp_path / "plan.txt").write_text("## Plan\nbody\n\ndifficulty: TRIVIAL\ndiff_lines: 1\n", encoding="utf-8")

    resolution = plan_review_common.resolve_plan_review_tier(tmp_path)
    data = json.loads((tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME).read_text(encoding="utf-8"))

    assert resolution.panel_tier == difficulty.HARD
    assert data["panel_tier"] == difficulty.HARD


def test_design_escalation_authorized_rejects_bare_high_accepted(tmp_path: Path) -> None:
    record = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "HARD", "confidence": "high", "rationale": "seed"}
        ),
    )
    difficulty.write_record(tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME, record)
    _ = (tmp_path / ".step3-review-result.env").write_text(
        "PLAN_REVIEW_CONTINUE_REASON=high-accepted\n",
        encoding="utf-8",
    )

    assert not plan_review_common.design_escalation_authorized(tmp_path)
    assert plan_review_common.effective_authorized_cap(tmp_path, tier=difficulty.HARD) == 2


@pytest.mark.parametrize("reason", ["non-nit-accepted", "structural-or-large-change", "degraded-panel"])
def test_design_escalation_authorized_rejects_generic_continuation_reasons(tmp_path: Path, reason: str) -> None:
    record = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "HARD", "confidence": "high", "rationale": "seed"}
        ),
    )
    difficulty.write_record(tmp_path / difficulty.DIFFICULTY_RECORD_BASENAME, record)
    _ = (tmp_path / ".step3-review-result.env").write_text(
        f"PLAN_REVIEW_CONTINUE_REASON={reason}\n",
        encoding="utf-8",
    )

    assert not plan_review_common.design_escalation_authorized(tmp_path)


def test_continuation_degraded_panel_converges_on_duplicate_findings(tmp_path: Path) -> None:
    # Degraded-panel continuation must not bypass cross-round dedup (#4808).
    findings = _high_finding_block(
        1,
        severity="major",
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
    assert "PLAN_REVIEW_CONTINUE_REASON=cap-reached" in proc2.stdout
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


def test_step3_loop_zero_findings_clears_stale_accepted_and_awaits_continuation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Multi-round converged zero-findings must not re-enter Gate B apply via stale tally artifacts (#5032)."""
    design = tmp_path
    _write_run_params(design)
    _ = (design / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 1\n- **Concern**: already applied\n",
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
    monkeypatch.setattr(plan_review_round, "_run_larch", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "2"])

    assert rc == 0
    assert (design / ".step3-round-2.phase").read_text(encoding="utf-8") == "awaiting-continuation\n"
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
    assert result_env["ROUNDS_COMPLETED"] == "2", result_env
    assert result_env["REVIEW_ROUND_COUNT"] == "2", result_env
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
    _ = (design / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 1\n- **Concern**: already applied\n",
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
    monkeypatch.setattr(plan_review_round, "_run_larch", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "2"])

    assert rc == 0
    out = capsys.readouterr().out
    assert "LOOP_STATUS=zero-findings-degraded-panel" in out, out
    assert "NEXT_ACTION=step3b" in out, out
    assert "ROUNDS_COMPLETED=2" in out, out
    assert "REVIEW_ROUND_COUNT=2" in out, out


def test_step3_loop_zero_findings_degraded_stop_records_completions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The final zero-findings-degraded-panel stop path must write step-3 sentinels."""
    design = tmp_path
    _write_run_params(design)
    _ = (design / "review-round-count.txt").write_text("1\n", encoding="utf-8")
    _ = (design / "accepted-plan-findings.md").write_text(
        "### FINDING_1: Stale from round 1\n- **Concern**: already applied\n",
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
    monkeypatch.setattr(plan_review_round, "_run_larch", fake_run_cli)
    monkeypatch.setattr(plan_review, "_run_command", fake_run_command)
    monkeypatch.setenv("RUN_STEP3_CONTINUATION_SH", str(continuation_stub))

    rc = plan_review.run_step3_review(["--design-tmpdir", str(design), "--starting-round", "2"])

    assert rc == 0
    assert (design / ".completed" / "step-3").is_file()
    assert (design / ".completed" / "step-3").is_file()


def test_step3_loop_postplan_validator_runs_from_consumer_cwd(tmp_path: Path) -> None:
    # #4847: the Step 3 plan-review loop must invoke `design postplan-emit` from
    # the consumer-repo cwd (not the plugin cache that `_run_command` otherwise
    # forces), so the validator derives the consumer repo and consumer-only
    # plan-command scripts are not false-flagged missing-script. End-to-end check
    # mirroring the #4490 postplan test in test_design_postplan.py.
    plugin_root = tmp_path / "plugin"
    plugin_root.joinpath("python").mkdir(parents=True)
    plugin_root.joinpath("scripts").mkdir()
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
    fake_entrypoint = plugin_root / "scripts" / "larch.sh"
    _ = fake_entrypoint.write_text(
        '#!/usr/bin/env bash\nexec "$CLAUDE_PLUGIN_ROOT/python/cli.py" "$@"\n',
        encoding="utf-8",
    )
    fake_entrypoint.chmod(fake_entrypoint.stat().st_mode | stat.S_IXUSR)
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

    cli_py = Path(__file__).resolve().parents[2] / "cli.py"
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


def test_plan_review_progress_note_uses_run_aware_breadcrumb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """plan_review._progress_note uses the Rust breadcrumb seam with its run ID."""
    monkeypatch.setenv("LARCH_RUN_ID", "pr-run-11")
    monkeypatch.chdir(tmp_path)

    breadcrumb_calls: list[tuple[str, str, str, str]] = []

    def fake_append(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        skill: str,
        step: str,
        text: str,
        cwd: str | None = None,
    ) -> bool:
        _ = repo_root, cwd
        breadcrumb_calls.append((run_id, skill, step, text))
        return True

    monkeypatch.setattr(plan_review.rust_runtime, "progress_note", fake_append)

    plan_review._progress_note(step="3", text="dispatching reviewers")  # pyright: ignore[reportPrivateUsage]

    assert len(breadcrumb_calls) == 1
    assert breadcrumb_calls[0][0] == "pr-run-11"
    assert breadcrumb_calls[0][3] == "dispatching reviewers"
