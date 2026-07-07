"""Step 3 result-env normalization, terminal sentinels, and escalation recording."""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from collections.abc import Sequence

from larch.core import logging_util
from larch.core.config import BGJOB_RC_KEY, STEP3_ESCALATION_FAILURE_STATUSES
from larch.design.design_lifecycle import (
    capture_contract_stream_to_paths,
    _classify_input,  # pyright: ignore[reportPrivateUsage]
    _replay_warn_error,  # pyright: ignore[reportPrivateUsage]
    load_bash_quoted_env,
    phase_driver_read_result_env,
    phase_driver_write_result_env,
    read_result_env_main,
    stage_terminal_state_core,
)
from larch.review.plan_review_common import (
    _REPO_ROOT,
    _emit_kv,
    _plugin_root,
    _require_tmpdir,
    _validate_tmpdir_arg,
    _write_atomic,
)


def _write_phase(*, tmpdir: Path, round_num: int, phase: str) -> None:
    _write_atomic(path=tmpdir / f".step3-round-{round_num}.phase", content=f"{phase}\n")


def step3_loop_write_completed_step3(design_tmpdir: str | Path) -> None:
    completed = Path(design_tmpdir) / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-3").touch()
    (completed / "step-3.5").touch()


def step3_wrapper_write_completed_step3_only(design_tmpdir: str | Path) -> None:
    completed = Path(design_tmpdir) / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-3").touch()


def step3_loop_write_terminal_step3(design_tmpdir: str | Path) -> None:
    # #4688 terminal-sentinel contract: after the result env persists, write the
    # hook-release sentinel pair so hook-bg-poll-guard.sh releases the live
    # design-step3-review marker on the first <task-notification> and the
    # wrapper EXIT trap can guarantee step-3-terminal. Distinct from .completed/step-3
    # (the pause / Gate B milestone): mid-loop bail-outs write step-3-terminal
    # without step-3. Written on every terminal envelope persist, including the
    # apply-required / vote-required mid-loop bails.
    tmpdir = Path(design_tmpdir)
    completed = tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    terminal = completed / "step-3-terminal"
    sidecar = tmpdir / ".step3-terminal-persisted-this-run"
    for path in (terminal, sidecar):
        path.unlink(missing_ok=True)
    terminal.touch()
    sidecar.touch()


def _step3_normalize_write_terminal_sentinel(design_tmpdir: Path) -> None:
    # #5418 Fix A: write step-3-terminal ONLY (no sidecar) so the harness probe
    # returns success before KV output triggers a <task-notification>, without
    # engaging the EXIT trap's step-3 minting path (which requires the sidecar).
    completed = design_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    terminal = completed / "step-3-terminal"
    terminal.unlink(missing_ok=True)
    terminal.touch()


def step3_loop_status_to_loop_status(*, status: str, fallback: str = "complete") -> str:
    if status == "complete" and fallback == "zero-findings-degraded-panel":
        return fallback
    if status == "cap-hit":
        return "cap-reached"
    if status in {
        "complete",
        "main-agent-vote-required",
        "postplan-failed",
        "panel-failed",
        "panel-init-failed",
        "tally-error",
        "degraded-empty-collector",
    }:
        return status
    if status in {"main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"}:
        return "complete"
    return fallback or "complete"



STEP3_NORMALIZE_ALLOW_KEYS = (
    "NEXT_ACTION",
    BGJOB_RC_KEY,
    "LOOP_STATUS",
    "STEP3_REVIEW_LOOP_STATUS",
    "POSTPLAN_RC",
    "DEDUP_RC",
    "PLAN_REVIEW_CONTINUE_REASON",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "IMPORTANT_ACCEPTED_COUNT",
    "DEGRADED_PANEL",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "ROUNDS_COMPLETED",
    "TALLY_PLAN_REVIEW_STATUS",
    "AGGREGATOR_STATUS",
    "VOTING_TALLY_FILE",
    "SCOPE_ANCHOR_FILE",
    "STEP3_REVIEW_CAP_REACHED",
    "STEP3_REVIEW_ROUND_NUM",
    "ROUND_NUM",
    "REVIEW_ROUND_COUNT",
    "REASON",
)
_STEP3_READ_RESULT_ENV_KEYS = (
    BGJOB_RC_KEY,
    "NEXT_ACTION",
    "STEP3_REVIEW_LOOP_STATUS",
    "LOOP_STATUS",
    "ROUNDS_COMPLETED",
    "FINAL_ROUND_NUM",
    "ACCEPTED_COUNT",
    "DEGRADED_PANEL_WARNING",
    "INVALID_SLOT_PANEL_WARNING",
    "REASON",
)
_STEP3_STATUS_VALUES = {
    "complete",
    "cap-hit",
    "main-agent-vote-required",
    "main-agent-apply-required",
    "per-round-approval-required",
    "postplan-operator-required",
    "postplan-failed",
    "panel-failed",
    "panel-init-failed",
    "tally-error",
    "degraded-empty-collector",
}
_STEP3_LOOP_STATUS_VALUES = {
    "complete",
    "cap-reached",
    "zero-findings-degraded-panel",
    "tally-error",
    "degraded-empty-collector",
    "panel-failed",
    "panel-init-failed",
    "main-agent-vote-required",
    "main-agent-apply-required",
    "per-round-approval-required",
    "postplan-operator-required",
    "postplan-failed",
}
_STEP3_EVIDENCE_STATUSES = set(STEP3_ESCALATION_FAILURE_STATUSES)
_STEP3_SYNTHESIS_STATUSES = {"panel-failed", "panel-init-failed", "tally-error", "degraded-empty-collector", "postplan-failed"}
# Statuses that require interactive main-agent action mid-loop; sentinel must NOT
# be written in normalize for these because the loop is not yet in a terminal state.
_STEP3_INTERACTIVE_STATUSES = {"main-agent-vote-required", "main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"}
_STEP3_COMPLETED_SENTINEL_STATUSES = {"complete", "cap-hit", "panel-failed", "panel-init-failed", "tally-error", "degraded-empty-collector", "postplan-failed"}
_STEP3_SUMMARY_FAILED_POSTPLAN = "SUMMARY_OUTCOME=failed-postplan"
_STEP3_SUMMARY_FAILED_JUDGE_PANEL = "SUMMARY_OUTCOME=failed-judge-panel"
_STEP3_NEXT_ACTION_BY_STATUS = {
    "complete": "step3b",
    "cap-hit": "step3b-bypass",
    "main-agent-vote-required": "mav",
    "main-agent-apply-required": "gate-b",
    "per-round-approval-required": "gate-b",
    "postplan-operator-required": "postplan-operator",
    "postplan-failed": "final-summary:failed-postplan",
    "panel-failed": "step3b-bypass",
    "panel-init-failed": "final-summary:failed-judge-panel",
    "tally-error": "step3b-bypass",
    "degraded-empty-collector": "step3b-bypass",
}


class _Step3NormalizeAbort(Exception):
    pass


def _step3_bgjob_result_env(tmpdir: Path) -> Path:
    return tmpdir / "bgjob" / "design-step3-review.result.env"


def _step3_legacy_result_env(tmpdir: Path) -> Path:
    return tmpdir / ".step3-review-result.env"


def _step3_selected_result_env(tmpdir: Path) -> tuple[Path, str]:
    bgjob_result_env = _step3_bgjob_result_env(tmpdir)
    if bgjob_result_env.is_file() and not bgjob_result_env.is_symlink():
        return bgjob_result_env, "ok"
    legacy_result_env = _step3_legacy_result_env(tmpdir)
    if legacy_result_env.is_file() and not legacy_result_env.is_symlink():
        return legacy_result_env, "ok"
    return bgjob_result_env, "missing"


def _step3_normalize_warn_stderr(message: str) -> None:
    print(message, file=sys.stderr)


def _step3_read_result_env_quiet(argv: Sequence[str]) -> tuple[int, Path | None, bool]:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--input", dest="input_path")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--fallback-input", dest="fallback_input", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--allow", dest="allow", action="append", default=[])  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--output", dest="output_path")  # pyright: ignore[reportUnusedCallResult]
    try:
        ns, _extra = parser.parse_known_args(list(argv))
    except SystemExit:
        return 1, None, False
    primary = Path(ns.input_path or "")
    fallback = Path(ns.fallback_input) if ns.fallback_input else None
    primary_kind = _classify_input(primary)
    primary_regular = primary_kind == "regular"
    selected: Path | None = None
    if primary_regular:
        selected = primary
    elif fallback is not None and fallback.is_file() and not fallback.is_symlink():
        selected = fallback
    with contextlib.redirect_stdout(io.StringIO()):
        try:
            rc = int(read_result_env_main(list(argv)))
        except SystemExit as exc:
            rc = int(exc.code) if isinstance(exc.code, int) else 1
    if rc == 0 and primary_regular and selected == primary and fallback is not None:
        try:
            primary_pairs = phase_driver_read_result_env(path=primary, allow_keys=ns.allow)
        except OSError:
            primary_pairs = []
        if not primary_pairs and fallback.is_file() and not fallback.is_symlink():
            selected = fallback
    if rc == 0:
        return 0, selected, primary_regular
    return rc, None, primary_regular


def _step3_replay_warn_error_safe(path: Path | None) -> None:
    if path is None or path.is_symlink() or not path.is_file():
        return
    try:
        _replay_warn_error(path)
    except OSError:
        return


def _step3_overlay_stdout_env(
    *,
    values: dict[str, str],
    stdout_file: Path,
    primary_regular: bool,
    selected_source: Path | None = None,
) -> None:
    if stdout_file.is_symlink() or not stdout_file.is_file():
        return
    allow = set(STEP3_NORMALIZE_ALLOW_KEYS)
    overlay_warn = primary_regular and selected_source != stdout_file
    try:
        lines = stdout_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in allow and value:
            values[key] = value
        elif key == "WARN" and overlay_warn:
            print(line)


def _step3_normalize_load_env(*, design_tmpdir: Path, stdout_file: Path) -> dict[str, str]:
    result_env = _step3_bgjob_result_env(design_tmpdir)
    legacy_result_env = _step3_legacy_result_env(design_tmpdir)
    values: dict[str, str] = {}
    safe_path: Path | None = None
    selected_source: Path | None = None
    primary_regular = _classify_input(result_env) == "regular"
    try:
        fd, safe_name = tempfile.mkstemp(prefix="larch-step3-review-env.", dir=os.environ.get("TMPDIR") or None)
        os.close(fd)
        safe_path = Path(safe_name)
    except OSError:
        _step3_normalize_warn_stderr(
            "**⚠ Step 3: could not allocate safe step3 review result env; aborting plan review**"
        )
        raise _Step3NormalizeAbort from None
    try:
        argv = ["--input", str(result_env), "--fallback-input", str(legacy_result_env)]
        for key in STEP3_NORMALIZE_ALLOW_KEYS:
            argv.extend(["--allow", key])
        argv.extend(["--output", str(safe_path)])
        rc, selected_source, primary_regular = _step3_read_result_env_quiet(argv)
        if rc == 0:
            values = load_bash_quoted_env(path=safe_path, allow_keys=STEP3_NORMALIZE_ALLOW_KEYS)
            if not values and stdout_file.is_file() and not stdout_file.is_symlink():
                selected_source = stdout_file
        else:
            _step3_normalize_warn_stderr(
                "**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**"
            )
            selected_source = stdout_file if stdout_file.is_file() and not stdout_file.is_symlink() else None
            primary_regular = _classify_input(result_env) == "regular"
    except OSError:
        _step3_normalize_warn_stderr(
            "**⚠ Step 3: could not read step3 review result env; recovering from plan-review stdout when possible**"
        )
        selected_source = stdout_file if stdout_file.is_file() and not stdout_file.is_symlink() else None
        primary_regular = _classify_input(result_env) == "regular"
    finally:
        with contextlib.suppress(FileNotFoundError):
            safe_path.unlink()
    _step3_replay_warn_error_safe(selected_source)
    selected_result_regular = selected_source is not None and selected_source != stdout_file
    _step3_overlay_stdout_env(
        values=values,
        stdout_file=stdout_file,
        primary_regular=primary_regular or selected_result_regular,
        selected_source=selected_source,
    )
    return values


def _step3_normalize_read_result_env(tmpdir: Path) -> int:
    result_env, status = _step3_selected_result_env(tmpdir)
    values = dict.fromkeys(_STEP3_READ_RESULT_ENV_KEYS, "")
    if status == "ok":
        try:
            for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
                if "=" not in line:
                    continue
                key, value = line.split("=", 1)
                if key in values:
                    values[key] = value
        except OSError:
            status = "missing"
            values = dict.fromkeys(_STEP3_READ_RESULT_ENV_KEYS, "")
    if not values.get("NEXT_ACTION"):
        values["NEXT_ACTION"] = _step3_next_action(
            status=values.get("STEP3_REVIEW_LOOP_STATUS", ""),
            loop_status=values.get("LOOP_STATUS", ""),
        )
    _emit_kv(key="READ_RESULT_ENV_STATUS", value=status)
    for key in _STEP3_READ_RESULT_ENV_KEYS:
        _emit_kv(key=key, value=values[key])
    return 0


def _step3_back_map_loop_status(loop_status: str) -> str:
    return {
        "complete": "complete",
        "cap-reached": "cap-hit",
        "main-agent-vote-required": "main-agent-vote-required",
        "main-agent-apply-required": "main-agent-apply-required",
        "per-round-approval-required": "per-round-approval-required",
        "postplan-operator-required": "postplan-operator-required",
        "postplan-failed": "postplan-failed",
        "panel-failed": "panel-failed",
        "panel-init-failed": "panel-init-failed",
        "tally-error": "tally-error",
        "degraded-empty-collector": "degraded-empty-collector",
    }.get(loop_status, "")


def _step3_next_action(status: str, *, loop_status: str = "", tally_status: str = "") -> str:
    if loop_status == "zero-findings-degraded-panel":
        return "step3b"
    if tally_status == "tally-error" and (status == "complete" or loop_status == "complete"):
        return "step3b-bypass"
    if status:
        return _STEP3_NEXT_ACTION_BY_STATUS.get(status, "")
    return ""


def _step3_persist_next_action(tmpdir: Path, *, action: str) -> None:
    if not action:
        return
    result_env = tmpdir / ".step3-review-result.env"
    if result_env.is_symlink() or not result_env.is_file():
        return
    try:
        lines = result_env.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    preserved = [line for line in lines if not line.startswith("NEXT_ACTION=")]
    _write_atomic(path=result_env, content="NEXT_ACTION=" + action + "\n" + "\n".join(preserved) + ("\n" if preserved else ""))


def _step3_set_persist_next_action(tmpdir: Path, *, values: dict[str, str]) -> None:
    values["NEXT_ACTION"] = _step3_next_action(
        status=values.get("STEP3_REVIEW_LOOP_STATUS", ""),
        loop_status=values.get("LOOP_STATUS", ""),
        tally_status=values.get("TALLY_PLAN_REVIEW_STATUS", ""),
    )
    _step3_persist_next_action(tmpdir=tmpdir, action=values["NEXT_ACTION"])


def _step3_emit_normalize_envelope_with_next_action(tmpdir: Path, *, values: dict[str, str]) -> None:
    _step3_set_persist_next_action(tmpdir=tmpdir, values=values)
    _step3_emit_normalize_envelope(values)


def _step3_next_action_rows(*, action: str) -> list[tuple[str, str]]:
    return [("NEXT_ACTION", action)] if action else []


def _step3_emit_next_action(status: str, *, loop_status: str = "", tally_status: str = "") -> None:
    action = _step3_next_action(status=status, loop_status=loop_status, tally_status=tally_status)
    if action:
        _emit_kv(key="NEXT_ACTION", value=action)


def _step3_parse_rounds(values: dict[str, str]) -> int:
    raw = values.get("ROUNDS_COMPLETED") or values.get("REVIEW_ROUND_COUNT") or "0"
    return int(raw, 10) if re.fullmatch(r"[0-9]+", raw) else 0


def _step3_review_zero_round_coverage_missing(*, tmpdir: Path, rounds_completed: int) -> bool:
    if rounds_completed == 0:
        return True
    round_one = tmpdir / "plan-review" / "round-1"
    if not round_one.is_dir():
        return True
    try:
        return not any(child.is_file() and not child.is_symlink() for child in round_one.iterdir())
    except OSError:
        return True


def _step3_result_env_unusable(path: Path) -> bool:
    return path.is_symlink() or not path.is_file() or not os.access(path, os.R_OK)


def _step3_review_write_result_env(*, tmpdir: Path, status: str, reason: str, rounds: int) -> None:
    result_env = tmpdir / ".step3-review-result.env"
    try:
        if result_env.is_symlink() or result_env.is_file():
            result_env.unlink()
        elif result_env.exists():
            return
        phase_driver_write_result_env(
            path=result_env,
            kvs=[
                ("NEXT_ACTION", _step3_next_action(status=status, loop_status=status)),
                ("STEP3_REVIEW_LOOP_STATUS", status),
                ("LOOP_STATUS", status),
                ("REASON", reason),
                ("TALLY_PLAN_REVIEW_STATUS", status),
                ("STEP3_REVIEW_CAP_REACHED", "false"),
                ("STEP3_REVIEW_ROUND_NUM", ""),
                ("ROUND_NUM", ""),
                ("ROUNDS_COMPLETED", str(rounds)),
                ("REVIEW_ROUND_COUNT", str(rounds)),
            ],
        )
        step3_loop_write_terminal_step3(tmpdir)
    except (OSError, ValueError):
        return


def _step3_emit_normalize_envelope(values: dict[str, str]) -> None:
    for key in (
        "NEXT_ACTION",
        "STEP3_REVIEW_LOOP_STATUS",
        "LOOP_STATUS",
        "POSTPLAN_RC",
        "DEDUP_RC",
        "FINAL_ROUND_NUM",
        "TALLY_PLAN_REVIEW_STATUS",
        "SCOPE_ANCHOR_FILE",
        "STEP3_REVIEW_ROUND_NUM",
        "ROUND_NUM",
        "REVIEW_ROUND_COUNT",
        "ROUNDS_COMPLETED",
        "ACCEPTED_COUNT",
        "IMPORTANT_ACCEPTED_COUNT",
        "STEP3_REVIEW_CAP_REACHED",
        "AGGREGATOR_STATUS",
        "VOTING_TALLY_FILE",
        "DEGRADED_PANEL",
        "DEGRADED_PANEL_WARNING",
        "INVALID_SLOT_PANEL_WARNING",
        "PLAN_REVIEW_CONTINUE_REASON",
        "REASON",
    ):
        value = values.get(key, "")
        if value:
            _emit_kv(key=key, value=value)


def _step3_record_report_evidence_quiet(*, status: str, tmpdir: Path) -> int:
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        try:
            return int(step3_record_report_evidence(status=status, design_tmpdir=tmpdir))
        except SystemExit as exc:
            return int(exc.code) if isinstance(exc.code, int) else 1


def normalize_step3_status_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review normalize-status")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--stdout-file", default="")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--loop-rc", default="0")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--read-result-env", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv or []))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    if ns.read_result_env:
        return _step3_normalize_read_result_env(tmpdir)
    stdout_file = Path(ns.stdout_file)
    try:
        values = _step3_normalize_load_env(design_tmpdir=tmpdir, stdout_file=stdout_file)
    except _Step3NormalizeAbort:
        return 1
    if ns.loop_rc == "2":
        _step3_normalize_warn_stderr("**⚠ Step 3: plan-review run configuration error (exit 2); aborting plan review**")
        return 1

    step3_status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    loop_status = values.get("LOOP_STATUS", "")
    if not step3_status:
        step3_status = _step3_back_map_loop_status(loop_status)
        if step3_status:
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
        if not step3_status and loop_status != "zero-findings-degraded-panel":
            _step3_normalize_warn_stderr("**⚠ Step 3: result env missing or empty after loop exit; treating as panel-failed**")
            step3_status = "panel-failed"
            loop_status = "panel-failed"
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
            values["LOOP_STATUS"] = loop_status
    if step3_status:
        if step3_status not in _STEP3_STATUS_VALUES:
            _step3_normalize_warn_stderr("**⚠ Step 3: missing or invalid STEP3_REVIEW_LOOP_STATUS after plan-review run; treating plan review as panel-failed**")
            step3_status = "panel-failed"
            values["STEP3_REVIEW_LOOP_STATUS"] = step3_status
        loop_status = step3_loop_status_to_loop_status(status=step3_status, fallback=values.get("LOOP_STATUS", "complete"))
        values["LOOP_STATUS"] = loop_status
    elif not loop_status or loop_status not in _STEP3_LOOP_STATUS_VALUES:
        _step3_normalize_warn_stderr("**⚠ Step 3: missing or invalid LOOP_STATUS after plan-review run; treating plan review as panel-failed**")
        loop_status = "panel-failed"
        values["LOOP_STATUS"] = loop_status

    rounds_completed = _step3_parse_rounds(values)
    orphan_timeout = values.get("REASON") == "orphan-timeout"
    if (
        values.get("STEP3_REVIEW_LOOP_STATUS") == "panel-failed"
        and not orphan_timeout
        and _step3_review_zero_round_coverage_missing(tmpdir=tmpdir, rounds_completed=rounds_completed)
    ):
        _step3_normalize_warn_stderr("**⚠ Step 3: panel failed before any reviewer round launched; treating as panel-init-failed**")
        values["STEP3_REVIEW_LOOP_STATUS"] = "panel-init-failed"
        values["LOOP_STATUS"] = "panel-init-failed"
        values["TALLY_PLAN_REVIEW_STATUS"] = "panel-init-failed"
        values["ROUNDS_COMPLETED"] = "0"
        values["REVIEW_ROUND_COUNT"] = "0"
        values["REASON"] = "panel-failed-zero-coverage"
        rounds_completed = 0
        _step3_review_write_result_env(tmpdir=tmpdir, status="panel-init-failed", reason="panel-failed-zero-coverage", rounds=0)

    status_for_synthesis = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    result_env = tmpdir / ".step3-review-result.env"
    if status_for_synthesis in _STEP3_SYNTHESIS_STATUSES and _step3_result_env_unusable(result_env):
        _step3_normalize_warn_stderr(
            f"**⚠ Step 3: {status_for_synthesis} without a persisted result env; synthesizing terminal result env so the Step 3 completion sentinel is written**"
        )
        _step3_review_write_result_env(tmpdir=tmpdir, status=status_for_synthesis, reason=values.get("REASON", "result-env-missing-after-loop"), rounds=rounds_completed)

    # #5418 Fix A: write step-3-terminal before emitting KV output so that the
    # harness probe triggered by the <task-notification> finds the sentinel
    # present. Write only the sentinel (not the sidecar) so the wrapper EXIT
    # trap's step-3 minting gate remains intact. Guard: skip interactive
    # mid-loop statuses (mav/gate-b) that are not terminal.
    _step3_normalize_terminal_status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    if _step3_normalize_terminal_status and _step3_normalize_terminal_status not in _STEP3_INTERACTIVE_STATUSES:
        _step3_normalize_write_terminal_sentinel(tmpdir)
        if _step3_normalize_terminal_status in _STEP3_COMPLETED_SENTINEL_STATUSES:
            step3_wrapper_write_completed_step3_only(tmpdir)
    _step3_emit_normalize_envelope_with_next_action(tmpdir=tmpdir, values=values)

    status = values.get("STEP3_REVIEW_LOOP_STATUS", "")
    if status in _STEP3_EVIDENCE_STATUSES and _step3_record_report_evidence_quiet(status=status, tmpdir=tmpdir) != 0:
        _step3_normalize_warn_stderr(f"**⚠ Step 3: failed to record escalation evidence for {status}**")
    if status == "postplan-failed":
        print(_STEP3_SUMMARY_FAILED_POSTPLAN)
        return 1
    if status == "panel-init-failed":
        print(_STEP3_SUMMARY_FAILED_JUDGE_PANEL)
        return 1
    return 0


def step3_stage_postplan_failed(*, design_tmpdir: str | Path, postplan_rc: str = "unknown") -> int:
    tmpdir = Path(design_tmpdir)
    sentinel = tmpdir / ".step3-postplan-terminal-state.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    stdout = tmpdir / "step3-stage-terminal-state.stdout.log"
    stderr = tmpdir / "step3-stage-terminal-state.stderr.log"
    rc = capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout,
        stderr,
        [
            "--design-tmpdir",
            str(tmpdir),
            "--outcome",
            "failed-postplan",
            "--step",
            "postplan",
            "--phase",
            "postplan",
            "--site",
            "step3-review",
            "--trigger",
            "postplan-failed",
            "--bail-reason",
            "postplan-failed",
            "--exit-code",
            postplan_rc,
            "--source-script",
            "design-step3-review",
            "--summary-outcome",
            "failed-postplan",
        ],
    )
    if rc == 0:
        sentinel.touch()
        return 0
    logging_util.emit_kv(key="WARN", value="Step 3: failed to stage failed-postplan terminal state")
    return 1


def stage_panel_init_failed(*, design_tmpdir: str | Path, trigger: str = "panel-init-failed") -> int:
    tmpdir = Path(design_tmpdir)
    sentinel = tmpdir / ".step3-panel-init-terminal-state.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    stdout = tmpdir / "step3-panel-init-terminal-state.stdout.log"
    stderr = tmpdir / "step3-panel-init-terminal-state.stderr.log"
    rc = capture_contract_stream_to_paths(
        stage_terminal_state_core,
        stdout,
        stderr,
        [
            "--design-tmpdir",
            str(tmpdir),
            "--outcome",
            "failed-judge-panel",
            "--step",
            "step3",
            "--phase",
            "validation",
            "--site",
            "step3-review",
            "--trigger",
            trigger,
            "--bail-reason",
            trigger,
            "--exit-code",
            "1",
            "--source-script",
            "design-step3-review",
            "--summary-outcome",
            "failed-judge-panel",
        ],
    )
    if rc == 0:
        sentinel.touch()
        return 0
    logging_util.emit_kv(key="WARN", value="Step 3: failed to stage panel-init-failed terminal state")
    return 1


def step3_record_report_evidence(
    *,
    status: str,
    design_tmpdir: str | Path | None = None,
    cli_surface: bool = False,
) -> int:
    if cli_surface and design_tmpdir is None:
        print("plan-review run: --design-tmpdir is required with --record-report-evidence", file=sys.stderr)
        return 2
    tmpdir_raw = str(design_tmpdir or os.environ.get("DESIGN_TMPDIR", ""))
    if not tmpdir_raw:
        return 0
    ok, message, tmpdir = _validate_tmpdir_arg(tmpdir_raw)
    if not ok:
        if cli_surface:
            print(f"plan-review run: {message}", file=sys.stderr)
        return 2
    phase = {
        "panel-failed": "validation",
        "panel-init-failed": "validation",
        "tally-error": "validation",
        "degraded-empty-collector": "validation",
    }.get(status)
    if phase is None:
        return 0
    sentinel = tmpdir / f".step3-report-{status}.recorded"
    if sentinel.exists() or sentinel.is_symlink():
        return 0
    helper_cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "stall-recovery"]
    stdout = tmpdir / f"step3-record-escalation-{status}.stdout.log"
    stderr = tmpdir / f"step3-record-escalation-{status}.stderr.log"
    try:
        with stdout.open("w", encoding="utf-8") as out, stderr.open("w", encoding="utf-8") as err:
            proc = subprocess.run(
                [
                    *helper_cmd,
                    "record-escalation",
                    "--profile",
                    "generic",
                    "--artifact-prefix",
                    "design-failure",
                    "--implement-tmpdir",
                    str(tmpdir),
                    "--site",
                    "step3-review",
                    "--trigger",
                    status,
                    "--step",
                    "step3",
                    "--phase",
                    phase,
                    "--dispatcher",
                    "design-step3-review",
                ],
                cwd=str(_REPO_ROOT),
                stdout=out,
                stderr=err,
                check=False,
            )
        if proc.returncode == 0:
            sentinel.touch()
            return 0
    except OSError:
        pass
    logging_util.emit_kv(key="WARN", value=f"Step 3: failed to record design escalation evidence for {status}")
    return 1


# pyright: reportPrivateUsage=false, reportUnusedFunction=false
