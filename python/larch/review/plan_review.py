"""Native entry points for /design Step 3 plan review.

Thin facade — implementation is split across sibling modules:
  plan_review_common   — constants, data classes, I/O helpers, _run_command
  plan_review_gate_b   — Gate B severity classification and display
  plan_review_normalize — Step 3 result-env normalization and escalation recording
  plan_review_findings  — cross-round applied-finding ledger and rejected-findings emit
  plan_review_loop      — envelope persistence, plan emit/preview, state, timing, continuation
"""

from __future__ import annotations

import argparse
import contextlib
import io
import os
import re
import shutil
import subprocess
import sys
import tempfile  # noqa: F401  # pylint: disable=unused-import
import time
from collections.abc import Callable, Sequence
from pathlib import Path

from larch.core import logging_util
from larch.core import config
from larch.design.design_lifecycle import (
    json_get_bool_main as design_json_get_bool_main,
    phase_driver_read_result_env,
    phase_driver_write_result_env,
)
from larch.git.repo_roots import consumer_repo_root
from larch.review import plan_review_round
from larch.review.plan_review_common import (
    POSTPLAN_RC_OPERATOR,
    POSTPLAN_RC_PAUSE,
    POSTPLAN_RC_PLAN_SIZE_WARN,
    _REPO_ROOT,
    _STEP3_ROUND_CARRY_KEYS,
    _count_accepted,
    _emit_kv,
    _merge_step3_round_carry_warnings,
    _parse_kv_text,
    _plugin_root,
    _positive_int,
    _read_count,
    _read_kv_file,
    _require_tmpdir,
    _run_command,
    _step3_round_carry_values,
    _validate_tmpdir_arg,
    _write_atomic,
    _write_count,
    effective_authorized_cap,
)
from larch.review.plan_review_findings import _already_addressed_keys_in_rejected  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import _finding_dedup_key  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import _read_already_addressed_finding_keys  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import _record_already_addressed_finding_keys  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import REJECTED_FINDINGS_REPORT_ANNOTATION  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import REJECTED_FINDINGS_REPORT_HEADING  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_findings import emit_rejected_findings
from larch.review.plan_review_loop import (
    _read_bool_param,
    _read_phase,
    emit_design_plan_preview,
    emit_plan,
    finalize_plan,
    gate_b_counts,
    gate_b_dedup_plan,
    gate_b_finding_line,
    persist_design_round_start_s,
    persist_retally_step3_env,
    plan_review_continuation,
    record_plan_review_round_timing,
    _record_gate_b_apply_timing_from_round_window,
    _record_design_round_timing_from_start_file,
    run_plan_review_round,
    step3_loop_emit_envelope,
    step3_loop_persist_envelope,
    step3_state,
    tally_plan_review,
)
from larch.review.plan_review_normalize import _step3_next_action  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_normalize import _step3_persist_next_action  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_normalize import _step3_read_result_env_quiet  # noqa: F401  # pylint: disable=unused-import
from larch.review.plan_review_normalize import (
    normalize_step3_status_main,
    stage_panel_init_failed,
    step3_loop_write_completed_step3,
    step3_loop_write_terminal_step3,
    step3_record_report_evidence,
    step3_wrapper_write_completed_step3_only,
    _write_phase,
)

# _run_command is imported from plan_review_common above.
# Tests can patch plan_review._run_command to intercept all facade subprocess calls.


def _exec_pause_save(tmpdir: Path) -> int:
    issue = os.environ.get("ISSUE_NUMBER", "")
    cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "pause-save", "--design-tmpdir", str(tmpdir)]
    if issue:
        cmd.extend(["--issue", issue])
    override = os.environ.get("RUN_STEP3_DESIGN_PAUSE_SAVE_SH", "")
    if override:
        cmd = [override, "--design-tmpdir", str(tmpdir)]
        if issue:
            cmd.extend(["--issue", issue])
    return _run_command(argv=cmd, capture=False).returncode


def _run_post_apply(*, tmpdir: Path, round_num: int, values: dict[str, str]) -> int:
    override = os.environ.get("RUN_STEP3_POSTPLAN_EMIT_SH", "")
    if override:
        base = [override]
    else:
        base = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "postplan-emit"]
    proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--with-plan-size"], cwd=consumer_repo_root())
    rc = proc.returncode
    if rc == 0:
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    if rc == POSTPLAN_RC_PAUSE:
        return _exec_pause_save(tmpdir)
    if rc == POSTPLAN_RC_PLAN_SIZE_WARN:
        logging_util.emit_kv(key="WARN", value=f"plan-size trigger (postplan rc=12) in continuation (round {round_num}): proceeding as warning-only")
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
        return 0
    values["POSTPLAN_RC"] = str(rc)
    if rc in {10, 13}:
        return POSTPLAN_RC_OPERATOR
    return 33


def _run_continuation(tmpdir: Path, *, approve_requested: bool) -> dict[str, str]:
    override = os.environ.get("RUN_STEP3_CONTINUATION_SH", "")
    if override:
        cmd = [override]
    else:
        cmd = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-review", "continuation"]
    env = os.environ.copy()
    env["DESIGN_TMPDIR"] = str(tmpdir)
    _ = env.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
    proc = _run_command(argv=[*cmd, "--design-tmpdir", str(tmpdir), "--approve-requested", "true" if approve_requested else "false"], env=env)
    if proc.returncode != 0:
        return {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "continuation-failed"}
    out = _parse_kv_text(proc.stdout)
    if "PLAN_REVIEW_CONTINUE" not in out:
        return {"PLAN_REVIEW_CONTINUE": "false", "PLAN_REVIEW_CONTINUE_REASON": "continuation-malformed"}
    return out


def _round_args(*, tmpdir: Path, round_num: int) -> list[str]:
    return ["--design-tmpdir", str(tmpdir), "--round-num", str(round_num), "--prune-round-num", str(round_num)]


_ROUND_DIR_PRESERVE = frozenset({"round-start-s"})


def _is_pre_collection_terminal(values: dict[str, str]) -> bool:
    loop_status = values.get("LOOP_STATUS", "")
    agg = values.get("AGGREGATOR_STATUS", "")
    if loop_status == "zero-findings-degraded-panel":
        return True
    return loop_status == "panel-failed" and agg in {"skipped", "skipped-pruned-empty"}


def _clean_round_dir(*, tmpdir: Path, round_num: int) -> None:
    round_dir = tmpdir / "plan-review" / f"round-{round_num}"
    if not round_dir.is_dir() or round_dir.is_symlink():
        return
    status_link = round_dir / "reviewer-status.tsv"
    if status_link.is_symlink():
        with contextlib.suppress(OSError):
            status_link.unlink()
    for child in round_dir.iterdir():
        if child.name in _ROUND_DIR_PRESERVE:
            continue
        if child.is_file() and not child.is_symlink():
            with contextlib.suppress(OSError):
                child.unlink()


def _snapshot_plan(*, tmpdir: Path, round_num: int) -> Path:
    snapshot = tmpdir / f"plan-pre-apply-round-{round_num}.txt"
    if not snapshot.exists():
        _ = shutil.copyfile(tmpdir / "plan.txt", snapshot)
    return snapshot


def _run_dedup(*, tmpdir: Path, round_num: int, values: dict[str, str]) -> int:
    snapshot = _snapshot_plan(tmpdir=tmpdir, round_num=round_num)
    override = os.environ.get("RUN_STEP3_DEDUP_PLAN_SH", "")
    if override:
        base = [override]
    else:
        base = [sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-review", "gate-b-dedup"]
    proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--snapshot-trailers"])
    rc = proc.returncode
    if rc == 0:
        proc = _run_command(argv=[*base, "--design-tmpdir", str(tmpdir), "--dedup"])
        rc = proc.returncode
    if rc != 0:
        values["DEDUP_RC"] = str(rc)
        if snapshot.is_file():
            _ = shutil.copyfile(snapshot, tmpdir / "plan.txt")
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
        return 22
    clear = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "design", "dialectic-clear-stale", "--design-tmpdir", str(tmpdir), "--reason", "plan-rewrite"])
    if clear.returncode != 0:
        print("**⚠ plan-review: dialectic-clear-stale failed after dedup; stale clarifier artifacts may linger (Gate C fingerprint binding still gates debate).**", file=sys.stderr)
    _ = (tmpdir / f".gate-b-postapply-ready-{round_num}").touch()
    with contextlib.suppress(FileNotFoundError):
        (tmpdir / f".gate-b-per-round-approval-round-{round_num}.env").unlink()
    return 0


def _write_design_round_meta(*, tmpdir: Path, round_num: int) -> None:
    """Persist ``round-meta.json`` for a completed plan-review round."""
    round_dir = str(tmpdir / "plan-review" / f"round-{round_num}")
    round_meta_override = os.environ.get("WRITE_DESIGN_ROUND_META_SH")
    if round_meta_override:
        if Path(round_meta_override).exists() and os.access(round_meta_override, os.X_OK):
            _ = _run_command(argv=[round_meta_override, "--round-dir", round_dir])
    else:
        _ = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "progress", "write-design-round-meta", "--round-dir", round_dir])
    end_s = int(time.time())
    if (tmpdir / f".gate-b-postapply-ready-{round_num}").is_file():
        _record_gate_b_apply_timing_from_round_window(tmpdir=tmpdir, round_num=round_num, end_s=end_s)
    _record_design_round_timing_from_start_file(tmpdir=tmpdir, round_num=round_num, end_s=end_s)


def _gate_b_apply_required_status(*, tmpdir: Path, round_num: int, approve_requested: bool) -> str:
    approval_env = tmpdir / f".gate-b-per-round-approval-round-{round_num}.env"
    if approve_requested and not approval_env.is_file():
        return "per-round-approval-required"
    return "main-agent-apply-required"


def _resume_gate_b_apply(
    *,
    tmpdir: Path,
    round_num: int,
    approve_requested: bool,
    values: dict[str, str],
) -> bool:
    postapply_ready = tmpdir / f".gate-b-postapply-ready-{round_num}"
    if postapply_ready.is_file():
        _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-post-apply")
        return True
    status = _gate_b_apply_required_status(tmpdir=tmpdir, round_num=round_num, approve_requested=approve_requested)
    step3_loop_emit_envelope(tmpdir=tmpdir, status=status, round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
    return False


def _run_round_subprocess(*, tmpdir: Path, argv: Sequence[str]) -> tuple[int, str]:
    env = os.environ.copy()
    _ = env.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
    _ = env.setdefault("PLUGIN_ROOT", str(_plugin_root()))
    env["DESIGN_TMPDIR"] = str(tmpdir)
    proc = _run_command(argv=[str(Path(os.environ["RUN_STEP3_PLAN_REVIEW_LOOP_SH"])), *argv], env=env)
    return proc.returncode, proc.stdout + proc.stderr


def _run_round_body(*, tmpdir: Path, round_num: int) -> tuple[int, dict[str, str]]:
    start_s = int(time.time())
    _ = persist_design_round_start_s(design_tmpdir=tmpdir, round_num=round_num, start_s=start_s)
    _clean_round_dir(tmpdir=tmpdir, round_num=round_num)
    if os.environ.get("RUN_STEP3_PLAN_REVIEW_LOOP_SH"):
        body_rc, out_text = _run_round_subprocess(tmpdir=tmpdir, argv=_round_args(tmpdir=tmpdir, round_num=round_num))
        values_pre = _parse_kv_text(out_text)
        round_status = tmpdir / "plan-review" / f"round-{round_num}" / "reviewer-status.tsv"
        if not round_status.is_file() or round_status.is_symlink():
            if round_status.is_symlink():
                with contextlib.suppress(OSError):
                    round_status.unlink()
            collect_override: str | None = None
            if _is_pre_collection_terminal(values_pre):
                collect_override = ""
                _ = (tmpdir / "collector-results.env").write_text("", encoding="utf-8")
            _ = plan_review_round.try_write_reviewer_status_tsv(
                design=tmpdir,
                round_num=round_num,
                collect_text=collect_override,
                header_fallback=True,
            )
        else:
            plan_review_round.sync_latest_reviewer_status(design=tmpdir, round_status=round_status)
            _ = plan_review_round.materialize_stable_reviewer_status_table(design=tmpdir, round_num=round_num)
    else:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            body_rc = run_plan_review_round(_round_args(tmpdir=tmpdir, round_num=round_num))
        out_text = buf.getvalue()
    print(out_text, end="")
    values = _parse_kv_text(out_text)
    result_env = _read_kv_file(path=tmpdir / ".step3-review-result.env")
    if not values.get("REASON") and result_env.get("REASON"):
        values["REASON"] = result_env["REASON"]
    loop_status = values.get("LOOP_STATUS", "panel-failed" if body_rc else "complete")
    if body_rc != 0 and loop_status not in {"tally-error", "degraded-empty-collector", "panel-failed"}:
        tally_status = values.get("TALLY_PLAN_REVIEW_STATUS", "")
        loop_status = "tally-error" if tally_status == "tally-error" else "panel-failed"
    if values.get("STEP3_REVIEW_LOOP_STATUS"):
        loop_status = values.get("LOOP_STATUS", loop_status)
    values["LOOP_STATUS"] = loop_status
    _ = plan_review_round.materialize_stable_reviewer_status_table(design=tmpdir, round_num=round_num)
    return body_rc, values


def _step3_emit_cap_reached(*, review_count: int) -> None:
    _emit_kv(key="NEXT_ACTION", value="step3b-bypass")
    _emit_kv(key="LOOP_STATUS", value="cap-reached")
    _emit_kv(key="TALLY_PLAN_REVIEW_STATUS", value="skipped-cap-reached")
    _emit_kv(key="INFO", value=f"cap reached; skipping review round {review_count + 1}")


def _apply_new_process_group(parser: argparse.ArgumentParser) -> None:
    if not hasattr(os, "setsid"):
        parser.exit(2, "cli.py plan-review run: --new-process-group failed: os.setsid is unavailable\n")
    try:
        os.setsid()
    except OSError as exc:
        parser.exit(2, f"cli.py plan-review run: --new-process-group failed: {exc}\n")


def _parse_orphan_timeout(parser: argparse.ArgumentParser, value: str) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parser.exit(2, "cli.py plan-review run: --orphan-timeout-s must be positive\n")
    if parsed <= 0:
        parser.exit(2, "cli.py plan-review run: --orphan-timeout-s must be positive\n")
    return parsed


def _step3_orphan_timeout_elapsed(*, tmpdir: Path, timeout_s: float | None) -> bool:
    if timeout_s is None:
        return False
    if (tmpdir / config.DESIGN_STEP3_REATTACH_ACTIVE_FILE).is_file():
        return False
    marker = tmpdir / config.DESIGN_STEP3_WRAPPER_DETACHED_FILE
    if marker.is_symlink() or not marker.is_file():
        return False
    try:
        age_s = time.time() - marker.stat().st_mtime
    except OSError:
        return False
    return age_s >= timeout_s


def _emit_step3_orphan_timeout(*, tmpdir: Path, round_num: int) -> int:
    values = {"REASON": "orphan-timeout", "LOOP_STATUS": "panel-failed", "TALLY_PLAN_REVIEW_STATUS": "panel-failed"}
    step3_wrapper_write_completed_step3_only(tmpdir)
    step3_loop_emit_envelope(
        tmpdir=tmpdir,
        status="panel-failed",
        round_num=round_num,
        rounds_completed=max(0, round_num - 1),
        final_round=round_num,
        values=values,
    )
    return 0


def run_step3_review(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review run")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--mode", default="loop")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--starting-round", type=_positive_int)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--read-result-env", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--no-preview", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--new-process-group", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--orphan-timeout-s", default="")  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    orphan_timeout_s = _parse_orphan_timeout(parser, ns.orphan_timeout_s)
    if ns.read_result_env:
        result = tmpdir / ".step3-review-result.env"
        for key, value in phase_driver_read_result_env(path=result, allow_keys=[
            "NEXT_ACTION",
            "STEP3_REVIEW_LOOP_STATUS",
            "LOOP_STATUS",
            "TALLY_PLAN_REVIEW_STATUS",
            "ROUNDS_COMPLETED",
            "FINAL_ROUND_NUM",
            "ACCEPTED_COUNT",
            "DEGRADED_PANEL",
            "DEGRADED_PANEL_WARNING",
            "INVALID_SLOT_PANEL_WARNING",
            "REASON",
        ]):
            _emit_kv(key=key, value=value)
        return 0
    if ns.new_process_group:
        _apply_new_process_group(parser)
    approve_requested = _read_bool_param(tmpdir=tmpdir, key="approve_requested", default=False)
    round_num = ns.starting_round or (_read_count(tmpdir) + 1)
    degraded_exit = False
    degraded_values: dict[str, str] = {}

    while True:
        if _step3_orphan_timeout_elapsed(tmpdir=tmpdir, timeout_s=orphan_timeout_s):
            return _emit_step3_orphan_timeout(tmpdir=tmpdir, round_num=round_num)
        phase = _read_phase(tmpdir=tmpdir, round_num=round_num)
        if not phase:
            review_count = _read_count(tmpdir)
            authorized_cap = effective_authorized_cap(tmpdir)
            if review_count >= authorized_cap:
                values = {"TALLY_PLAN_REVIEW_STATUS": "skipped-cap-reached", "LOOP_STATUS": "cap-reached"}
                phase_driver_write_result_env(
                    path=tmpdir / ".step3-review-cap.env",
                    kvs=[("LOOP_STATUS", "cap-reached"), ("TALLY_PLAN_REVIEW_STATUS", "skipped-cap-reached")],
                )
                for stale in ("accepted-plan-findings.md", "voting-tally.md"):
                    with contextlib.suppress(OSError):
                        (tmpdir / stale).unlink()
                step3_loop_write_completed_step3(tmpdir)
                _step3_emit_cap_reached(review_count=review_count)
                step3_loop_persist_envelope(design_tmpdir=tmpdir, status="cap-hit", round_num=review_count + 1, rounds_completed=review_count, final_round=review_count + 1, values=values)
                return 0
            _write_count(tmpdir=tmpdir, count=round_num)
            _body_rc, values = _run_round_body(tmpdir=tmpdir, round_num=round_num)
            rounds_done = _read_count(tmpdir)
            loop_status = values["LOOP_STATUS"]
            if loop_status == "cap-reached":
                step3_loop_write_completed_step3(tmpdir)
                step3_loop_emit_envelope(tmpdir=tmpdir, status="cap-hit", round_num=round_num, rounds_completed=max(0, round_num - 1), final_round=round_num, values=values)
                return 0
            if loop_status in {"tally-error", "degraded-empty-collector", "panel-failed"}:
                if loop_status in {"tally-error", "degraded-empty-collector"}:
                    _write_count(tmpdir=tmpdir, count=max(0, round_num - 1))
                else:
                    _write_count(tmpdir=tmpdir, count=max(round_num, rounds_done))
                step3_wrapper_write_completed_step3_only(tmpdir)
                step3_loop_emit_envelope(tmpdir=tmpdir, status=loop_status, round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            if loop_status == "main-agent-vote-required":
                _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-vote-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            if loop_status in {"complete", "zero-findings-degraded-panel"}:
                values = _merge_step3_round_carry_warnings(values=values, carry=degraded_values)
                accepted = _count_accepted(tmpdir) or int(values.get("ACCEPTED_COUNT", "0") or "0")
                values["ACCEPTED_COUNT"] = str(accepted)
                for key in _STEP3_ROUND_CARRY_KEYS:
                    if values.get(key):
                        degraded_values[key] = values[key]
                if loop_status == "zero-findings-degraded-panel":
                    phase_driver_write_result_env(
                        path=tmpdir / ".step3-review-result.env",
                        kvs=[
                            ("NEXT_ACTION", "step3b"),
                            ("LOOP_STATUS", "zero-findings-degraded-panel"),
                            ("ROUNDS_COMPLETED", str(round_num)),
                            ("REVIEW_ROUND_COUNT", str(round_num)),
                            ("PANEL_PRUNED_EMPTY", values.get("PANEL_PRUNED_EMPTY", "true")),
                            ("TALLY_PLAN_REVIEW_STATUS", values.get("TALLY_PLAN_REVIEW_STATUS", "ok")),
                            ("ACCEPTED_COUNT", str(accepted)),
                            ("DEGRADED_PANEL", values.get("DEGRADED_PANEL", "0")),
                            ("DEGRADED_PANEL_WARNING", values.get("DEGRADED_PANEL_WARNING", "")),
                            ("INVALID_SLOT_PANEL_WARNING", values.get("INVALID_SLOT_PANEL_WARNING", "")),
                            ("REASON", values.get("REASON", "")),
                        ],
                    )
                    degraded_exit = True
                    degraded_values = dict(values)
                if accepted == 0:
                    _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
                    continue
                if approve_requested:
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                    step3_loop_emit_envelope(tmpdir=tmpdir, status="per-round-approval-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                    return 0
                _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-apply")
                step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-apply-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            _emit_kv(key="WARN", value=f"missing or invalid LOOP_STATUS={loop_status!r}; treating as panel-failed")
            step3_wrapper_write_completed_step3_only(tmpdir)
            step3_loop_emit_envelope(tmpdir=tmpdir, status="panel-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
            return 0

        if phase in {"awaiting-apply", "awaiting-revise"}:
            values = dict(degraded_values)
            if _resume_gate_b_apply(
                tmpdir=tmpdir,
                round_num=round_num,
                approve_requested=approve_requested,
                values=values,
            ):
                continue
            return 0

        if phase in {"awaiting-post-apply", "awaiting-postplan-operator"}:
            if phase == "awaiting-postplan-operator":
                sentinel = tmpdir / f".postplan-operator-continue-{round_num}"
                if sentinel.is_file():
                    with contextlib.suppress(FileNotFoundError):
                        sentinel.unlink()
                    _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-continuation")
                    continue
                step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-operator-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=_step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values))
                return 0
            postapply_ready = tmpdir / f".gate-b-postapply-ready-{round_num}"
            if not postapply_ready.is_file():
                values = _step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values)
                dedup_rc = _run_dedup(tmpdir=tmpdir, round_num=round_num, values=values)
                if dedup_rc != 0:
                    step3_loop_emit_envelope(tmpdir=tmpdir, status="main-agent-apply-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                    return 0
            values = _step3_round_carry_values(degraded_exit=degraded_exit, degraded_values=degraded_values)
            post_rc = _run_post_apply(tmpdir=tmpdir, round_num=round_num, values=values)
            if post_rc == 0:
                continue
            if post_rc == POSTPLAN_RC_OPERATOR:
                _write_phase(tmpdir=tmpdir, round_num=round_num, phase="awaiting-postplan-operator")
                step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-operator-required", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
                return 0
            step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=values)
            return 0

        if phase == "awaiting-continuation":
            if (tmpdir / f".gate-b-postapply-ready-{round_num}").is_file():
                _write_design_round_meta(tmpdir=tmpdir, round_num=round_num)
            _write_count(tmpdir=tmpdir, count=round_num)
            cont = _run_continuation(tmpdir=tmpdir, approve_requested=approve_requested)
            if cont.get("PLAN_REVIEW_CONTINUE") == "true":
                with contextlib.suppress(FileNotFoundError):
                    (tmpdir / ".step3-review-result.env").unlink()
                _ = _run_command(
                    argv=[
                        sys.executable,
                        str(_plugin_root() / "python" / "cli.py"),
                        "plan-review",
                        "step3-state",
                        "--design-tmpdir",
                        str(tmpdir),
                        "--auto-continuation-entry",
                    ]
                )
                with contextlib.suppress(FileNotFoundError):
                    (tmpdir / ".step3-entry-plan-printed").unlink()
                round_num += 1
                degraded_exit = False
                degraded_values = _step3_round_carry_values(degraded_exit=False, degraded_values=degraded_values)
                continue
            if degraded_exit:
                step3_loop_write_completed_step3(tmpdir)
                step3_loop_write_terminal_step3(tmpdir)
                _emit_kv(key="NEXT_ACTION", value="step3b")
                _emit_kv(key="LOOP_STATUS", value="zero-findings-degraded-panel")
                _emit_kv(key="ROUNDS_COMPLETED", value=round_num)
                _emit_kv(key="REVIEW_ROUND_COUNT", value=round_num)
                for key in (
                    "PANEL_PRUNED_EMPTY",
                    "TALLY_PLAN_REVIEW_STATUS",
                    "ACCEPTED_COUNT",
                    "DEGRADED_PANEL",
                    "DEGRADED_PANEL_WARNING",
                    "INVALID_SLOT_PANEL_WARNING",
                    "REASON",
                ):
                    if degraded_values.get(key):
                        _emit_kv(key=key, value=degraded_values[key])
                return 0
            complete_values = dict(degraded_values)
            complete_values.update({k: v for k, v in cont.items() if k in {"PLAN_REVIEW_CONTINUE_REASON", "ACCEPTED_COUNT", "DEGRADED_PANEL", "DEGRADED_PANEL_WARNING", "INVALID_SLOT_PANEL_WARNING"}})
            step3_loop_write_completed_step3(tmpdir)
            _write_atomic(
                path=tmpdir / ".step3-review-cap.env",
                content=f"STEP3_REVIEW_CAP_REACHED=false\nSTEP3_REVIEW_ROUND_NUM={round_num}\n",
            )
            step3_loop_emit_envelope(tmpdir=tmpdir, status="complete", round_num=round_num, rounds_completed=round_num, final_round=round_num, values=complete_values)
            if degraded_exit:
                _emit_kv(key="LOOP_STATUS", value="zero-findings-degraded-panel")
                _emit_kv(key="REVIEW_ROUND_COUNT", value=round_num)
            return 0

        step3_loop_emit_envelope(tmpdir=tmpdir, status="postplan-failed", round_num=round_num, rounds_completed=round_num, final_round=round_num, values={"REASON": f"invalid-phase:{phase or 'missing'}"})
        return 2


def run_step3_loop(argv: Sequence[str]) -> int:
    return run_step3_review(argv)


def prelaunch_failure(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review prelaunch-failure")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--reason", default="panel-init-failed")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    values = {"REASON": ns.reason, "LOOP_STATUS": "panel-init-failed"}
    _ = stage_panel_init_failed(design_tmpdir=tmpdir, trigger=ns.reason)
    step3_loop_emit_envelope(tmpdir=tmpdir, status="panel-init-failed", round_num=0, rounds_completed=0, final_round=0, values=values)
    return 0


def step35(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review step35")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    result = _read_kv_file(path=tmpdir / ".step3-review-result.env")
    loop_status = result.get("LOOP_STATUS", os.environ.get("LOOP_STATUS", ""))
    step3_status = result.get("STEP3_REVIEW_LOOP_STATUS", os.environ.get("STEP3_REVIEW_LOOP_STATUS", ""))
    if step3_status in {"main-agent-apply-required", "per-round-approval-required", "postplan-operator-required"} or (
        not step3_status and loop_status in {"complete", "zero-findings-degraded-panel", "main-agent-vote-required"}
    ):
        step3_wrapper_write_completed_step3_only(tmpdir)
    _emit_kv(key="APPROVE_REQUESTED", value="true" if _read_bool_param(tmpdir=tmpdir, key="approve_requested", default=False) else "false")
    return 0


def step35_settle(argv: Sequence[str]) -> int:
    script = _plugin_root() / "skills" / "design" / "scripts" / "design-step35-settle.sh"
    bash = shutil.which("bash") or "/bin/bash"
    proc = subprocess.run([bash, str(script), *argv], cwd=str(_REPO_ROOT), check=False)
    return proc.returncode


def _delegate_step3_script(*, script_name: str, argv: Sequence[str]) -> int:
    script = _plugin_root() / "skills" / "design" / "scripts" / script_name
    if not script.is_file():
        return 2
    bash = shutil.which("bash") or "/bin/bash"
    return subprocess.run([bash, str(script), *argv], cwd=str(_REPO_ROOT), check=False).returncode


def _json_get_bool_cli(argv: Sequence[str]) -> int:
    return design_json_get_bool_main(argv)


def round_artifact_included(name: str) -> bool:
    if name in {"round-summary.env", "findings-classification.tsv", "prune-decision.env", "prune-nit.env", "reviewer-status.tsv"}:
        return True
    if name.endswith(("-vote-output.txt", "-vote-output-first-pass.txt", ".failure-diag")):
        return os.environ.get("LARCH_FLUSH_DEBUG") == "1"
    return False


def round_revise_artifact_included(_name: str) -> bool:
    return False


def round_revise_artifact_excluded(name: str) -> bool:
    suffixes = (
        "-output.txt",
        "-output-candidate.patch",
        ".done",
        ".dirty-tree",
        ".meta",
        ".prompt",
        ".sidecar",
        ".sidecar.history",
        ".events.jsonl",
        ".events.history",
        ".untracked-baseline",
        ".diag",
        ".failure-diag",
        ".json",
        ".stderr",
        ".token-record",
        ".stderr-tail",
    )
    return name in {"revise.env", "prompt.txt"} or any(name.endswith(suffix) for suffix in suffixes)


def drift_baseline_write_once(*, design_tmpdir: str | Path, plan_lines: str, diff_lines: str) -> int:
    ok, _message, tmpdir = _validate_tmpdir_arg(design_tmpdir)
    if not ok:
        return 1
    if not re.fullmatch(r"[0-9]+", plan_lines) or not re.fullmatch(r"[0-9]+", diff_lines):
        return 1
    path = tmpdir / "drift-baseline.env"
    if path.is_file() and not path.is_symlink():
        return 0
    if path.is_symlink():
        path.unlink()
    try:
        _write_atomic(path=path, content=f"BASELINE_PLAN_LINES={plan_lines}\nBASELINE_DIFF_LINES={diff_lines}\n")
    except OSError:
        return 1
    return 0


def _artifact_cli(*, argv: Sequence[str], predicate: Callable[[str], bool]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review round-artifact-included")
    parser.add_argument("name", nargs="?")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--name", dest="name_opt")  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    name = ns.name_opt or ns.name
    if not name:
        parser.error("artifact name is required")
    return 0 if predicate(Path(name).name) else 1


def _drift_baseline_cli(argv: Sequence[str]) -> int:
    if not argv or argv[0] != "write-once":
        print("usage: cli.py plan-review drift-baseline write-once --design-tmpdir DIR --plan-lines N --diff-lines N", file=sys.stderr)
        return 2
    parser = argparse.ArgumentParser(prog="cli.py plan-review drift-baseline write-once")
    parser.add_argument("write_once")  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--plan-lines", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--diff-lines", required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(list(argv))
    return drift_baseline_write_once(design_tmpdir=ns.design_tmpdir, plan_lines=ns.plan_lines, diff_lines=ns.diff_lines)


def run_main(argv: list[str] | None = None) -> int:
    args = list(argv or [])
    if "--record-report-evidence" in args:
        idx = args.index("--record-report-evidence")
        try:
            status = args[idx + 1]
        except IndexError:
            print("plan-review run: --record-report-evidence requires a value", file=sys.stderr)
            return 2
        design_tmpdir: str | None = None
        if "--design-tmpdir" in args:
            didx = args.index("--design-tmpdir")
            if didx + 1 < len(args):
                design_tmpdir = args[didx + 1]
        return step3_record_report_evidence(status=status, design_tmpdir=design_tmpdir, cli_surface=True)
    return run_step3_review(args)


def step3_entry(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review step3-entry")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--reentry", action="store_true")  # pyright: ignore[reportUnusedCallResult]
    ns, _extra = parser.parse_known_args(list(argv))
    tmpdir = _require_tmpdir(parser=parser, design_tmpdir=ns.design_tmpdir)
    if ns.reentry:
        (tmpdir / ".step3-reentry").touch()
    with contextlib.suppress(FileNotFoundError):
        (tmpdir / ".pause-save-complete").unlink()
    anchor = tmpdir / "plan-review-scope-anchor.txt"
    stripped = tmpdir / ".plan-review-scope-stripped.txt"
    issue_body = tmpdir / "issue-body.txt"
    feature = tmpdir / "feature-description.txt"
    if issue_body.is_file() and issue_body.stat().st_size > 0:
        proc = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-block", "strip-body", "--file", str(issue_body), "--output", str(stripped)])
        if proc.returncode != 0:
            _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "strip-body-failure"])
            return 1
    elif feature.is_file() and feature.stat().st_size > 0:
        proc = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "plan-block", "strip-body", "--file", str(feature), "--output", str(stripped)])
        if proc.returncode != 0:
            _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "strip-body-failure"])
            return 1
    else:
        _write_atomic(path=stripped, content="")
    parts: list[str] = []
    if stripped.is_file():
        parts.append(stripped.read_text(encoding="utf-8", errors="replace"))
    outline = tmpdir / "design-outline.md"
    if outline.is_file() and (tmpdir / ".outline-approved").is_file():
        parts.append("\n\n## Approved direction (outline)\n\n" + outline.read_text(encoding="utf-8", errors="replace"))
    body = "".join(parts).strip()
    if not body:
        _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "scope-anchor-missing"])
        return 1
    redact = _run_command(argv=[sys.executable, str(_plugin_root() / "python" / "cli.py"), "redact", "secrets"], stdin_text=body)
    if redact.returncode != 0 or not redact.stdout.strip():
        _ = prelaunch_failure(["--design-tmpdir", str(tmpdir), "--reason", "scope-anchor-missing"])
        return 1
    _write_atomic(path=anchor, content=redact.stdout if redact.stdout.endswith("\n") else redact.stdout + "\n")
    _emit_kv(key="SCOPE_ANCHOR_FILE", value=str(anchor))
    return 0


# ---------------------------------------------------------------------------
# *_main entry points — wired by cli.py dispatch table
# ---------------------------------------------------------------------------

def tally_main(argv: list[str] | None = None) -> int:
    return tally_plan_review(argv or [])


def emit_main(argv: list[str] | None = None) -> int:
    return emit_plan(argv or [])


def finalize_main(argv: list[str] | None = None) -> int:
    return finalize_plan(argv or [])


def preview_main(argv: list[str] | None = None) -> int:
    return emit_design_plan_preview(argv or [])


def gate_b_counts_main(argv: list[str] | None = None) -> int:
    return gate_b_counts(argv or [])


def gate_b_finding_line_main(argv: list[str] | None = None) -> int:
    return gate_b_finding_line(argv or [])


def gate_b_dedup_main(argv: list[str] | None = None) -> int:
    return gate_b_dedup_plan(argv or [])


def persist_retally_env_main(argv: list[str] | None = None) -> int:
    return persist_retally_step3_env(argv or [])


def step3_state_main(argv: list[str] | None = None) -> int:
    return step3_state(argv or [])


def record_round_timing_main(argv: list[str] | None = None) -> int:
    return record_plan_review_round_timing(argv or [])


def persist_round_start_s_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review persist-round-start-s")
    parser.add_argument("--design-tmpdir", required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--round-num", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    parser.add_argument("--start-s", type=int, required=True)  # pyright: ignore[reportUnusedCallResult]
    ns = parser.parse_args(argv or [])
    return persist_design_round_start_s(design_tmpdir=ns.design_tmpdir, round_num=ns.round_num, start_s=ns.start_s)


def continuation_main(argv: list[str] | None = None) -> int:
    return plan_review_continuation(argv or [])


def prelaunch_failure_main(argv: list[str] | None = None) -> int:
    return prelaunch_failure(argv or [])


def step35_main(argv: list[str] | None = None) -> int:
    return step35(argv or [])


def step35_settle_main(argv: list[str] | None = None) -> int:
    return step35_settle(argv or [])


def json_get_bool_main(argv: list[str] | None = None) -> int:
    return _json_get_bool_cli(argv or [])


def step3_entry_main(argv: list[str] | None = None) -> int:
    return step3_entry(argv or [])


def step3_mav_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3-mav.sh", argv=argv or [])


def step3b_entry_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-entry.sh", argv=argv or [])


def step3b_sanitize_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-sanitize.sh", argv=argv or [])


def step3b_tail_main(argv: list[str] | None = None) -> int:
    return _delegate_step3_script(script_name="design-step3b-tail.sh", argv=argv or [])


def emit_rejected_main(argv: list[str] | None = None) -> int:
    return emit_rejected_findings(argv or [])


def normalize_status_main(argv: list[str] | None = None) -> int:
    return normalize_step3_status_main(argv or [])


def round_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_artifact_included)


def round_revise_artifact_included_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_revise_artifact_included)


def round_revise_artifact_excluded_main(argv: list[str] | None = None) -> int:
    return _artifact_cli(argv=argv or [], predicate=round_revise_artifact_excluded)


def drift_baseline_main(argv: list[str] | None = None) -> int:
    return _drift_baseline_cli(argv or [])


# pyright: reportPrivateUsage=false, reportUnusedImport=false
# pyright: reportUnusedFunction=false
