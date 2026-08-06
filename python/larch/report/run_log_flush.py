# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false
"""Checkpoint and terminal snapshot operations for larch run logs."""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import subprocess
import sys
import tempfile
from contextlib import redirect_stdout, suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.core import architectural_guidelines
from larch.core import config
from larch.core import proc
from larch.core import redact
from larch.core import rust_runtime
from larch.calibration import difficulty
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext
from larch.errors import ShipError
from larch.git import pr_body
from larch.issue import execution_issues
from larch.report import final_report
from larch.report import timing
from larch.report import tokens

from larch.report.run_log_batch import (
    _REPO_ROOT,
    _append_execution_issue,
    _larch_sessions_scratch_dir,
    _path_is_repo_related,
    _read_kv_file,
    _read_state_kv,
    _write_batch as _write_batch_impl,
    parse_preterminal_outcome_label,
    parse_preterminal_outcome_label_from_run_dir,
)
from larch.report.run_log_manifest import (
    REFRESH_SKIP_RECOVERY_FAILED,
    Manifest,
    RefreshSkip,
    _manifest_step9a1_explicitly_ran,
    _manifest_step9a1_explicitly_skipped,
    _pre_push_probe,
    _read_manifest_v2,
    _read_session_env_key,
    _run_log_dir,
    _write_manifest,
    effective_run_id,
    load_or_recover_manifest_checked,
    update_manifest,
    validate_run_id_slug,
)


@dataclass(frozen=True)
class TranscriptCaptureResult:
    status: str
    path: Path | None
    source_configured: bool
    artifact_present: bool = False
    omission_recorded: bool = False

    @property
    def ok(self) -> bool:
        if self.source_configured:
            return self.status in {"captured", "suppressed-no-logs-commit"}
        return self.artifact_present or self.omission_recorded


@dataclass(frozen=True)
class TerminalSnapshotResult:
    ok: bool
    transcript_status: str
    error: str = ""


_write_batch = _write_batch_impl


def _report_subprocess_env(ctx: RunContext) -> dict[str, str]:
    env: dict[str, str] = dict(os.environ)
    env["IMPLEMENT_TMPDIR"] = ctx.tmpdir
    env["LARCH_TIMING_SKILL"] = "implement"
    _ = env.pop("DESIGN_TMPDIR", None)
    for export_key, file_key in (
        ("LARCH_TOKEN_SESSION_ID", "LARCH_TOKEN_SESSION_ID"),
        ("LARCH_CLAUDE_SOURCE_FILE", "LARCH_CLAUDE_SOURCE_FILE"),
        ("LARCH_TIMING_LEDGER", "LARCH_TIMING_LEDGER"),
    ):
        value = _read_session_env_key(ctx=ctx, key=file_key)
        if value:
            env[export_key] = value
    return env


def _write_report_json(*, path: Path, data: dict[str, object]) -> None:
    tmp = path.with_name(path.name + ".tmp")
    _ = tmp.write_text(json.dumps(data, sort_keys=True) + "\n", encoding="utf-8")
    _ = tmp.replace(path)


def _render_ledger_reports(*, runner: Runner, ctx: RunContext, log_root: Path, strict: bool = False) -> None:
    """Re-render token and timing JSON from their live ledgers."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        if strict:
            raise ShipError("terminal ledger refresh requires a run id")
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    env = _report_subprocess_env(ctx)
    errors: list[str] = []
    try:
        rendered = tokens.token_report(mode="full", fmt="json", env=env)
        if isinstance(rendered, dict):
            _write_report_json(path=token_path, data=rendered)
        elif strict:
            errors.append("token report renderer returned no JSON object")
    except Exception as exc:
        errors.append(f"token report render failed: {exc}")
    if token_path.is_file():
        try:
            _write_batch(log_root=log_root, skill="implement", run_id=run_id, batch="token-report", input_file=str(token_path))
        except (OSError, ShipError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"token report staging failed: {exc}")
    elif strict:
        errors.append("token-report.json source was not produced")
    try:
        ledger = timing.resolve_timing_ledger_path(env=env)
        if ledger is not None:
            data = timing.TimingReport(ledger).render_json(env=env)
            _write_report_json(path=timing_path, data=data)
        elif strict:
            errors.append("timing ledger was unavailable")
    except Exception as exc:
        errors.append(f"timing report render failed: {exc}")
    if timing_path.is_file():
        try:
            _write_batch(log_root=log_root, skill="implement", run_id=run_id, batch="timing-report", input_file=str(timing_path))
        except (OSError, ShipError, ValueError, json.JSONDecodeError) as exc:
            errors.append(f"timing report staging failed: {exc}")
    elif strict:
        errors.append("timing-report.json source was not produced")
    if strict and errors:
        raise ShipError("; ".join(errors))


def _should_flush_execution_issues(
    *, ctx: RunContext,
    issue_log: Path,
    batch_path: Path,
) -> bool:
    if not issue_log.is_file() or issue_log.stat().st_size == 0:
        return False
    tmp = Path(ctx.tmpdir)
    if (tmp / ".execution-issues-step7a-reached").is_file():
        return True
    if (tmp / ".execution-issues-flushed.sha").is_file():
        return True
    return batch_path.is_file()


def _render_execution_issues_batch(
    *, ctx: RunContext,
    batch_dir: Path,
    step_label: str,
    source_label: str,
) -> None:
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    batch_path = batch_dir / "execution-issues.ndjson"
    if not _should_flush_execution_issues(ctx=ctx, issue_log=issue_log, batch_path=batch_path):
        return
    file_sha = hashlib.sha256(issue_log.read_bytes()).hexdigest()
    existing = batch_path.read_text(encoding="utf-8") if batch_path.is_file() else ""
    records = execution_issues.execution_issue_records(
        text=issue_log.read_text(encoding="utf-8"),
        existing_batch=existing,
        step_label=step_label,
        source_label=source_label,
        file_sha=file_sha,
    )
    if not records:
        return
    batch_path.parent.mkdir(parents=True, exist_ok=True)
    with batch_path.open("a", encoding="utf-8") as handle:
        for record in records:
            _ = handle.write(record + "\n")
    sentinel = Path(ctx.tmpdir) / ".execution-issues-flushed.sha"
    _ = sentinel.write_text(file_sha, encoding="utf-8")


def render_execution_issues_batch(
    *, ctx: RunContext,
    batch_dir: Path,
    step_label: str,
    source_label: str,
) -> None:
    _render_execution_issues_batch(
        ctx=ctx,
        batch_dir=batch_dir,
        step_label=step_label,
        source_label=source_label,
    )


def _reconcile_terminal_manifest_from_ctx(ctx: RunContext) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    run_dir = _run_log_dir(ctx)
    if not (run_dir / "final-summary.md").is_file():
        return
    outcome_values = rust_runtime.normalized_stall_outcome_values(
        proc.ProcRunner(),
        implement_tmpdir=ctx.tmpdir,
    )
    outcome = outcome_values.get("IMPLEMENT_NORMALIZED_OUTCOME", "bailed")
    rc, err = final_report._reconcile_manifest_for_terminal_report(  # pyright: ignore[reportPrivateUsage]  # noqa: SLF001
        Path(ctx.tmpdir),
        run_id=run_id,
        outcome=outcome,
    )
    if rc != 0:
        msg = err or "manifest reconcile failed"
        raise ShipError(msg)


def _write_final_report(
    *, runner: Runner,
    ctx: RunContext,
    skip_tracking_upsert: bool = False,
) -> None:
    _ = runner
    result = pr_body.write_final_report(
        Path(ctx.tmpdir),
        skip_tracking_upsert=skip_tracking_upsert,
    )
    if result.exit_code != 0:
        msg = result.error or "final report write failed"
        raise ShipError(msg)


def write_final_report_comment(*, runner: Runner, ctx: RunContext) -> None:
    _ = runner
    result = pr_body.write_final_report(Path(ctx.tmpdir), comment_only=True)
    if result.exit_code != 0:
        msg = result.error or "final report comment write failed"
        raise ShipError(msg)


def _stage_vendor_failure_diagnostics(*, ctx: RunContext, log_root: Path, strict: bool = False) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        if strict:
            raise ShipError("terminal vendor diagnostics refresh requires a run id")
        return
    script = _REPO_ROOT / "scripts" / "flush-vendor-failure-diagnostics.sh"
    if not script.is_file():
        if strict:
            raise ShipError("vendor diagnostics checkpoint helper is unavailable")
        return
    try:
        result = proc.run(
            ["bash", str(script), "--tmpdir", ctx.tmpdir, "--run-id", run_id, "--log-root", str(log_root)],
            cwd=str(_REPO_ROOT),
        )
    except Exception as exc:
        if strict:
            raise ShipError(f"vendor diagnostics refresh failed: {exc}") from exc
        return
    if not strict:
        return
    if result.returncode != 0:
        detail = (result.stderr or result.stdout or "").strip()
        raise ShipError(f"vendor diagnostics refresh exited {result.returncode}: {detail or 'no detail'}")
    values = larch_io.parse_kv(
        "\n".join((result.stdout or "").split()),
        duplicate_policy="last",
    )
    if values.get("FLUSH_STATUS") == "flushed" and values.get("BATCH_WRITTEN") != "true":
        raise ShipError("vendor diagnostics refresh did not stage its non-empty batch")


def _stage_guideline_ship_outcome(*, ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    path = architectural_guidelines.guideline_ship_outcome_path(Path(ctx.tmpdir))
    if not path.is_file() or path.is_symlink():
        return
    try:
        _write_batch(
            log_root=log_root,
            skill="implement",
            run_id=run_id,
            batch=config.RUN_LOG_BATCH_GUIDELINE_SHIP_OUTCOME,
            input_file=str(path),
        )
    except (OSError, ShipError, ValueError) as exc:
        raise ShipError(f"guideline outcome staging failed: {exc}") from exc


def _stage_invariant_ship_outcome(*, ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    path = architectural_guidelines.invariant_ship_outcome_path(Path(ctx.tmpdir))
    if not path.is_file() or path.is_symlink():
        return
    try:
        _write_batch(
            log_root=log_root,
            skill="implement",
            run_id=run_id,
            batch=config.RUN_LOG_BATCH_INVARIANT_SHIP_OUTCOME,
            input_file=str(path),
        )
    except (OSError, ShipError, ValueError) as exc:
        raise ShipError(f"invariant outcome staging failed: {exc}") from exc


def _stage_ship_route_handoff(*, ctx: RunContext, log_root: Path, strict: bool = False) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    handoff = Path(ctx.tmpdir) / ".ship-route-exit-handoff.env"
    if not handoff.is_file():
        return
    try:
        _ = _write_batch(
            log_root=log_root,
            skill="implement",
            run_id=run_id,
            batch="ship-route-exit-handoff",
            input_file=str(handoff),
        )
    except (OSError, ShipError, ValueError, json.JSONDecodeError) as exc:
        if strict:
            raise ShipError(f"ship route handoff staging failed: {exc}") from exc


def _read_finalize_kv(*, tmpdir: Path, key: str) -> str:
    return _read_kv_file(path=tmpdir / "finalize-state.sh", key=key)


def _read_run_flags_kv(*, tmpdir: Path, key: str) -> str:
    return _read_kv_file(path=tmpdir / "run-flags.sh", key=key)


def _step9a1_heuristic(ctx: RunContext) -> bool | None:
    tmpdir = Path(ctx.tmpdir)
    log_root = tmpdir / "larch-logs"
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    design_done = _read_finalize_kv(tmpdir=tmpdir, key="DESIGN_ONLY_DONE") == "true"
    no_issues = _read_run_flags_kv(tmpdir=tmpdir, key="NO_ISSUES") == "true"
    if design_done and no_issues:
        return False
    run_dir = log_root / "implement" / run_id
    manifest_path = run_dir / "manifest.json"
    stats = run_dir / "run-statistics.md"
    if manifest_path.is_file():
        with suppress(OSError, json.JSONDecodeError, TypeError):
            manifest = Manifest.from_json(_read_manifest_v2(manifest_path))
            if _manifest_step9a1_explicitly_skipped(manifest):
                return False
            if _manifest_step9a1_explicitly_ran(manifest):
                return stats.is_file()
    if stats.is_file():
        return True
    forked_target = _read_state_kv(state_file=ctx.state_file, key="FORKED_TARGET") == "true"
    if ctx.forked or forked_target:
        return False
    ndjson = run_dir / "oos-issues.ndjson"
    if ndjson.is_file() and ndjson.stat().st_size > 0:
        return False
    return None


def _token_sidecar_paths(tmpdir: Path) -> tuple[tuple[str, Path], ...]:
    pairs: list[tuple[str, Path]] = []
    for tool in ("codex", "cursor", "claude"):
        path = tmpdir / f"{tool}-tokens.json"
        if path.is_file():
            pairs.append((tool, path))
    return tuple(pairs)


def _timing_sidecar_paths(tmpdir: Path) -> tuple[tuple[str, Path], ...]:
    pairs: list[tuple[str, Path]] = []
    for tool in ("codex", "cursor", "claude"):
        path = tmpdir / f"{tool}-timing.json"
        if path.is_file():
            pairs.append((tool, path))
    return tuple(pairs)


def _render_token_timing_batches(*, ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    batch_dir = log_root / "implement" / run_id
    batch_dir.mkdir(parents=True, exist_ok=True)
    sidecars: list[tuple[str, Path]] = list(_token_sidecar_paths(tmpdir))
    has_canonical_sidecars = bool(sidecars)
    if token_path.is_file():
        sidecars.append(("refresh", token_path))
    timing_sidecars: list[tuple[str, Path]] = list(_timing_sidecar_paths(tmpdir))
    has_canonical_sidecars = has_canonical_sidecars or bool(timing_sidecars)
    if timing_path.is_file():
        timing_sidecars.append(("refresh", timing_path))
    if not has_canonical_sidecars:
        # No per-tool sidecars; refresh JSONs served as the only input — write
        # them as the canonical report and return.  Do NOT copy the -refresh.json
        # files themselves into batch_dir: they are volatile in-loop snapshots and
        # are byte-identical to token-report.json / timing-report.json in nearly
        # all runs (issue #3708 Phase 1).
        if token_path.is_file():
            _ = tokens.scrape_run(
                sidecar_paths=(("refresh", token_path),),
                timing_sidecar_paths=(("refresh", timing_path),) if timing_path.is_file() else (),
                output_path=batch_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson",
                timing_output_path=batch_dir / f"{config.RUN_LOG_BATCH_TIMING_REPORT}.ndjson",
            )
        return
    _ = tokens.scrape_run(
        sidecar_paths=tuple(sidecars),
        timing_sidecar_paths=tuple(timing_sidecars),
        output_path=batch_dir / f"{config.RUN_LOG_BATCH_TOKEN_REPORT}.ndjson",
        timing_output_path=batch_dir / f"{config.RUN_LOG_BATCH_TIMING_REPORT}.ndjson",
    )
    # Do NOT copy the -refresh.json files into batch_dir: they are volatile
    # in-loop snapshots that duplicate the canonical NDJSON written above.


def _refresh_difficulty_record(*, ctx: RunContext, log_root: Path, cwd: str | None) -> None:
    run_id = effective_run_id(ctx)
    if not run_id or not cwd:
        return
    run_dir = log_root / "implement" / run_id
    record_path = run_dir / difficulty.DIFFICULTY_RECORD_BASENAME
    if not record_path.is_file() or record_path.is_symlink():
        return
    try:
        data: object = json.loads(record_path.read_text(encoding="utf-8", errors="replace"))
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(data, dict):
        return
    data = cast("dict[str, object]", data)
    predicted = str(data.get("predicted_tier") or "").upper()
    confidence = str(data.get("confidence") or "").lower()
    rationale = str(data.get("rationale") or "")
    if not predicted or not confidence or not rationale:
        return
    try:
        source_rating = difficulty.validate_rating_object(
            {"predicted_tier": predicted, "confidence": confidence, "rationale": rationale}
        )
    except ValueError:
        return
    changed = proc.run(
        ["git", "diff", "--name-only", "HEAD"],
        cwd=cwd,
    )
    if changed.returncode != 0:
        return
    changed_paths = tuple(line.strip() for line in (changed.stdout or "").splitlines() if line.strip())
    rater = str(data.get("rater") or "unknown")
    with suppress(OSError, ValueError):
        kwargs: dict[str, object] = {
            "rater": rater,
            "rater_tool": str(data.get("rater_tool") or "unknown"),
            "rater_model": str(data.get("rater_model") or "unknown"),
            "changed_paths": changed_paths,
            "panel_skipped": str(data.get("panel_skipped") or ""),
            "audit_upgrade": str(data.get("audit_upgrade") or ""),
            "escalations": tuple(data.get("escalations") or ()),  # preserve structured escalation objects
        }
        if rater == "implement":
            kwargs["implement_rating"] = source_rating
        elif rater == "fallback":
            kwargs["fallback_rating"] = source_rating
        else:
            kwargs["design_rating"] = source_rating
        refreshed = difficulty.build_record(**kwargs)  # type: ignore[arg-type]
        refreshed = difficulty._merge_existing_record_fields(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            refreshed,
            data,
            difficulty.blank_merge_args(),
        )
        difficulty.write_record(record_path, refreshed)
        _write_batch(log_root=log_root, skill="implement", run_id=run_id, batch="difficulty-rating", input_file=str(record_path))


def _reconcile_stalled_summary_backstop(*, ctx: RunContext, strict_final_report: bool) -> None:
    run_dir = _run_log_dir(ctx)
    try:
        needed = final_report.stalled_summary_manifest_reconciliation_needed(run_dir)
        changed = final_report.reconcile_stalled_summary_from_manifest(run_dir)
        still_needed = final_report.stalled_summary_manifest_reconciliation_needed(run_dir)
    except OSError as exc:
        if strict_final_report:
            raise ShipError(f"stalled summary reconciliation failed: {exc}") from exc
        return
    if strict_final_report and needed and (not changed or still_needed):
        msg = "stalled summary reconciliation failed"
        raise ShipError(msg)


def _stage_local_checkpoint(
    *,
    runner: Runner,
    ctx: RunContext,
    log_root: Path,
    cwd: str | None = None,
    mode: str = "refresh",
    strict_final_report: bool = False,
) -> None:
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    if mode in {"refresh", "checkpoint"}:
        _refresh_difficulty_record(ctx=ctx, log_root=log_root, cwd=cwd)
    if mode == "refresh":
        _render_execution_issues_batch(
            ctx=ctx,
            batch_dir=run_dir,
            step_label="pre-push",
            source_label="execution-issues.md pre-push refresh",
        )
        if strict_final_report:
            _write_final_report(runner=runner, ctx=ctx, skip_tracking_upsert=True)
            final_summary = run_dir / "final-summary.md"
            if not final_summary.is_file():
                msg = "final-summary.md missing after final report write"
                raise ShipError(msg)
        else:
            with suppress(ShipError):
                _write_final_report(runner=runner, ctx=ctx)
        _reconcile_stalled_summary_backstop(ctx=ctx, strict_final_report=strict_final_report)
        _render_ledger_reports(runner=runner, ctx=ctx, log_root=log_root)
        _render_token_timing_batches(ctx=ctx, log_root=log_root)
    else:
        _render_execution_issues_batch(
            ctx=ctx,
            batch_dir=run_dir,
            step_label="commit-tail",
            source_label="execution-issues.md commit-tail",
        )
    _stage_vendor_failure_diagnostics(ctx=ctx, log_root=log_root)
    _stage_invariant_ship_outcome(ctx=ctx, log_root=log_root)
    _stage_guideline_ship_outcome(ctx=ctx, log_root=log_root)
    _stage_ship_route_handoff(ctx=ctx, log_root=log_root)
    if mode == "refresh":
        _ = capture_session_transcript(ctx=ctx, runner=runner, defer_commit=True)
        _render_execution_issues_batch(
            ctx=ctx,
            batch_dir=run_dir,
            step_label="pre-push-post-transcript",
            source_label="execution-issues.md post-transcript refresh",
        )
        if strict_final_report:
            _write_final_report(runner=runner, ctx=ctx, skip_tracking_upsert=True)
        else:
            with suppress(ShipError):
                _write_final_report(runner=runner, ctx=ctx, skip_tracking_upsert=True)
        if (run_dir / "final-summary.md").is_file():
            _reconcile_terminal_manifest_from_ctx(ctx)


def _refresh_skip_for_commit_result(commit_result: CommandResult) -> RefreshSkip | None:
    if commit_result.returncode == 0:
        return None
    err = (commit_result.stderr or commit_result.stdout or "").strip()
    reason = (
        config.REFRESH_SKIP_RUN_LOG_INCOMPLETE
        if commit_result.returncode == config.RUN_LOG_INCOMPLETE_RC
        else config.REFRESH_SKIP_COMMIT_FAILED
    )
    return RefreshSkip(skipped=True, reason=reason, error=err)


_PRETERMINAL_BLOCK_MESSAGE_MAX_CHARS = 300


def _parse_preterminal_outcome_label(text: str) -> str | None:
    return parse_preterminal_outcome_label(text)


def _parse_preterminal_outcome_label_from_run_dir(run_dir: Path) -> str | None:
    return parse_preterminal_outcome_label_from_run_dir(run_dir)


def _check_preterminal_outcome_label(outcome: str) -> None:
    label = outcome.strip().lower()
    if label in config.PRETERMINAL_FORBIDDEN_OUTCOME_LABELS:
        msg = (
            "refusing pre-terminal run-log staging with terminal outcome "
            f"label {label!r}"
        )
        raise ShipError(msg)


def _bounded_preterminal_message(message: str) -> str:
    return " ".join(message.split())[:_PRETERMINAL_BLOCK_MESSAGE_MAX_CHARS]


def _preterminal_outcome_commit_blocked(run_dir: Path) -> str | None:
    try:
        outcome = _parse_preterminal_outcome_label_from_run_dir(run_dir)
    except OSError as exc:
        return _bounded_preterminal_message(f"pre-terminal outcome check failed: {exc}")
    if outcome is None:
        return None
    try:
        _check_preterminal_outcome_label(outcome)
    except ShipError as exc:
        return _bounded_preterminal_message(
            f"{exc}; commit only neutral in-progress labels before terminal reconciliation"
        )
    return None


def _preterminal_outcome_refresh_skip(ctx: RunContext) -> RefreshSkip | None:
    blocked = _preterminal_outcome_commit_blocked(_run_log_dir(ctx))
    if blocked is None:
        return None
    return RefreshSkip(
        skipped=True,
        reason=config.REFRESH_SKIP_PRETERMINAL_OUTCOME,
        error=blocked,
    )


def refresh_logs_checkpoint(
    *, runner: Runner, ctx: RunContext, cwd: str | None = None, strict_final_report: bool = False
) -> RefreshSkip:
    """Refresh the mutable implement staging tree without publishing it."""
    skip = _pre_push_probe(ctx)
    if skip.skipped:
        return skip
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    log_root = Path(ctx.tmpdir) / "larch-logs"
    try:
        _stage_local_checkpoint(
            runner=runner, ctx=ctx, log_root=log_root, cwd=cwd, mode="refresh", strict_final_report=strict_final_report
        )
    except ShipError as exc:
        if strict_final_report:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED, error=str(exc).strip())
        raise
    if strict_final_report and not (_run_log_dir(ctx) / "final-summary.md").is_file():
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    step9a1 = _step9a1_heuristic(ctx)
    steps_update = dict(manifest.steps_ran)
    if step9a1 is not None:
        steps_update["step9a1"] = step9a1
    try:
        _ = update_manifest(ctx, steps_ran=steps_update)
    except (OSError, ShipError):
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    return RefreshSkip(skipped=False, reason="")


def refresh_postmerge_snapshot(
    ctx: RunContext, *, merge_result: str | None = None, runner: Runner | None = None
) -> RefreshSkip:
    """Post-merge tmpdir-only flush; terminal publication remains Step 18-owned."""
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    log_root = Path(ctx.tmpdir) / "larch-logs"
    resolved = merge_result or _read_state_kv(state_file=ctx.state_file, key="MERGE_RESULT") or ctx.merge_result
    finalize = resolved in config.POST_MERGE_MERGE_RESULTS
    pr_number = _read_state_kv(state_file=ctx.state_file, key="PR_NUMBER") if ctx.state_file else ""
    if not pr_number and ctx.pr_number is not None:
        pr_number = str(ctx.pr_number)
    try:
        if runner is not None:
            _write_final_report(runner=runner, ctx=ctx)
            _render_ledger_reports(runner=runner, ctx=ctx, log_root=log_root)
        _render_token_timing_batches(ctx=ctx, log_root=log_root)
    except ShipError as exc:
        reason = "redaction-failed" if "redaction" in str(exc).lower() else "post-merge-refresh-failed"
        return RefreshSkip(skipped=True, reason=reason)
    if (_run_log_dir(ctx) / "final-summary.md").is_file():
        try:
            _reconcile_terminal_manifest_from_ctx(ctx)
        except ShipError:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
        recovery = load_or_recover_manifest_checked(ctx)
        if not recovery.recovery_ok:
            return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
        manifest = recovery.manifest
    status = config.MANIFEST_STATUS_DONE if finalize else manifest.status
    extra = dict(manifest.extra or {})
    reserved = dict(manifest.reserved)
    if str(pr_number).isdigit():
        reserved["pr_number"] = int(pr_number)
    updated = Manifest(
        status=status,
        version=manifest.version,
        run_id=manifest.run_id,
        steps_ran=dict(manifest.steps_ran),
        created_at=manifest.created_at,
        updated_at=manifest.updated_at,
        extra=extra or None,
        reserved=reserved,
    )
    try:
        _write_manifest(ctx=ctx, manifest=updated)
    except OSError:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    return RefreshSkip(skipped=False, reason="")


def finalize_postmerge_logs(
    ctx: RunContext, *, merge_result: str | None = None, runner: Runner | None = None
) -> RefreshSkip:
    """Central postmerge finalization path: recover, write done/pr, then report."""
    return refresh_postmerge_snapshot(ctx, merge_result=merge_result, runner=runner)


def capture_session_transcript(
    *, ctx: RunContext, runner: Runner, defer_commit: bool = False, warning_step_label: str = "pre-push-refresh"
) -> TranscriptCaptureResult:
    """Copy the current transcript into the run tree and report the capture result."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        return TranscriptCaptureResult(status="run-id-missing", path=None, source_configured=False)
    log_root = Path(ctx.tmpdir) / "larch-logs"
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    source = os.environ.get("LARCH_CLAUDE_SOURCE_FILE", "")
    no_logs = _read_state_kv(state_file=ctx.state_file, key="NO_LOGS_COMMIT") or ("true" if ctx.no_logs_commit else "false")
    existing = log_root / "implement" / run_id / "session-transcript.jsonl"
    status = "source-not-configured"
    omission_recorded = False
    if source:
        output = io.StringIO()
        with redirect_stdout(output):
            _ = capture_transcript_main(
                [
                    "--source-file",
                    source,
                    "--log-root",
                    str(log_root),
                    "--tmpdir",
                    str(ctx.tmpdir),
                    "--skill",
                    "implement",
                    "--run-id",
                    run_id,
                    "--no-logs-commit",
                    no_logs,
                    "--execution-issues-log",
                    str(issue_log),
                    "--warning-step-label",
                    warning_step_label,
                    "--refresh-mode",
                    "true",
                    "--defer-commit",
                    "true" if defer_commit else "false",
                ]
            )
        rendered = output.getvalue()
        if rendered:
            sys.stdout.write(rendered)
        for line in rendered.splitlines():
            if line.startswith("SESSION_TRANSCRIPT_STATUS="):
                status = line.partition("=")[2].strip() or "unknown"
                break
    else:
        print("SESSION_TRANSCRIPT_STATUS=source-not-configured")
        if not existing.is_file():
            omission_recorded = _capture_transcript_append_warning(
                issues_log=issue_log,
                step_label=warning_step_label,
                status=status,
                message=(
                    "LARCH_CLAUDE_SOURCE_FILE was not configured; session-transcript.jsonl could not be refreshed."
                ),
            )
    # Do NOT copy session-transcript-refresh.txt into the run tree: it is a
    # volatile in-loop snapshot that duplicates the canonical batch in nearly
    # all runs (issue #3708 Phase 1).
    out = Path(ctx.tmpdir) / "session-transcript-refresh.txt"
    return TranscriptCaptureResult(
        status=status,
        path=out if out.is_file() else (existing if existing.is_file() else None),
        source_configured=bool(source),
        artifact_present=existing.is_file(),
        omission_recorded=omission_recorded,
    )


def _capture_transcript_append_warning(
    *, issues_log: Path | None,
    step_label: str,
    status: str,
    message: str,
) -> bool:
    if issues_log is None:
        return False
    entry = f"- **Step {step_label}: session-transcript status={status}:** {message}"
    try:
        _append_execution_issue(log_file=issues_log, category="Warnings", entry=entry)
    except OSError:
        return False
    return True


def _capture_transcript_emit(
    *, issues_log: Path | None,
    step_label: str,
    status: str,
    message: str,
) -> int:
    _capture_transcript_append_warning(issues_log=issues_log, step_label=step_label, status=status, message=message)
    print(f"SESSION_TRANSCRIPT_STATUS={status}")
    return 0


def _capture_transcript_redact_stderr(path: Path) -> str:
    if not path.is_file():
        return ""
    snippet = " ".join(path.read_text(encoding="utf-8", errors="replace").split())
    try:
        snippet = redact.redact_secrets_only(snippet)
    except Exception:
        snippet = "<REDACTION_FAILED>"
    return snippet[:300]


def _capture_transcript_scratch_dir(*, tmpdir: str, log_root: Path) -> Path:
    if tmpdir:
        scratch_dir = Path(tmpdir)
    elif _path_is_repo_related(log_root.parent):
        scratch_dir = _larch_sessions_scratch_dir()
    else:
        scratch_dir = log_root.parent
    scratch_dir.mkdir(parents=True, exist_ok=True)
    return scratch_dir


def _parse_capture_transcript_args(argv: list[str]) -> argparse.Namespace | None:
    parser = argparse.ArgumentParser(prog="cli.py run-log capture-transcript", add_help=False)
    parser.add_argument("--source-file", default="")
    parser.add_argument("--log-root", required=True)
    parser.add_argument("--tmpdir", default="")
    parser.add_argument("--skill", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--no-logs-commit", default="false")
    parser.add_argument("--execution-issues-log", default="")
    parser.add_argument("--warning-step-label", default="7a")
    parser.add_argument("--refresh-mode", default="false")
    parser.add_argument("--defer-commit", default="false")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("SESSION_TRANSCRIPT_STATUS=usage-error")
        return None
    if args.no_logs_commit not in {"true", "false"} or args.refresh_mode not in {"true", "false"} or args.defer_commit not in {"true", "false"}:
        print("SESSION_TRANSCRIPT_STATUS=usage-error")
        return None
    return args


def capture_transcript_main(argv: list[str]) -> int:
    args = _parse_capture_transcript_args(argv)
    if args is None:
        return 0
    issues_log = Path(args.execution_issues_log) if args.execution_issues_log else None
    log_root = Path(args.log_root)
    if not validate_run_id_slug(args.run_id):
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="invalid-run-id",
            message="run-id was invalid; transcript capture skipped.",
        )
    existing_transcript = log_root / args.skill / args.run_id / "session-transcript.jsonl"
    source = Path(args.source_file) if args.source_file else None
    transcript_path: Path | None = None
    if source is None or not source.is_file() or source.stat().st_size == 0:
        if args.refresh_mode == "true" and existing_transcript.is_file():
            return _capture_transcript_emit(
                issues_log=issues_log,
                step_label=args.warning_step_label,
                status="source-file-missing",
                message="Claude source file was empty or not a regular file; refresh skipped and prior transcript retained.",
            )
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="source-file-missing",
            message="Claude source file was empty or not a regular file; transcript capture skipped.",
        )
    for line in source.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("TRANSCRIPT_PATH="):
            transcript_path = Path(line.removeprefix("TRANSCRIPT_PATH=").strip())
            break
    if transcript_path is None or not transcript_path.is_file():
        if args.refresh_mode == "true" and existing_transcript.is_file():
            return _capture_transcript_emit(
                issues_log=issues_log,
                step_label=args.warning_step_label,
                status="transcript-path-missing",
                message="Claude source file did not contain a TRANSCRIPT_PATH entry; refresh skipped and prior transcript retained.",
            )
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="transcript-path-missing",
            message="Claude source file did not contain a TRANSCRIPT_PATH entry; transcript capture skipped.",
        )
    try:
        scratch_dir = _capture_transcript_scratch_dir(tmpdir=args.tmpdir, log_root=log_root)
    except OSError as exc:
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="write-failed",
            message=f"session-transcript scratch directory could not be created: {exc}",
        )
    rendered = Path(tempfile.mkstemp(prefix="session-transcript.", suffix=".jsonl", dir=scratch_dir)[1])
    render_err = Path(tempfile.mkstemp(prefix="render-stderr.", suffix=".log", dir=scratch_dir)[1])
    try:
        result = subprocess.run(
            [
                sys.executable,
                str(_REPO_ROOT / "python/cli.py"),
                "run-log",
                "render-session-transcript",
                "--input",
                str(transcript_path),
                "--output",
                str(rendered),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            if result.stderr:
                render_err.write_text(result.stderr, encoding="utf-8")
            msg = _capture_transcript_redact_stderr(render_err) or "session-transcript renderer exited non-zero with no stderr"
            return _capture_transcript_emit(
                issues_log=issues_log,
                step_label=args.warning_step_label,
                status="render-failed",
                message=f"session-transcript render failed; transcript was not staged: {msg}",
            )
        if not rendered.is_file() or rendered.stat().st_size == 0:
            return _capture_transcript_emit(
                issues_log=issues_log,
                step_label=args.warning_step_label,
                status="render-empty",
                message="session-transcript renderer produced an empty file; transcript was not staged.",
            )
        _write_batch(log_root=log_root, skill=args.skill, run_id=args.run_id, batch="session-transcript", input_file=str(rendered))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="write-failed",
            message=f"larch-log write failed; transcript was not captured: {exc}",
        )
    finally:
        rendered.unlink(missing_ok=True)
        render_err.unlink(missing_ok=True)
    if args.no_logs_commit == "true":
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="suppressed-no-logs-commit",
            message="--no-logs-commit was set; transcript was written under the staging log root but not published.",
        )
    print("SESSION_TRANSCRIPT_STATUS=captured")
    return 0


def _load_refresh_session_env(tmpdir: Path) -> None:
    session_env = tmpdir / "session-env.sh"
    if not session_env.is_file():
        return
    for key in ("LARCH_TOKEN_SESSION_ID", "LARCH_CLAUDE_SOURCE_FILE", "LARCH_TIMING_LEDGER"):
        value = _read_kv_file(path=session_env, key=key)
        if value:
            os.environ[key] = value
    os.environ["IMPLEMENT_TMPDIR"] = str(tmpdir)


def _refresh_context(*, tmpdir: Path, state_file: Path, run_id: str) -> RunContext:
    return RunContext(
        branch="",
        issue=_read_kv_file(path=state_file, key="ISSUE_NUMBER") or "",
        repo="",
        run_id=run_id,
        tmpdir=str(tmpdir),
        merge=False,
        draft=False,
        forked=_read_kv_file(path=state_file, key="FORKED_TARGET") == "true",
        manifest_path=str(tmpdir / "larch-logs" / "implement" / run_id / "manifest.json"),
        tool_label="",
        no_admin_fallback=False,
        repo_unavailable=False,
        state_file=str(state_file),
        no_logs_commit=_read_kv_file(path=state_file, key="NO_LOGS_COMMIT") == "true",
        merge_result=_read_kv_file(path=state_file, key="MERGE_RESULT"),
        stall_tracking=_read_kv_file(path=state_file, key="STALL_TRACKING") == "true",
        stall_step=_read_kv_file(path=state_file, key="STALL_STEP"),
    )


def _terminal_execution_issues_flush(*, ctx: RunContext, run_id: str) -> None:
    log_root = Path(ctx.tmpdir) / "larch-logs"
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    rc, status, _records, detail = execution_issues.flush_execution_issues_safety_net(
        log_root=log_root,
        run_id=run_id,
        issue_log=issue_log,
        step_label="18",
        source_label="execution-issues.md terminal snapshot",
    )
    if rc != 0 or status not in {"ok", "skip", "no-records"}:
        raise ShipError(
            f"terminal execution-issues checkpoint failed: status={status} rc={rc} detail={detail or 'none'}"
        )
    batch = log_root / "implement" / run_id / "execution-issues.ndjson"
    if not batch.exists():
        batch.parent.mkdir(parents=True, exist_ok=True)
        batch.touch()


def _record_terminal_snapshot_failure(*, ctx: RunContext, message: str) -> None:
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    bounded = " ".join(message.split())[:1000]
    try:
        _append_execution_issue(
            log_file=issue_log, category="Tool Failures", entry=f"- **Step 18 terminal snapshot**: {bounded}"
        )
    except OSError:
        return
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    with suppress(OSError, ShipError):
        _terminal_execution_issues_flush(ctx=ctx, run_id=run_id)


def _verify_terminal_snapshot_files(*, ctx: RunContext, transcript: TranscriptCaptureResult) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        raise ShipError("terminal snapshot verification requires a run id")
    run_dir = Path(ctx.tmpdir) / "larch-logs" / "implement" / run_id
    required = ("final-summary.md", "token-report.json", "timing-report.json", "execution-issues.ndjson")
    missing = [name for name in required if not (run_dir / name).is_file()]
    transcript_path = run_dir / "session-transcript.jsonl"
    if transcript.source_configured and not transcript_path.is_file():
        missing.append("session-transcript.jsonl")
    if missing:
        raise ShipError(f"terminal snapshot missing required files: {', '.join(missing)}")


def prepare_terminal_snapshot(
    *, runner: Runner, tmpdir: Path, run_id: str, cwd: str | None = None, no_logs_commit: bool = False
) -> TerminalSnapshotResult:
    """Prepare the complete mutable snapshot immediately before publication."""
    if not validate_run_id_slug(run_id):
        return TerminalSnapshotResult(
            ok=False, transcript_status="not-attempted", error="terminal snapshot requires a valid run id"
        )
    state_file = tmpdir / "finalize-state.sh"
    _load_refresh_session_env(tmpdir)
    ctx = _refresh_context(tmpdir=tmpdir, state_file=state_file, run_id=run_id).with_(no_logs_commit=no_logs_commit)
    transcript = TranscriptCaptureResult(status="not-attempted", path=None, source_configured=False)
    log_root = tmpdir / "larch-logs"
    run_dir = log_root / "implement" / run_id
    try:
        recovery = load_or_recover_manifest_checked(ctx)
        if not recovery.recovery_ok:
            raise ShipError("terminal manifest recovery failed")
        run_dir.mkdir(parents=True, exist_ok=True)
        _refresh_difficulty_record(ctx=ctx, log_root=log_root, cwd=cwd)
        _write_final_report(runner=runner, ctx=ctx, skip_tracking_upsert=True)
        _reconcile_stalled_summary_backstop(ctx=ctx, strict_final_report=True)
        _render_ledger_reports(runner=runner, ctx=ctx, log_root=log_root, strict=True)
        _render_token_timing_batches(ctx=ctx, log_root=log_root)
        _stage_vendor_failure_diagnostics(ctx=ctx, log_root=log_root, strict=True)
        _stage_invariant_ship_outcome(ctx=ctx, log_root=log_root)
        _stage_guideline_ship_outcome(ctx=ctx, log_root=log_root)
        _stage_ship_route_handoff(ctx=ctx, log_root=log_root, strict=True)
        transcript = capture_session_transcript(ctx=ctx, runner=runner, defer_commit=True, warning_step_label="18")
        if not transcript.ok:
            raise ShipError(
                f"terminal transcript refresh failed: status={transcript.status}; "
                "the prior staged transcript was retained when available"
            )
        _terminal_execution_issues_flush(ctx=ctx, run_id=run_id)
        _write_final_report(runner=runner, ctx=ctx, skip_tracking_upsert=True)
        _reconcile_terminal_manifest_from_ctx(ctx)
        recovery = load_or_recover_manifest_checked(ctx)
        if not recovery.recovery_ok:
            raise ShipError("terminal manifest reload failed")
        steps_update = dict(recovery.manifest.steps_ran)
        steps_update["step18"] = True
        updates: dict[str, object] = {"steps_ran": steps_update}
        if ctx.stall_tracking:
            updates["stalled_at_step"] = ctx.stall_step or "unknown"
        _ = update_manifest(ctx, **updates)
        _verify_terminal_snapshot_files(ctx=ctx, transcript=transcript)
    except (OSError, ShipError, ValueError, json.JSONDecodeError) as exc:
        error = " ".join(str(exc).split()) or exc.__class__.__name__
        _record_terminal_snapshot_failure(ctx=ctx, message=error)
        return TerminalSnapshotResult(ok=False, transcript_status=transcript.status, error=error)
    return TerminalSnapshotResult(ok=True, transcript_status=transcript.status)


def terminal_snapshot_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log prepare-terminal-snapshot", add_help=False)
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--repo-root", default="")
    parser.add_argument("--no-logs-commit", choices=("true", "false"), default="false")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("TERMINAL_SNAPSHOT_STATUS=failed")
        print("TERMINAL_SNAPSHOT_ERROR=usage-error")
        return 2
    tmpdir = Path(args.implement_tmpdir)
    if not tmpdir.is_absolute() or not tmpdir.is_dir() or tmpdir.is_symlink():
        print("TERMINAL_SNAPSHOT_STATUS=failed")
        print("TERMINAL_SNAPSHOT_ERROR=invalid-implement-tmpdir")
        return 2
    cwd = args.repo_root or None
    result = prepare_terminal_snapshot(
        runner=proc, tmpdir=tmpdir, run_id=args.run_id, cwd=cwd, no_logs_commit=args.no_logs_commit == "true"
    )
    print(f"TERMINAL_SNAPSHOT_STATUS={'prepared' if result.ok else 'failed'}")
    print(f"TERMINAL_SNAPSHOT_ERROR={result.error}")
    if result.ok:
        return 0
    return config.EXIT_INTERNAL_ERROR


def refresh_run_logs_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py run-log refresh", add_help=False)
    parser.add_argument("--state-file", default="")
    parser.add_argument("--implement-tmpdir", default=os.environ.get("IMPLEMENT_TMPDIR", ""))
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        print("REFRESH_COMMITTED=false REASON=usage-error")
        return 0
    tmpdir = Path(args.implement_tmpdir)
    state_file = Path(args.state_file) if args.state_file else tmpdir / "finalize-state.sh"
    if not state_file.is_file():
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_STATE_FILE_MISSING}")
        return 0
    run_id = _read_kv_file(path=state_file, key="RUN_ID")
    if not run_id:
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_NO_RUN_ID}")
        return 0
    if not validate_run_id_slug(run_id):
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_INVALID_RUN_ID}")
        return 0
    if _read_kv_file(path=state_file, key="NO_LOGS_COMMIT") == "true":
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_NO_LOGS_COMMIT}")
        return 0
    if (tmpdir / "post-merge-sentinel").is_file() or _read_kv_file(path=state_file, key="MERGE_RESULT") in config.POST_MERGE_MERGE_RESULTS:
        print(f"REFRESH_SKIPPED=true REASON={config.REFRESH_SKIP_POST_MERGE}")
        return 0
    _load_refresh_session_env(tmpdir)
    ctx = _refresh_context(tmpdir=tmpdir, state_file=state_file, run_id=run_id)
    skip = refresh_logs_checkpoint(runner=proc, ctx=ctx, cwd=str(Path.cwd()))
    if skip.skipped:
        if skip.reason in {
            config.REFRESH_SKIP_COMMIT_FAILED,
            config.REFRESH_SKIP_PRETERMINAL_OUTCOME,
            config.REFRESH_SKIP_RUN_LOG_INCOMPLETE,
            REFRESH_SKIP_RECOVERY_FAILED,
        }:
            err = " ".join(skip.error.split())
            if err:
                print(f"REFRESH_COMMITTED=false REASON={skip.reason} ERROR={err}")
            else:
                print(f"REFRESH_COMMITTED=false REASON={skip.reason}")
        elif skip.reason == config.REFRESH_SKIP_VOLATILE_ONLY:
            print("REFRESH_COMMITTED=false REASON=no-changes")
        else:
            print(f"REFRESH_SKIPPED=true REASON={skip.reason}")
    else:
        print("REFRESH_COMMITTED=true")
    return 0


def run_log_checkpoint_main(argv: list[str]) -> int:
    if argv:
        print(f"python3 python/cli.py run-log checkpoint: unknown argument: {argv[0]}", file=sys.stderr)
        return 0
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir or os.environ.get("LARCH_NO_LOGS_COMMIT") == "true":
        return 0
    sid = Path(tmpdir) / "session-id"
    if not sid.exists() or (Path(tmpdir) / "post-merge-sentinel").exists():
        return 0
    run_id = sid.read_text(encoding="utf-8", errors="replace").strip()
    if not validate_run_id_slug(run_id):
        return 0
    log_root = Path(tmpdir) / "larch-logs"
    ctx = RunContext(
        branch="",
        issue="",
        repo="",
        run_id=run_id,
        tmpdir=tmpdir,
        merge=False,
        draft=False,
        forked=False,
        manifest_path=str(log_root / "implement" / run_id / "manifest.json"),
        tool_label="",
        no_admin_fallback=False,
        repo_unavailable=False,
    )
    try:
        _stage_local_checkpoint(runner=proc, ctx=ctx, log_root=log_root, cwd=str(Path.cwd()), mode="checkpoint")
    except Exception as exc:
        print(f"WARN: run-log checkpoint failed: {exc}", file=sys.stderr)
        return config.EXIT_INTERNAL_ERROR
    return 0


# pyright: reportArgumentType=false
