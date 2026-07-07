"""Review-and-fix Python driver for accepted findings and /implement Step 5."""
# pylint: disable=unused-import

# ruff: noqa: PLR2004
# pyright: reportUnusedCallResult=false, reportArgumentType=false

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, cast
from collections.abc import Generator

from larch.agents import agents
from larch.core import config
from larch.core import external_defaults
from larch.calibration import difficulty
from larch import io as larch_io
from larch.core import logging_util
from larch.core import proc
from larch.report import progress_report
from larch.core import redact
from larch.review import review_pipeline
from larch.review import review_tally
from larch.review import self_review_tally
from larch.report import run_logs
from larch.review import voting
from larch.review.review_types import ReviewCoreStatus, parse_findings, parse_findings_text, read_finding_text

# --- imports from split sibling modules ---

from larch.review._raf_util import (
    _PLUGIN_ROOT,
    _PY_CLI,
    _append_text,
    _capture_emit_to,
    _core_round_state,
    _count_findings,
    _count_matching_lines,
    _count_rejected_lines,
    _emit_kv,
    _env_get,
    _err,
    _git_head,
    _git_output,
    _git_status_porcelain,
    _git_status_porcelain_or_fail,
    _git_stdout,
    _non_negative_int,
    _parse_env_file,
    _parse_env_lines,
    _plugin_root,
    _positive_int,
    _prior_summary_counts,
    _read_text,
    _rehydrate_session_env,
    _resolve_run_id,
    _run,
    _session_get,
    _step5_repo_root,
    _temporary_env,
    _write_env,
    _write_text,
)
from larch.review.snapshot import (
    _collect_self_review_stage_paths,
    _structural_loc,
    _write_pre_coder_snapshot,
    _write_pre_self_review_snapshot,
    pre_coder_snapshot_dir,
)
from larch.review.coder_runner import (
    CoderResult,
    RoundCommitResult,
    _codex_available,
    _collect_review_fix_stage_paths,
    _compose_coder_prompt,
    _cursor_available,
    _post_dispatch_submodule_revert,
    _resolve_coder_timing_ledger,
    _run_coder_codex,
    _run_coder_cursor,
    apply_findings_with_coder,
)
from larch.review.batch_report import (
    _skip_ratio_threshold,
    observe_code_review_tally_flush,
    flush_review_batches,
    flush_round_log_after_coder,
    flush_scout_manifest,
    write_rejected_findings_aggregate,
    _process_skipped_findings,
)
from larch.review.round_runner import (
    ReviewCoreImpl,
    RoundResult,
    _dynamic_archetypes,
    _emit_round_kvs,
    _high_severity_count,
    _run_round,
    _surface_dropped_reviewer_warning,
    _surface_parse_failed_warning,
    _surface_under_quorum_warning,
    _timing_row_matches,
    review_core_capture,
)

# Keep these module-level constants for backward compatibility with any code
# that reads them via review_and_fix._PLUGIN_ROOT etc.
_FINDING_RE = re.compile(r"^### FINDING_[0-9]+:")
_SKIPPED_RE = re.compile(r"^SKIPPED:\s*(FINDING_\d+)")
_HIGH_RE = re.compile(
    r"(^### FINDING_[0-9]+:[^\n]*(\*\*Blocking\*\*|\*\*Important\*\*|\*\*Critical\*\*|\*\*High\*\*)"
    r"|\*\*[Bb]locking\*\*"
    r"|\*\*[Ii]mportant\*\*"
    r"|^- \*\*Concern\*\*:\s*\[[Bb]locking\](?:[\s,:;.\)]|$)"
    r"|^- \*\*Concern\*\*:\s*\[[Ii]mportant\](?:[\s,:;.\)]|$))"
)
_OOS_HEADING_RE = re.compile(r"^### FINDING_[0-9]+:.*\[(?:OUT_OF_SCOPE|OOS)\]")
_STEP5_REVIEW_RESULT_ENV = ".step5-review-result.env"


@dataclass(frozen=True)
class _Step5Envelope:
    status: str
    stall_tracking: bool
    stall_reason: str
    rounds_completed: int
    final_round: int
    final_irf: str
    coder_status: str
    files_hint: str
    effective_cap: int


# --- commit-fixes helpers (used by commit_fixes CLI entry point) ---

def _emit_commit_fixes_kvs(*, committed: bool, sha: str, error: str, outcome: Literal["ok", "noop", "failed"]) -> None:
    _emit_kv(key="COMMITTED", value=committed)
    _emit_kv(key="SHA", value=sha)
    _emit_kv(key="ERROR", value=error)
    _emit_kv(key="COMMIT_OUTCOME", value=outcome)


def _commit_fixes_result_error(result: proc.CommandResult) -> str:
    return (result.stderr or result.stdout).replace("\n", " ")[:500]


def _finish_stage_all_commit_success(sha: str) -> int:
    _status = _run(["git", "status", "--porcelain"])
    if _status.returncode != 0:
        _emit_commit_fixes_kvs(committed=True, sha=sha, error="git status probe failed", outcome="failed")
        return 1
    _emit_commit_fixes_kvs(committed=True, sha=sha, error="", outcome="ok")
    return 0


def _commit_fixes_stage_all(message: str) -> int:
    _status = _run(["git", "status", "--porcelain"])
    porcelain = _status.stdout
    probe_ok = _status.returncode == 0
    if not probe_ok:
        _emit_commit_fixes_kvs(committed=False, sha="", error="git status probe failed", outcome="failed")
        return 1
    if not porcelain.strip():
        _emit_commit_fixes_kvs(committed=False, sha="", error="", outcome="noop")
        return 0
    raw_implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not raw_implement_tmpdir:
        _emit_commit_fixes_kvs(committed=False, sha="", error="IMPLEMENT_TMPDIR required", outcome="failed")
        return 2
    implement_tmpdir = Path(raw_implement_tmpdir)
    paths = _collect_review_fix_stage_paths(implement_tmpdir)
    stage_file = implement_tmpdir / "review-fix-stage-paths.txt"
    _write_text(path=stage_file, text="\n".join(paths) + ("\n" if paths else ""))
    if not paths:
        # Dirty tree with no review-delta paths means the dirt is pre-existing and
        # unrelated to the review fix — benign noop, not a Tool Failure (issue #5715).
        _emit_commit_fixes_kvs(committed=False, sha="", error="", outcome="noop")
        return 0
    raw_project = os.environ.get("CLAUDE_PROJECT_DIR", "").strip()
    if raw_project:
        _rr = _run(["git", "-C", raw_project, "rev-parse", "--show-toplevel"])
        repo_root = _rr.stdout.strip() if _rr.returncode == 0 and _rr.stdout.strip() else ""
    else:
        _rr = _run(["git", "rev-parse", "--show-toplevel"])
        repo_root = _rr.stdout.strip() if _rr.returncode == 0 else ""
    result = _run([
        sys.executable,
        str(_PY_CLI),
        "git",
        "commit",
        "--only",
        "--pathspec-from-file",
        str(stage_file),
        "-m",
        message,
    ], cwd=Path(repo_root) if repo_root else None)
    if result.returncode != 0:
        _emit_commit_fixes_kvs(committed=False, sha="", error=_commit_fixes_result_error(result), outcome="failed")
        return result.returncode
    return _finish_stage_all_commit_success(_git_head())


# --- step5-specific helpers ---

def _step5_probe_prior_round_env(*, implement_tmpdir: Path, prior_round: int) -> bool:
    expected = implement_tmpdir / f"round-{prior_round}" / "review-and-fix.env"
    if expected.is_file():
        return True
    with contextlib.suppress(OSError):
        os.sync()
    return expected.is_file()


def _step5_write_terminal_sentinel(*, implement_tmpdir: Path) -> None:
    completed = implement_tmpdir / ".completed"
    completed.mkdir(parents=True, exist_ok=True)
    (completed / "step-5-terminal").touch()


@contextlib.contextmanager
def _stderr_sidecar(path: Path) -> Generator[None, None, None]:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        original = sys.stderr
        class _Tee:
            def write(self, data: str) -> int:
                original.write(data)
                handle.write(data)
                return len(data)

            def flush(self) -> None:
                original.flush()
                handle.flush()

        sys.stderr = _Tee()  # type: ignore[assignment]
        try:
            yield
        finally:
            sys.stderr = original


def _step5_post_round_gates(*,
    result: RoundResult,
    round_num: int,
    round_cap: int,
) -> tuple[str | None, str | None, bool]:
    """Return (terminal_status, stall_reason, should_continue_next_round)."""
    if result.status != "fix-applied":
        return None, None, False
    pre_head_file = pre_coder_snapshot_dir(result.round_dir) / "pre-coder-head.txt"
    post_head_file = result.round_dir / "post-coder-head.txt"
    structural = _structural_loc(pre_head_file=pre_head_file, post_head_file=post_head_file)
    high_n = _high_severity_count(result.accepted_file)
    fix_count = result.coder.input_count
    substantial = high_n >= 2 or structural >= 100 or fix_count >= 8
    skipped = result.skipped_finding_count
    skip_ratio = (skipped / fix_count) if fix_count > 0 else 0.0
    threshold = _skip_ratio_threshold()
    if skip_ratio >= threshold:
        if round_num < round_cap:
            return None, None, True
        return "stall", "bulk-skip-ratio-cap", False
    if substantial:
        if round_num < round_cap:
            return None, None, True
        return "cap-hit", "", False
    return "complete", "", False


def _stringify_step5_env_value(*, value: str | int | bool) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _step5_result_env_path() -> Path:
    raw_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not raw_tmpdir:
        raise OSError("IMPLEMENT_TMPDIR required for step 5 result env")
    tmpdir = Path(raw_tmpdir)
    if tmpdir.is_symlink():
        raise OSError(f"refusing symlink implement tmpdir for step 5 result env: {tmpdir}")
    if not tmpdir.is_dir():
        raise OSError(f"step 5 result env implement tmpdir is not a directory: {tmpdir}")
    return tmpdir / _STEP5_REVIEW_RESULT_ENV


def _step5_difficulty_rows() -> list[tuple[str, str | int | bool]]:
    rows: list[tuple[str, str | int | bool]] = []
    record = Path(os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")) / difficulty.DIFFICULTY_RECORD_BASENAME
    if not record.is_file():
        return rows
    try:
        data = json.loads(record.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return rows
    if not isinstance(data, dict):
        return rows
    record_data = cast("dict[str, object]", data)
    if record_data.get("panel_tier"):
        rows.append(("PANEL_TIER", str(record_data.get("panel_tier"))))
    if record_data.get("audit_upgrade") is not None:
        audit_upgrade = str(record_data.get("audit_upgrade")).lower() == "true" or record_data.get("audit_upgrade") is True
        rows.append(("AUDIT_UPGRADE", audit_upgrade))
    return rows


def _step5_envelope_rows(envelope: _Step5Envelope) -> list[tuple[str, str | int | bool]]:
    rows: list[tuple[str, str | int | bool]] = [
        ("STEP5_REVIEW_STATUS", envelope.status),
        ("STALL_TRACKING", envelope.stall_tracking),
        ("STALL_REASON", envelope.stall_reason),
        ("ROUNDS_COMPLETED", envelope.rounds_completed),
        ("FINAL_ROUND_NUM", envelope.final_round),
        ("FINAL_REVIEW_AND_FIX_STATUS", envelope.final_irf),
        ("CODER_STATUS", envelope.coder_status),
        ("FILES_CHANGED_HINT", envelope.files_hint),
        ("EFFECTIVE_ROUND_CAP", envelope.effective_cap),
    ]
    rows.extend(_step5_difficulty_rows())
    return rows


def _write_step5_result_env(rows: list[tuple[str, str | int | bool]]) -> None:
    result_env = _step5_result_env_path()
    safe_rows: list[tuple[str, str]] = []
    for key, value in rows:
        text = _stringify_step5_env_value(value=value)
        if "\n" in text or "\r" in text:
            text = text.replace("\r", " ").replace("\n", " ")
        safe_rows.append((key, text))
    larch_io.atomic_write(
        path=result_env,
        text=larch_io.format_kvs(safe_rows),
        mode=0o600,
        nofollow=True,
    )


def _step5_result_env_rows_from_text(text: str) -> list[tuple[str, str | int | bool]]:
    parsed = _parse_env_lines(text)
    rows: list[tuple[str, str | int | bool]] = [
        (key, parsed[key])
        for key in (
            "STEP5_REVIEW_STATUS",
            "STALL_TRACKING",
            "STALL_REASON",
            "ROUNDS_COMPLETED",
            "FINAL_ROUND_NUM",
            "FINAL_REVIEW_AND_FIX_STATUS",
            "CODER_STATUS",
            "FILES_CHANGED_HINT",
            "EFFECTIVE_ROUND_CAP",
        )
        if key in parsed
    ]
    rows.extend(_step5_difficulty_rows())
    return rows


def _emit_step5_envelope(*, status: str, stall_tracking: bool, stall_reason: str, rounds_completed: int, final_round: int, final_irf: str, coder_status: str, files_hint: str, effective_cap: int, extra_rows: list[tuple[str, str | int | bool]] | None = None, persist: bool = True) -> None:
    rows = _step5_envelope_rows(
        _Step5Envelope(
            status=status,
            stall_tracking=stall_tracking,
            stall_reason=stall_reason,
            rounds_completed=rounds_completed,
            final_round=final_round,
            final_irf=final_irf,
            coder_status=coder_status,
            files_hint=files_hint,
            effective_cap=effective_cap,
        )
    )
    if extra_rows:
        rows.extend(extra_rows)
    if persist:
        _write_step5_result_env(rows)
    for key, value in rows:
        _emit_kv(key=key, value=value)


def _build_step5_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix step5")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--round-num", default="")
    parser.add_argument("--mode", choices=("loop", "single", "mav-apply"), default="")
    parser.add_argument("--starting-round", default="1")
    parser.add_argument("--findings-file", default="")
    parser.add_argument("--session-env-path", default="")
    parser.add_argument("--codex-available", default="")
    parser.add_argument("--cursor-available", default="")
    parser.add_argument("--plan-file", default="")
    parser.add_argument("--feature-file", default="")
    parser.add_argument("--run-id", default="")
    parser.add_argument("--round-cap", default="2")
    parser.add_argument("--difficulty", default="")
    parser.add_argument("--audit-roll", default="")
    parser.add_argument("--diff-file", default="")
    parser.add_argument("--commit-count", default="0")
    parser.add_argument("--dynamic-archetypes", default="")
    parser.add_argument("--no-dynamic-archetypes", action="store_true")
    parser.add_argument("--pre-scouted-manifest", default="")
    parser.add_argument("--new-process-group", action="store_true")
    parser.add_argument("--orphan-timeout-s", default="")
    return parser


def _preflight_step5(args: argparse.Namespace) -> tuple[Path, int]:
    implement_tmpdir = Path(args.implement_tmpdir).resolve()
    if not implement_tmpdir.is_dir():
        raise ValueError(f"--implement-tmpdir not a directory: {args.implement_tmpdir}")
    if not args.mode:
        args.mode = "single" if args.round_num else "loop"
    if args.mode == "loop" and args.round_num:
        raise ValueError(f"--mode loop does not take --round-num (got: {args.round_num})")
    if args.mode in {"single", "mav-apply"} and not args.round_num:
        raise ValueError(f"--round-num is required for --mode {args.mode}")
    if args.round_num:
        args.round_num = str(_positive_int(value=args.round_num, label="--round-num"))
    starting_round = _positive_int(value=args.starting_round, label="--starting-round")
    if args.mode == "mav-apply" and not args.findings_file:
        raise ValueError("--findings-file is required for --mode mav-apply")
    if args.mode == "mav-apply" and not Path(args.findings_file).is_file():
        raise ValueError(f"--findings-file must name an existing file: {args.findings_file}")
    session_env = Path(args.session_env_path) if args.session_env_path else implement_tmpdir / "session-env.sh"
    feature_file = Path(args.feature_file) if args.feature_file else implement_tmpdir / "feature-description.txt"
    plan_file = Path(args.plan_file) if args.plan_file else implement_tmpdir / "plan.txt"
    if not os.access(session_env, os.R_OK):
        raise ValueError(f"session-env not readable: {session_env}")
    if not feature_file.is_file():
        raise ValueError(f"feature file not found: {feature_file}")
    if not plan_file.is_file():
        raise ValueError(f"plan file not found at conventional path: {plan_file}")
    if not plan_file.stat().st_size:
        raise ValueError(f"plan file is empty at conventional path: {plan_file}")
    run_id = args.run_id or _resolve_run_id(session_env_path=session_env, implement_tmpdir=implement_tmpdir, session_id_file=implement_tmpdir / "session-id")
    if not run_id:
        raise ValueError("RUN_ID unresolved from session-env, parent-issue, manifest, or session-id")
    args.run_id = run_id
    args.session_env_path = str(session_env)
    args.feature_file = str(feature_file)
    args.plan_file = str(plan_file)
    if not args.codex_available:
        args.codex_available = _session_get(session_env_path=session_env, key="CODEX_BINARY_FOUND", default="")
    if not args.cursor_available:
        args.cursor_available = _session_get(session_env_path=session_env, key="CURSOR_BINARY_FOUND", default="")
    if args.codex_available not in {"true", "false"}:
        args.codex_available = "true" if _codex_available() else "false"
    if args.cursor_available not in {"true", "false"}:
        args.cursor_available = "true" if _cursor_available() else "false"
    if args.no_dynamic_archetypes:
        args.dynamic_archetypes = "0"
    if args.difficulty:
        normalized = difficulty.normalize_tier(args.difficulty)
        if not normalized:
            raise ValueError("--difficulty must be TRIVIAL, MODERATE, or HARD")
        args.difficulty = normalized
    if args.mode != "mav-apply" and not args.pre_scouted_manifest:
        marker = implement_tmpdir / "step2-external-scout-eligible.txt"
        status_file = implement_tmpdir / "step2-scout-coder-status.env"
        scout_status = _env_get(path=status_file, key="SCOUT_CODER_STATUS", default=_session_get(session_env_path=session_env, key="SCOUT_CODER_STATUS", default=""))
        manifest = implement_tmpdir / "scout-coder-manifest.json"
        if marker.is_file() and scout_status == "ok" and manifest.is_file():
            args.pre_scouted_manifest = str(manifest)
    if args.mode == "mav-apply":
        args.pre_scouted_manifest = ""
    _dynamic_archetypes(args=args, implement_tmpdir=implement_tmpdir)
    return implement_tmpdir, starting_round


def _resolve_step5_tier(args: argparse.Namespace, *, implement_tmpdir: Path, starting_round: int) -> difficulty.TierResolution:
    record = implement_tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
    audit_roll = args.audit_roll
    rng: object = None
    if audit_roll:
        rng = int(audit_roll)
    resolution = difficulty.resolve_panel_tier(
        record,
        override=args.difficulty,
        rng=rng,
        audit_enabled=starting_round <= 1,
        round_num=starting_round,
    )
    args.panel_tier = resolution.panel_tier
    args.round_cap = str(resolution.round_cap)
    args.escalated_round = "true" if resolution.escalated_round else "false"
    return resolution


def _escalation_trigger_for_result(result: RoundResult) -> str:
    if result.skipped_finding_count and result.coder.input_count > 0:
        skip_ratio = result.skipped_finding_count / result.coder.input_count
        if skip_ratio >= _skip_ratio_threshold():
            return "bulk-skip"
    high_n = _high_severity_count(result.accepted_file)
    if high_n >= 2:
        return "high-severity"
    pre_head_file = pre_coder_snapshot_dir(result.round_dir) / "pre-coder-head.txt"
    post_head_file = result.round_dir / "post-coder-head.txt"
    structural = _structural_loc(pre_head_file=pre_head_file, post_head_file=post_head_file)
    if structural >= 100:
        return "structural-loc"
    if result.coder.input_count >= 8:
        return "finding-count"
    return ""


def _persist_round_start(*, implement_tmpdir: Path, round_num: int, start_s: int) -> None:
    round_dir = implement_tmpdir / f"round-{round_num}"
    if round_dir.is_symlink():
        return
    try:
        round_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        return
    if round_dir.is_symlink() or not round_dir.is_dir():
        return
    start_file = round_dir / "round-start-s"
    if start_file.is_symlink() or start_file.exists():
        return
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(start_file, flags, 0o644)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(f"{start_s}\n")
    except OSError:
        return


def _append_record_escalation_tool_failure(*, implement_tmpdir: Path, reason: str) -> None:
    execution = implement_tmpdir / "execution-issues.md"
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    entry = (
        f"\n## Tool Failure: record-escalation\n\n"
        f"- utc: `{ts}`\n"
        f"- helper: `python/cli.py stall-recovery record-escalation`\n"
        f"- reason: `{reason}`\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(log_file=execution, category="Tool Failures", entry=entry)


def _tmpdir_local_file(*, tmpdir: Path, file_path: Path) -> bool:
    if not file_path.is_absolute() or file_path.is_symlink() or not file_path.is_file():
        return False
    try:
        _ = file_path.resolve().relative_to(tmpdir.resolve())
    except ValueError:
        return False
    return True


def _record_escalation_if_needed(*, implement_tmpdir: Path, review_status: str, review_rc: int, stderr_path: Path) -> list[tuple[str, str | int | bool]]:
    rows: list[tuple[str, str | int | bool]] = []
    if review_status == "coder-main-agent-required":
        cmd = [
            sys.executable, str(_plugin_root() / "python" / "cli.py"), "stall-recovery", "record-escalation",
            "--implement-tmpdir", str(implement_tmpdir),
            "--site", "step5",
            "--trigger", "coder-main-agent-required",
            "--step", "5",
            "--phase", "review",
            "--dispatcher", "run-step5-review",
            "--exit-code", str(review_rc),
        ]
        if stderr_path.is_file() and stderr_path.stat().st_size and _tmpdir_local_file(tmpdir=implement_tmpdir, file_path=stderr_path):
            cmd += ["--failure-detail-log", str(stderr_path)]
        result = _run(cmd)
        if result.returncode == 0:
            rows.extend([
                ("STEP5_REVIEW_LEDGER_READY", "true"),
                ("STEP5_REVIEW_LEDGER_SITE", "step5"),
                ("STEP5_REVIEW_LEDGER_TRIGGER", "coder-main-agent-required"),
            ])
        else:
            if result.stderr:
                _err(result.stderr.rstrip())
            _append_record_escalation_tool_failure(implement_tmpdir=implement_tmpdir, reason=f"helper-exit-{result.returncode}")
            rows.extend([
                ("STEP5_REVIEW_LEDGER_READY", "true"),
                ("STEP5_REVIEW_LEDGER_SITE", "step5"),
                ("STEP5_REVIEW_LEDGER_TRIGGER", "coder-main-agent-required"),
            ])
    elif review_status == "main-agent-vote-required":
        rows.extend([
            ("STEP5_REVIEW_LEDGER_READY", "true"),
            ("STEP5_REVIEW_LEDGER_SITE", "step5-mav"),
            ("STEP5_REVIEW_LEDGER_TRIGGER", "main-agent-vote-required"),
        ])
    else:
        return rows
    rows.extend([
        ("STEP5_REVIEW_LEDGER_STEP", "5"),
        ("STEP5_REVIEW_LEDGER_PHASE", "review"),
        ("STEP5_REVIEW_LEDGER_DISPATCHER", "run-step5-review"),
        ("STEP5_REVIEW_LEDGER_EXIT_CODE", review_rc),
    ])
    if stderr_path.is_file() and stderr_path.stat().st_size:
        rows.append(("STEP5_REVIEW_LEDGER_FAILURE_DETAIL_LOG", str(stderr_path)))
    return rows


def _record_handoff_escalation_and_restage(*, implement_tmpdir: Path, review_status: str, review_rc: int, stderr_path: Path, run_id: str) -> list[tuple[str, str | int | bool]]:
    rows = _record_escalation_if_needed(implement_tmpdir=implement_tmpdir, review_status=review_status, review_rc=review_rc, stderr_path=stderr_path)
    _restage_difficulty_batch_fail_open(implement_tmpdir=implement_tmpdir, run_id=run_id)
    return rows


def _record_step5_round_timing(
    *,
    implement_tmpdir: Path,
    round_num: int,
    start_s: int,
    end_s: int,
    result: RoundResult,
) -> None:
    record_round_timing([
        "--implement-tmpdir", str(implement_tmpdir),
        "--round", str(round_num),
        "--start-s", str(start_s),
        "--end-s", str(end_s),
        "--accepted", str(result.accepted_count),
        "--rejected", str(result.rejected_count),
    ])


def _record_step5_round_timing_before_gates(
    *,
    implement_tmpdir: Path,
    round_num: int,
    start_s: int,
    result: RoundResult,
) -> None:
    if result.status == "fix-applied":
        return
    _record_step5_round_timing(
        implement_tmpdir=implement_tmpdir,
        round_num=round_num,
        start_s=start_s,
        end_s=int(time.time()),
        result=result,
    )


def _flush_review_batches_for_result(*, implement_tmpdir: Path, run_id: str, rounds_completed: int, result: RoundResult | None) -> None:
    try:
        flush_review_batches(
            impl_tmpdir=implement_tmpdir,
            run_id=run_id,
            rounds=rounds_completed,
            _accepted=result.total_accepted_count if result else 0,
            _rejected=result.total_rejected_count if result else 0,
            exonerated=result.total_exonerated_count if result else 0,
            _neutral=result.total_neutral_count if result else 0,
        )
    except Exception as exc:  # observability only: do not change terminal Step 5 status
        _err(f"⚠ review-and-fix: code-review batch flush failed: {exc}")
        entry = (
            "\n## Larch-log batch — `code-review` flush failed\n\n"
            f"Step 5 could not flush code-review run-log batches: `{exc}`\n"
        )
        with contextlib.suppress(OSError):
            run_logs.append_execution_issue(
                log_file=implement_tmpdir / "execution-issues.md",
                category="Warnings",
                entry=entry,
            )
    _restage_difficulty_batch_fail_open(implement_tmpdir=implement_tmpdir, run_id=run_id)


def _append_difficulty_restage_warning(*, implement_tmpdir: Path, reason: str) -> None:
    _err(f"⚠ review-and-fix: difficulty-rating batch restage failed: {reason}")
    entry = (
        "\n## Larch-log batch — `difficulty-rating` restage failed\n\n"
        f"Step 5 could not restage the resolved difficulty-rating run-log batch: `{reason}`\n"
    )
    with contextlib.suppress(OSError):
        run_logs.append_execution_issue(
            log_file=implement_tmpdir / "execution-issues.md",
            category="Warnings",
            entry=entry,
        )


def _restage_difficulty_batch_fail_open(*, implement_tmpdir: Path, run_id: str) -> None:
    try:
        _restage_difficulty_batch(implement_tmpdir=implement_tmpdir, run_id=run_id)
    except Exception as exc:  # observability only: do not change terminal Step 5 status
        _append_difficulty_restage_warning(implement_tmpdir=implement_tmpdir, reason=str(exc))


def _restage_difficulty_batch(*, implement_tmpdir: Path, run_id: str) -> None:
    clean_run_id = run_id.strip()
    if not clean_run_id:
        return
    record = implement_tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME
    if record.is_symlink() or not record.is_file():
        return
    result = _run([
        sys.executable,
        str(_plugin_root() / "python" / "cli.py"),
        "run-log",
        "write",
        "--log-root",
        str(implement_tmpdir / "larch-logs"),
        "--skill",
        "implement",
        "--run-id",
        clean_run_id,
        "--batch",
        "difficulty-rating",
        "--input-file",
        str(record),
    ])
    if result.returncode == 0:
        return
    detail = (result.stderr or result.stdout or "").strip()
    reason = f"helper-exit-{result.returncode}" + (f": {detail}" if detail else "")
    _append_difficulty_restage_warning(implement_tmpdir=implement_tmpdir, reason=reason)


def _finish_step5_terminal_success(*,
    terminal_status: str,
    args: argparse.Namespace,
    implement_tmpdir: Path,
    rounds_completed: int,
    result: RoundResult,
) -> int:
    _flush_review_batches_for_result(
        implement_tmpdir=implement_tmpdir,
        run_id=args.run_id,
        rounds_completed=rounds_completed,
        result=result,
    )
    _emit_step5_envelope(
        status="cap-hit" if terminal_status == "cap-hit" else "complete",
        stall_tracking=False,
        stall_reason="",
        rounds_completed=rounds_completed,
        final_round=result.round_num,
        final_irf=result.status,
        coder_status=result.coder.status,
        files_hint=result.coder.commit_sha,
        effective_cap=int(str(args.round_cap)),
    )
    return 0


def _apply_step5_new_process_group(parser: argparse.ArgumentParser) -> None:
    if not hasattr(os, "setsid"):
        parser.exit(2, "cli.py review-and-fix step5: --new-process-group failed: os.setsid is unavailable\n")
    try:
        os.setsid()
    except OSError as exc:
        parser.exit(2, f"cli.py review-and-fix step5: --new-process-group failed: {exc}\n")


def _parse_optional_positive_float(value: str, *, label: str) -> float | None:
    if not value:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be positive") from exc
    if parsed <= 0:
        raise ValueError(f"{label} must be positive")
    return parsed


def _step5_parse_optional_epoch(value: str) -> float | None:
    text = value.strip()
    if not text:
        return None
    try:
        parsed = float(text)
    except ValueError:
        return None
    return parsed if parsed > 0 else None


def _step5_detached_marker_value(*, implement_tmpdir: Path, key: str) -> str:
    marker = implement_tmpdir / config.IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE
    if marker.is_symlink() or not marker.is_file():
        return ""
    prefix = f"{key}="
    try:
        for line in marker.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith(prefix):
                return line.partition("=")[2]
    except OSError:
        return ""
    return ""


def _step5_orphan_timeout_elapsed(*, implement_tmpdir: Path, timeout_s: float | None) -> bool:
    if timeout_s is None:
        return False
    if (implement_tmpdir / config.IMPLEMENT_STEP5_REATTACH_ACTIVE_FILE).is_file():
        return False
    marker = implement_tmpdir / config.IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE
    if marker.is_symlink() or not marker.is_file():
        return False
    detached_at = _step5_parse_optional_epoch(_step5_detached_marker_value(implement_tmpdir=implement_tmpdir, key="DETACHED_AT_EPOCH"))
    if detached_at is not None:
        return time.time() - detached_at >= timeout_s
    try:
        age_s = time.time() - marker.stat().st_mtime
    except OSError:
        return False
    return age_s >= timeout_s


def _emit_step5_orphan_timeout(*, rounds_completed: int, final_round: int, effective_cap: int) -> int:
    _emit_step5_envelope(
        status="stall",
        stall_tracking=True,
        stall_reason="orphan-timeout",
        rounds_completed=rounds_completed,
        final_round=final_round,
        final_irf="orphan-timeout",
        coder_status="",
        files_hint="",
        effective_cap=effective_cap,
    )
    return 2


def normalize_status(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix normalize-status")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--stdout-file", required=True)
    parser.add_argument("--loop-rc", default="0")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code)
    implement_tmpdir = Path(args.implement_tmpdir)
    if implement_tmpdir.is_dir() and not implement_tmpdir.is_symlink():
        os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(implement_tmpdir)
    stdout_file = Path(args.stdout_file)
    if stdout_file.is_symlink() or not stdout_file.is_file():
        _emit_step5_envelope(status="stall", stall_tracking=True, stall_reason="missing-captured-stdout", rounds_completed=0, final_round=0, final_irf="unknown", coder_status="", files_hint="", effective_cap=2, persist=False)
        return 2
    try:
        text = stdout_file.read_text(encoding="utf-8", errors="replace")
    except OSError:
        _emit_step5_envelope(status="stall", stall_tracking=True, stall_reason="unreadable-captured-stdout", rounds_completed=0, final_round=0, final_irf="unknown", coder_status="", files_hint="", effective_cap=2, persist=False)
        return 2
    has_envelope = any(line.startswith("STEP5_REVIEW_STATUS=") and line.partition("=")[2] for line in text.splitlines())
    if has_envelope:
        terminal = implement_tmpdir / ".completed" / "step-5-terminal"
        with contextlib.suppress(FileNotFoundError):
            terminal.unlink()
        try:
            _write_step5_result_env(_step5_result_env_rows_from_text(text))
            _step5_write_terminal_sentinel(implement_tmpdir=implement_tmpdir)
        except OSError as exc:
            _err(f"review-and-fix normalize-status: {exc}")
            _emit_step5_envelope(
                status="stall",
                stall_tracking=True,
                stall_reason="internal-error",
                rounds_completed=0,
                final_round=0,
                final_irf="unknown",
                coder_status="",
                files_hint="",
                effective_cap=2,
                persist=False,
            )
            return 2
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        try:
            loop_rc = int(str(args.loop_rc))
        except ValueError:
            loop_rc = 0
        return loop_rc
    _ = implement_tmpdir
    _emit_step5_envelope(status="stall", stall_tracking=True, stall_reason="missing-step5-envelope", rounds_completed=0, final_round=0, final_irf="unknown", coder_status="", files_hint="", effective_cap=2, persist=False)
    return 2


# --- public entry points ---

def step5(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-step5")
    parser = _build_step5_parser()
    try:
        args = parser.parse_args(argv)
        if args.new_process_group:
            _apply_step5_new_process_group(parser)
        orphan_timeout_s = _parse_optional_positive_float(args.orphan_timeout_s, label="--orphan-timeout-s")
    except SystemExit as exc:
        return int(exc.code)
    except ValueError as exc:
        _err(f"review-and-fix step5: {exc}")
        return 2
    os.environ[config.ENV_IMPLEMENT_TMPDIR] = str(Path(args.implement_tmpdir).resolve())
    loop_mode = args.mode == "loop" or (not args.mode and not args.round_num)
    default_cap = _positive_int(value=str(args.round_cap), label="--round-cap") if str(args.round_cap).isdigit() else 2
    progress_done: Path | None = None
    if loop_mode and args.implement_tmpdir:
        progress_done = Path(args.implement_tmpdir).resolve() / "progress" / "done"
        with contextlib.suppress(FileNotFoundError):
            progress_done.unlink()
    try:
        try:
            implement_tmpdir, starting_round = _preflight_step5(args)
            resolution = _resolve_step5_tier(args, implement_tmpdir=implement_tmpdir, starting_round=starting_round)
            round_cap = resolution.round_cap
        except ValueError as exc:
            _err(f"review-and-fix step5: {exc}")
            if loop_mode:
                _emit_step5_envelope(status="stall", stall_tracking=False, stall_reason="preflight-failed", rounds_completed=0, final_round=0, final_irf="unknown", coder_status="", files_hint="", effective_cap=default_cap)
            return 2
        os.environ["IMPLEMENT_TMPDIR"] = str(implement_tmpdir)
        os.environ["CODEX_BINARY_FOUND"] = args.codex_available
        os.environ["CURSOR_BINARY_FOUND"] = args.cursor_available
        os.environ.setdefault("CLAUDE_PLUGIN_ROOT", str(_plugin_root()))
        os.environ["LARCH_TOKEN_SESSION_ID"] = _session_get(session_env_path=Path(args.session_env_path), key="LARCH_TOKEN_SESSION_ID", default=args.run_id)
        os.environ["LARCH_CLAUDE_SOURCE_FILE"] = _session_get(session_env_path=Path(args.session_env_path), key="LARCH_CLAUDE_SOURCE_FILE", default=os.environ.get("LARCH_CLAUDE_SOURCE_FILE", ""))
        os.environ["LARCH_TIMING_LEDGER"] = _session_get(session_env_path=Path(args.session_env_path), key="LARCH_TIMING_LEDGER", default=os.environ.get("LARCH_TIMING_LEDGER", ""))
        _run(["python3", str(_plugin_root() / "python" / "cli.py"), "timing", "mark", "--if-latest-differs", "Step 5 — code review"], env={**os.environ, "LARCH_TIMING_SKILL": "implement"})
        if not loop_mode:
            progress_done = implement_tmpdir / "progress" / "done"
        if args.mode == "mav-apply":
            args.round_num = str(_positive_int(value=args.round_num, label="--round-num"))
            round_dir = implement_tmpdir / f"round-{args.round_num}"
            round_dir.mkdir(parents=True, exist_ok=True)
            _write_pre_coder_snapshot(round_dir)
            coder = apply_findings_with_coder(input_file=Path(args.findings_file), round_dir=round_dir, result_file=round_dir / "coder.env", round_num=int(args.round_num))
            if coder.rc == 0 and coder.status == "applied":
                with contextlib.suppress(FileNotFoundError):
                    (round_dir / "post-coder-head.txt").unlink()
                head = _git_head()
                if head:
                    post = round_dir / "post-coder-head.txt"
                    _write_text(path=post, text=head + "\n")
                    post.chmod(0o444)
            _emit_kv(key="REVIEW_AND_FIX_STATUS", value="mav-apply-done")
            _emit_kv(key="CODER_STATUS", value=coder.status)
            return 0
        if args.mode == "single":
            args.round_num = args.round_num or "1"
            stderr_path = round_dir_stderr(implement_tmpdir=implement_tmpdir, round_num=int(args.round_num))
            with _stderr_sidecar(stderr_path):
                result = _run_round(args, suppress_emit=False)
            return result.rc
        if starting_round > 1:
            prior_round = starting_round - 1
            prior_env = implement_tmpdir / f"round-{prior_round}" / "review-and-fix.env"
            if starting_round > round_cap and prior_env.is_file():
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=0, result=None)
                _emit_step5_envelope(status="mav-resume-past-cap", stall_tracking=False, stall_reason="", rounds_completed=0, final_round=prior_round, final_irf="complete", coder_status="", files_hint="", effective_cap=round_cap)
                return 0
            if not _step5_probe_prior_round_env(implement_tmpdir=implement_tmpdir, prior_round=prior_round):
                _err(
                    f"IMPLEMENT_TMPDIR={implement_tmpdir} STARTING_ROUND={starting_round} "
                    f"expected_env_path={prior_env} base_cap={round_cap}"
                )
                _emit_step5_envelope(status="stall", stall_tracking=False, stall_reason="starting-round-invalid", rounds_completed=0, final_round=starting_round, final_irf="unknown", coder_status="", files_hint="", effective_cap=round_cap)
                return 2
        rounds_completed = 0
        last: RoundResult | None = None
        round_num = starting_round
        while True:
            if _step5_orphan_timeout_elapsed(implement_tmpdir=implement_tmpdir, timeout_s=orphan_timeout_s):
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=rounds_completed, result=last)
                final_round = last.round_num if last else max(0, round_num - 1)
                return _emit_step5_orphan_timeout(rounds_completed=rounds_completed, final_round=final_round, effective_cap=round_cap)
            if round_num > round_cap:
                prior = round_num - 1
                final_irf = last.status if last else "complete"
                coder_status = last.coder.status if last else ""
                files_hint = last.coder.commit_sha if last else ""
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=rounds_completed, result=last)
                _emit_step5_envelope(status="mav-resume-past-cap", stall_tracking=False, stall_reason="", rounds_completed=rounds_completed, final_round=prior, final_irf=final_irf, coder_status=coder_status, files_hint=files_hint, effective_cap=round_cap)
                return 0
            args.round_num = str(round_num)
            start_s = int(time.time())
            _persist_round_start(implement_tmpdir=implement_tmpdir, round_num=round_num, start_s=start_s)
            stderr_path = round_dir_stderr(implement_tmpdir=implement_tmpdir, round_num=round_num)
            with _stderr_sidecar(stderr_path):
                result = _run_round(args, suppress_emit=True)
            last = result
            rounds_completed = round_num
            if result.status in {"main-agent-vote-required", "coder-main-agent-required"}:
                _persist_round_start(implement_tmpdir=implement_tmpdir, round_num=round_num, start_s=start_s)
                handoff_rows = _record_handoff_escalation_and_restage(implement_tmpdir=implement_tmpdir, review_status=result.status, review_rc=0, stderr_path=stderr_path, run_id=args.run_id)
                _emit_step5_envelope(
                    status=result.status,
                    stall_tracking=False,
                    stall_reason="",
                    rounds_completed=rounds_completed,
                    final_round=round_num,
                    final_irf=result.status,
                    coder_status=result.coder.status,
                    files_hint=result.coder.commit_sha,
                    effective_cap=round_cap,
                    extra_rows=handoff_rows,
                )
                return 0
            if result.status == "self-review-required":
                _record_step5_round_timing_before_gates(
                    implement_tmpdir=implement_tmpdir,
                    round_num=round_num,
                    start_s=start_s,
                    result=result,
                )
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=rounds_completed, result=result)
                _emit_step5_envelope(
                    status="self-review-required",
                    stall_tracking=False,
                    stall_reason="",
                    rounds_completed=rounds_completed,
                    final_round=round_num,
                    final_irf=result.status,
                    coder_status=result.coder.status,
                    files_hint=result.coder.commit_sha,
                    effective_cap=round_cap,
                )
                return 0
            _record_step5_round_timing_before_gates(
                implement_tmpdir=implement_tmpdir,
                round_num=round_num,
                start_s=start_s,
                result=result,
            )
            terminal_status = result.status
            stall_reason = ""
            stall_tracking = False
            if result.status in {"panel-failed", "aggregator-validation-exhausted"}:
                terminal_status, stall_tracking, stall_reason = "stall", True, result.status
            elif result.status == "coder-failed":
                terminal_status, stall_tracking, stall_reason = (
                    "stall",
                    True,
                    {"submodule-violation": "submodule-violation"}.get(result.coder.status, "coder-failed"),
                )
            elif result.status in {"converged-small-changes", "no-changes", "no-findings", "in-scope-filtered-out", "complete", "prune-skipped"}:
                terminal_status = "complete"
            elif result.status in {"classifier-failed", "tally-flush-failed"}:
                terminal_status, stall_tracking, stall_reason = "stall", True, result.status
            elif result.status == "fix-applied":
                trigger = _escalation_trigger_for_result(result)
                if trigger and difficulty.normalize_tier(getattr(args, "panel_tier", ""), difficulty.MODERATE) != difficulty.HARD:
                    from_tier = difficulty.normalize_tier(getattr(args, "panel_tier", ""), difficulty.MODERATE)
                    to_tier = difficulty.next_tier(from_tier)
                    difficulty.append_escalation(
                        implement_tmpdir / difficulty.DIFFICULTY_RECORD_BASENAME,
                        round_num + 1,
                        from_tier,
                        to_tier,
                        trigger,
                    )
                    args.panel_tier = to_tier
                    round_cap = difficulty.tier_ceiling(to_tier)
                    args.round_cap = str(round_cap)
                    args.escalated_round = "true"
                    _emit_kv(key="ESCALATED_FROM", value=from_tier)
                    _emit_kv(key="ESCALATED_TO", value=to_tier)
                    _emit_kv(key="ESCALATION_TRIGGER", value=trigger)
                    _record_step5_round_timing(
                        implement_tmpdir=implement_tmpdir,
                        round_num=round_num,
                        start_s=start_s,
                        end_s=int(time.time()),
                        result=result,
                    )
                    round_num += 1
                    continue
                args.escalated_round = "false"
                try:
                    gate_status, gate_reason, gate_continue = _step5_post_round_gates(
                        result=result,
                        round_num=round_num,
                        round_cap=round_cap,
                    )
                finally:
                    _record_step5_round_timing(
                        implement_tmpdir=implement_tmpdir,
                        round_num=round_num,
                        start_s=start_s,
                        end_s=int(time.time()),
                        result=result,
                    )
                if gate_continue:
                    round_num += 1
                    continue
                if gate_status:
                    terminal_status = gate_status
                    stall_reason = gate_reason or ""
                    stall_tracking = gate_status == "stall"
            else:
                terminal_status = "stall"
                stall_tracking = True
                stall_reason = f"round-failed-{result.status}"
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=rounds_completed, result=result)
            if terminal_status == "stall":
                _emit_step5_envelope(status="stall", stall_tracking=stall_tracking, stall_reason=stall_reason, rounds_completed=rounds_completed, final_round=round_num, final_irf=result.status, coder_status=result.coder.status, files_hint=result.coder.commit_sha, effective_cap=round_cap)
                _flush_review_batches_for_result(implement_tmpdir=implement_tmpdir, run_id=args.run_id, rounds_completed=rounds_completed, result=result)
                return result.rc or 2
            return _finish_step5_terminal_success(terminal_status=terminal_status, args=args, implement_tmpdir=implement_tmpdir, rounds_completed=rounds_completed, result=result)
    except Exception as exc:
        _err(f"review-and-fix step5: {exc}")
        if loop_mode:
            _emit_step5_envelope(
                status="stall",
                stall_tracking=False,
                stall_reason="internal-error",
                rounds_completed=0,
                final_round=0,
                final_irf="unknown",
                coder_status="",
                files_hint="",
                effective_cap=default_cap,
                persist=not isinstance(exc, OSError),
            )
        return 2
    finally:
        if progress_done is not None:
            progress_done.parent.mkdir(parents=True, exist_ok=True)
            progress_done.touch(exist_ok=True)


def round_dir_stderr(*, implement_tmpdir: Path, round_num: int) -> Path:
    return implement_tmpdir / f"round-{round_num}" / "review-and-fix.stderr"


def apply_findings(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-apply-findings")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix apply-findings")
    parser.add_argument("--findings-file", required=True)
    parser.add_argument("--review-tmpdir", required=True)
    parser.add_argument("--session-env-path", "--session-env", default="")
    args = parser.parse_args(argv)
    findings = Path(args.findings_file)
    review_tmpdir = Path(args.review_tmpdir)
    if not findings.is_file():
        _err("review-and-fix apply-findings: --findings-file must name a file")
        return 2
    review_tmpdir.mkdir(parents=True, exist_ok=True)
    if args.session_env_path:
        _rehydrate_session_env(Path(args.session_env_path))
    if not findings.stat().st_size or _count_findings(findings) == 0:
        _emit_kv(key="REVIEW_AND_FIX_STATUS", value="no-findings")
        _emit_kv(key="FIX_COUNT", value=0)
        _emit_kv(key="CODER_TOOL", value="none")
        _emit_kv(key="CODER_STATUS", value="skipped")
        _emit_kv(key="SUBMODULE_SCRUB_COUNT", value=0)
        _emit_kv(key="SUBMODULE_REVERT_COUNT", value=0)
        return 0
    coder = apply_findings_with_coder(input_file=findings, round_dir=review_tmpdir, result_file=review_tmpdir / "coder.env")
    status = "complete" if coder.rc == 0 else "coder-main-agent-required" if coder.rc == 4 else "coder-failed"
    _emit_kv(key="REVIEW_AND_FIX_STATUS", value=status)
    _emit_kv(key="FIX_COUNT", value=coder.input_count or _count_findings(findings))
    _emit_kv(key="CODER_TOOL", value=coder.tool)
    _emit_kv(key="CODER_STATUS", value=coder.status)
    if coder.log_file:
        _emit_kv(key="CODER_LOG_FILE", value=coder.log_file)
    if coder.commit_sha:
        _emit_kv(key="CODER_COMMIT_SHA", value=coder.commit_sha)
    _emit_kv(key="SUBMODULE_SCRUB_COUNT", value=coder.scrub_count)
    _emit_kv(key="SUBMODULE_REVERT_COUNT", value=coder.revert_count)
    return 0 if coder.rc in {0, 4} else 2


def check_changes(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-check-changes")
    args = list(argv or [])
    baseline = ""
    head_baseline = ""
    strict = False
    parse_error = ""
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--baseline":
            if i + 1 >= len(args):
                parse_error = "--baseline requires a path argument"
                break
            baseline = args[i + 1]
            i += 2
        elif arg == "--head-baseline":
            if i + 1 >= len(args):
                parse_error = "--head-baseline requires a path argument"
                break
            head_baseline = args[i + 1]
            i += 2
        elif arg == "--strict":
            strict = True
            i += 1
        else:
            parse_error = f"Unknown argument: {arg}"
            break
    if parse_error:
        _err(f"ERROR={parse_error}")
        _emit_kv(key="FILES_CHANGED", value="false")
        _emit_kv(key="UNTRACKED_BASELINE", value="missing")
        _emit_kv(key="GIT_PROBE_FAILED", value="false")
        return 0
    git_probe_failed = False
    unstaged = _run(["git", "diff", "--name-only"])
    if unstaged.returncode != 0:
        git_probe_failed = True
        unstaged_out = ""
    else:
        unstaged_out = unstaged.stdout
    staged = _run(["git", "diff", "--name-only", "--cached"])
    if staged.returncode != 0:
        git_probe_failed = True
        staged_out = ""
    else:
        staged_out = staged.stdout
    untracked_baseline = "missing"
    untracked_delta: set[str] = set()
    if baseline and os.access(baseline, os.R_OK):
        untracked_baseline = "present"
        cur = _run(["git", "ls-files", "--others", "--exclude-standard"])
        if cur.returncode != 0:
            git_probe_failed = True
        else:
            current = set(filter(None, cur.stdout.splitlines()))
            base = set(filter(None, _read_text(Path(baseline)).splitlines()))
            untracked_delta = current - base
    head_moved = False
    if head_baseline and os.access(head_baseline, os.R_OK):
        baseline_head = _read_text(Path(head_baseline)).strip()
        current = _run(["git", "rev-parse", "HEAD"])
        if current.returncode != 0:
            git_probe_failed = True
        elif baseline_head and baseline_head != current.stdout.strip():
            head_moved = True
    files_changed = bool(unstaged_out.strip() or staged_out.strip() or untracked_delta or head_moved)
    if strict and git_probe_failed:
        files_changed = True
    _emit_kv(key="FILES_CHANGED", value=files_changed)
    _emit_kv(key="UNTRACKED_BASELINE", value=untracked_baseline)
    _emit_kv(key="GIT_PROBE_FAILED", value=git_probe_failed)
    return 0


def commit_fixes(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-commit-fixes")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix commit-fixes", add_help=False)
    parser.add_argument("--message", "-m", default="Address code review feedback")
    parser.add_argument("--stage-all", action="store_true")
    parser.add_argument("--help", action="store_true")
    parser.add_argument("files", nargs="*")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        _emit_commit_fixes_kvs(committed=False, sha="", error="usage", outcome="failed")
        return 2
    if args.help:
        _err("Usage: review-and-fix commit-fixes [--stage-all] [--message MSG] [files...]")
        return 0
    if not args.message.strip():
        _emit_commit_fixes_kvs(committed=False, sha="", error="--message must be non-empty", outcome="failed")
        return 2
    session = Path(os.environ.get("IMPLEMENT_TMPDIR", "")) / "session-env.sh"
    if session.is_file():
        for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
            if not os.environ.get(key):
                os.environ[key] = _session_get(session_env_path=session, key=key, default="")
    cli = _plugin_root() / "python" / "cli.py"
    _run(["python3", str(cli), "token", "mark", "Step 7 — commit review fixes"])
    _run(["python3", str(cli), "timing", "mark", "Step 7 — commit review fixes"], env={**os.environ, "LARCH_TIMING_SKILL": "implement"})
    if args.stage_all:
        return _commit_fixes_stage_all(args.message)
    result = _run([sys.executable, str(_PY_CLI), "git", "commit", "-m", args.message, *args.files])
    if result.returncode == 0:
        sha = _git_head()
        _emit_commit_fixes_kvs(committed=True, sha=sha, error="", outcome="ok")
        return 0
    _emit_commit_fixes_kvs(committed=False, sha="", error=_commit_fixes_result_error(result), outcome="failed")
    return result.returncode


def write_rejected(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-write-rejected")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix write-rejected")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--run-id", default="")
    parser.add_argument("--log-root", default="")
    args = parser.parse_args(argv)
    implement_tmpdir = Path(args.implement_tmpdir)
    if not implement_tmpdir.is_dir():
        _emit_kv(key="REJECTED_COUNT", value=0)
        _emit_kv(key="STATUS", value="failed")
        _emit_kv(key="ERROR", value="--implement-tmpdir not found")
        return 2
    summary = implement_tmpdir / "rejected-findings.md"
    full = implement_tmpdir / "rejected-findings-full.md"
    detail = full if full.is_file() and full.stat().st_size else summary
    if not detail.is_file() or not detail.stat().st_size:
        logging_util.emit("⏩ 16: rejected findings status=empty count=0")
        _emit_kv(key="REJECTED_COUNT", value=0)
        _emit_kv(key="STATUS", value="empty")
        return 0
    count = _count_rejected_lines(detail)
    if args.run_id and args.log_root:
        dest = Path(args.log_root) / "implement" / args.run_id / "rejected-findings.md"
        dest.parent.mkdir(parents=True, exist_ok=True)
        redacted = redact.redact_secrets_only(redact.redact_tmpdir_paths(_read_text(detail)))
        _write_text(path=dest, text=redacted)
    logging_util.emit(f"⚠ 16: rejected findings count={count} details={detail.name}")
    _emit_kv(key="REJECTED_COUNT", value=count)
    _emit_kv(key="STATUS", value="ok")
    return 0


def record_round_timing(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-record-round-timing")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix record-round-timing")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--round", required=True)
    parser.add_argument("--start-s", required=True)
    parser.add_argument("--end-s", required=True)
    parser.add_argument("--accepted", default="")
    parser.add_argument("--rejected", default="")
    try:
        args = parser.parse_args(argv)
        round_num = _non_negative_int(value=args.round, label="--round")
        start_s = _non_negative_int(value=args.start_s, label="--start-s")
        end_s = _non_negative_int(value=args.end_s, label="--end-s")
        accepted = _non_negative_int(value=args.accepted, label="--accepted") if args.accepted else -1
        rejected = _non_negative_int(value=args.rejected, label="--rejected") if args.rejected else -1
    except (SystemExit, ValueError) as exc:
        if not isinstance(exc, SystemExit):
            _err(f"record-round-timing: WARNING: {exc}")
        return 2
    implement_tmpdir = Path(args.implement_tmpdir).resolve()
    if not implement_tmpdir.is_dir() or implement_tmpdir.is_symlink():
        _err("record-round-timing: WARNING: --implement-tmpdir must name a directory")
        return 2
    round_dir = implement_tmpdir / f"round-{round_num}"
    if accepted < 0 or rejected < 0:
        tally = _parse_env_file(round_dir / "review-tally.env")
        if accepted < 0:
            raw = tally.get("ACCEPTED_COUNT", tally.get("ACCEPTED", ""))
            accepted = int(raw) if raw.isdigit() else _count_findings(round_dir / "accepted-findings.md")
        if rejected < 0:
            raw = tally.get("REJECTED_COUNT", tally.get("REJECTED", ""))
            if raw.isdigit():
                rejected = int(raw)
            else:
                rejected = _count_rejected_lines(round_dir / "rejected-findings.md")
    accepted = max(accepted, 0)
    rejected = max(rejected, 0)
    ledger = implement_tmpdir / "timing-ledger.tsv"
    step_label = "Step 5 — code review"
    if ledger.is_file():
        for line in _read_text(ledger).splitlines():
            parts = line.split("\t")
            if _timing_row_matches(
                parts,
                round_num=round_num,
                start_s=start_s,
                end_s=end_s,
                step_label=step_label,
            ):
                return 0
    env = {**os.environ, "IMPLEMENT_TMPDIR": str(implement_tmpdir), "LARCH_TIMING_LEDGER": str(ledger), "LARCH_TIMING_SKILL": "implement"}
    _run([
        "python3", str(_plugin_root() / "python" / "cli.py"), "timing", "record-round",
        "--skill", "implement",
        "--step", step_label,
        "--round", str(round_num),
        "--start-s", str(start_s),
        "--end-s", str(end_s),
        "--accepted", str(accepted),
        "--rejected", str(rejected),
    ], env=env)
    if ledger.is_file():
        return 0
    return 1


def _self_review_findings_jsonl(*, accepted: int, rejected: int) -> str:
    tally_data = {"mode": "self-review", "accepted_count": accepted, "rejected_count": rejected}
    records: list[str] = []
    for item in self_review_tally.self_review_tally_items(tally_data):
        record = {
            "id": item.finding_id,
            "issue_number": "0",
            "phase": "code-review",
            "outcome": item.outcome,
            "schema_version": "2",
            "reviewer_slots": ["self-review"],
            "round_num": "1",
            "category": "",
            "body_severity": "",
            "focus_area": "",
            "prose_body": "",
        }
        records.append(json.dumps(record, separators=(",", ":")))
    return "".join(f"{record}\n" for record in records)


def write_self_review_tally(argv: list[str] | None = None) -> int:
    """Emit the Step 5 self-review run-log artifacts (best effort).

    Writes ``code-review-tally.json`` (mode ``self-review``) and matching
    ``review-findings-full.jsonl`` rows so final reports, audit runs, and
    difficulty calibration can recover self-review counts when the tally is
    unavailable. Observability only: writer failures are surfaced (stderr plus
    fail-open Warnings entries) but the verb still returns 0 so the thin
    SKILL.md launcher fence never blocks Step 6.
    """
    logging_util.quiet_init(argv0="review-and-fix-write-self-review-tally")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix write-self-review-tally")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2
    implement_tmpdir = Path(args.implement_tmpdir)
    if not implement_tmpdir.is_dir():
        _err("write-self-review-tally: WARNING: --implement-tmpdir must name a directory")
        return 2
    if not args.run_id:
        _err("write-self-review-tally: WARNING: --run-id must be non-empty")
        return 2
    accepted = _count_matching_lines(
        implement_tmpdir / "self-review-accepted.md",
        pattern=r"^### \[Code Review\] Self-review accepted",
    )
    rejected = _count_matching_lines(
        implement_tmpdir / "rejected-findings.md",
        pattern=r"^### \[Code Review\] Self-review$",
    )
    log_root = implement_tmpdir / "larch-logs"
    batch_input = implement_tmpdir / "larch-log-batches-input"
    batch_input.mkdir(parents=True, exist_ok=True)
    findings_file = batch_input / "review-findings-full.jsonl"
    _write_text(path=findings_file, text=_self_review_findings_jsonl(accepted=accepted, rejected=rejected))
    tally_result = _run([
        "python3", str(_PY_CLI), "voting", "write-tally",
        "--log-root", str(log_root),
        "--skill", "implement",
        "--run-id", args.run_id,
        "--phase", "code-review",
        "--mode", "self-review",
        "--rounds", "1",
        "--accepted", str(accepted),
        "--rejected", str(rejected),
    ])
    observe_code_review_tally_flush(impl_tmpdir=implement_tmpdir, run_id=args.run_id, result=tally_result)
    if tally_result.returncode != 0:
        _err(f"⚠ review-and-fix: self-review write-tally failed (rc={tally_result.returncode})")
        if tally_result.stderr:
            _err(tally_result.stderr.rstrip())
    findings_result = _run([
        "python3", str(_PY_CLI), "run-log", "write",
        "--log-root", str(log_root),
        "--skill", "implement",
        "--run-id", args.run_id,
        "--batch", "review-findings-full",
        "--input-file", str(findings_file),
    ])
    if findings_result.returncode != 0:
        _err(f"⚠ review-and-fix: self-review run-log write review-findings-full failed (rc={findings_result.returncode})")
        if findings_result.stderr:
            _err(findings_result.stderr.rstrip())
    if tally_result.returncode == 0 and findings_result.returncode != 0:
        with contextlib.suppress(OSError):
            run_logs.append_execution_issue(
                log_file=implement_tmpdir / "execution-issues.md",
                category="Warnings",
                entry="Step 5 self-review findings emission failed; final report may fall back to Code review: N/A.",
            )
    return 0


def write_pre_self_review_snapshot(argv: list[str] | None = None) -> int:
    logging_util.quiet_init(argv0="review-and-fix-write-pre-self-review-snapshot")
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix write-pre-self-review-snapshot")
    parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    implement_tmpdir = Path(args.implement_tmpdir)
    if not implement_tmpdir.is_dir():
        _err("write-pre-self-review-snapshot: --implement-tmpdir must name a directory")
        return 2
    # Guard: unstaged working-tree changes get baked into the snapshot baseline,
    # causing commit-route to see "no delta" and stall later (#5662).
    unstaged = [p for p in _git_output(["diff", "--name-only"]).splitlines() if p]
    if unstaged:
        listed = ", ".join(unstaged[:5]) + (" (and more)" if len(unstaged) > 5 else "")
        _err(
            f"write-pre-self-review-snapshot: {len(unstaged)} unstaged modified"
            f" file(s) found; commit or discard before snapshotting: {listed}"
        )
        return 1
    head = _write_pre_self_review_snapshot(implement_tmpdir)
    _emit_kv(key="PRE_SELF_REVIEW_HEAD", value=head)
    return 0
# pyright: reportPrivateUsage=false, reportUnusedImport=false
