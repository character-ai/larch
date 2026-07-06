# pyright: reportUnusedCallResult=false, reportUnusedFunction=false, reportPrivateUsage=false
"""Flush and finalization operations for larch run-logs."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import suppress
from pathlib import Path
from typing import cast

from larch.core import architectural_guidelines
from larch.core import config
from larch.core import proc
from larch.core import redact
from larch.calibration import difficulty
from larch.core.proc import Runner
from larch.core.run_context import RunContext
from larch.errors import ShipError
from larch.git import pr_body
from larch.report import exec_issue_detail
from larch.report import final_report
from larch.report import timing
from larch.report import tokens

from larch.report.run_log_batch import (
    _REPO_ROOT,
    _append_execution_issue,
    _larch_sessions_scratch_dir,
    _normalize_body_for_hash,
    _path_is_repo_related,
    _redact_batch_payload,
    _read_kv_file,
    _read_state_kv,
    _write_batch,
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
from larch.report.run_log_commit import _commit_run


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


def _render_ledger_reports(*, runner: Runner, ctx: RunContext, log_root: Path) -> None:
    """Re-render token/timing JSON from ledgers (python3 python/cli.py run-log refresh parity)."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    tmpdir = Path(ctx.tmpdir)
    token_path = tmpdir / "token-report-refresh.json"
    timing_path = tmpdir / "timing-report-refresh.json"
    env = _report_subprocess_env(ctx)
    with suppress(Exception):
        rendered = tokens.token_report(mode="full", fmt="json", env=env)
        if isinstance(rendered, dict):
            _write_report_json(path=token_path, data=rendered)
    if token_path.is_file():
        with suppress(Exception):
            _write_batch(log_root=log_root, skill="implement", run_id=run_id, batch="token-report", input_file=str(token_path))
    with suppress(Exception):
        ledger = timing.resolve_timing_ledger_path(env=env)
        if ledger is not None:
            data = timing.TimingReport(ledger).render_json(env=env)
            _write_report_json(path=timing_path, data=data)
    if timing_path.is_file():
        with suppress(Exception):
            _write_batch(log_root=log_root, skill="implement", run_id=run_id, batch="timing-report", input_file=str(timing_path))


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


def _execution_issue_record(
    *, body_lines: list[str],
    category: str,
    step_label: str,
    source_label: str,
    file_sha: str,
    seen_keys: set[str],
) -> str | None:
    body = "\n".join(body_lines)
    redacted_body = _redact_batch_payload(body)
    body_keys = _execution_issue_body_keys(category=category, body=redacted_body)
    if body_keys <= seen_keys:
        return None
    norm_sha = hashlib.sha256(
        _normalize_body_for_hash(redacted_body).encode("utf-8"),
    ).hexdigest()
    payload = {
        "phase": "implement",
        "step": step_label,
        "category": category,
        "source": source_label,
        "source_sha256": norm_sha or file_sha,
        "body": redacted_body,
    }
    seen_keys.update(body_keys)
    return json.dumps(payload, sort_keys=True)


def _execution_issue_body_keys(*, category: str, body: str) -> set[str]:
    return {f"{category}\0{key}" for key in exec_issue_detail.structured_body_dedupe_keys(body, category)}


def _existing_execution_issue_keys(existing_batch: str) -> set[str]:
    keys: set[str] = set()
    for raw in existing_batch.splitlines():
        try:
            row: object = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if not isinstance(row, dict):
            continue
        row_dict = cast("dict[str, object]", row)
        category = row_dict.get("category")
        body = row_dict.get("body")
        if isinstance(category, str) and isinstance(body, str):
            keys.update(_execution_issue_body_keys(category=category, body=body))
    return keys


def _execution_issue_chunks(body_lines: list[str]) -> list[list[str]]:
    chunks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in body_lines:
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            current.append(line)
            continue
        if not in_fence and line.startswith("- ") and current:
            if any(item.strip() for item in current):
                chunks.append(current)
            current = [line]
            continue
        current.append(line)
    if any(item.strip() for item in current):
        chunks.append(current)
    return chunks


def _append_execution_issue_records(
    *,
    records: list[str],
    body_lines: list[str],
    record_context: tuple[str, str, str, str],
    seen_keys: set[str],
) -> None:
    category, step_label, source_label, file_sha = record_context
    for chunk in _execution_issue_chunks(body_lines):
        record = _execution_issue_record(
            body_lines=chunk,
            category=category,
            step_label=step_label,
            source_label=source_label,
            file_sha=file_sha,
            seen_keys=seen_keys,
        )
        if record is not None:
            records.append(record)


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
    seen_keys = _existing_execution_issue_keys(existing)
    records: list[str] = []
    current_cat = "Tool Failures"
    body_lines: list[str] = []
    for line in issue_log.read_text(encoding="utf-8").splitlines():
        if line.startswith("### "):
            if body_lines:
                _append_execution_issue_records(
                    records=records,
                    body_lines=body_lines,
                    record_context=(current_cat, step_label, source_label, file_sha),
                    seen_keys=seen_keys,
                )
                body_lines = []
            current_cat = line.removeprefix("### ")
            continue
        body_lines.append(line)
    if body_lines:
        _append_execution_issue_records(
            records=records,
            body_lines=body_lines,
            record_context=(current_cat, step_label, source_label, file_sha),
            seen_keys=seen_keys,
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
    # Function-scoped import breaks the circular import:
    # run_logs → run_log_flush → stall_recovery → run_logs
    from larch.state import stall_recovery  # noqa: PLC0415
    outcome_values = stall_recovery.normalized_outcome_values(
        argparse.Namespace(implement_tmpdir=ctx.tmpdir, in_memory_stall_tracking=""),
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
    rc, _comment_url, error = pr_body.write_final_report(
        Path(ctx.tmpdir),
        skip_tracking_upsert=skip_tracking_upsert,
    )
    if rc != 0:
        msg = error or "final report write failed"
        raise ShipError(msg)


def write_final_report_comment(*, runner: Runner, ctx: RunContext) -> None:
    _ = runner
    rc, _comment_url, error = pr_body.write_final_report(Path(ctx.tmpdir), comment_only=True)
    if rc != 0:
        msg = error or "final report comment write failed"
        raise ShipError(msg)


def _stage_vendor_failure_diagnostics(*, ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    script = _REPO_ROOT / "scripts" / "flush-vendor-failure-diagnostics.sh"
    if not script.is_file():
        return
    with suppress(Exception):
        _ = proc.run(
            [
                "bash",
                str(script),
                "--tmpdir",
                ctx.tmpdir,
                "--run-id",
                run_id,
                "--log-root",
                str(log_root),
            ],
            cwd=str(_REPO_ROOT),
        )


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


def _stage_ship_route_handoff(*, ctx: RunContext, log_root: Path) -> None:
    run_id = effective_run_id(ctx)
    if not run_id:
        return
    handoff = Path(ctx.tmpdir) / ".ship-route-exit-handoff.env"
    if not handoff.is_file():
        return
    with suppress(Exception):
        _ = _write_batch(
            log_root=log_root,
            skill="implement",
            run_id=run_id,
            batch="ship-route-exit-handoff",
            input_file=str(handoff),
        )


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
            argparse.Namespace(
                override_source="",
                audit_upgrade="",
                escalation=None,
                round_cap="",
                codex_model_role="",
                audit_evaluated="",
                escalated_round="",
                override_tier="",
                panel_tier="",
            ),
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


def _stage_pre_commit(
    *, runner: Runner,
    ctx: RunContext,
    log_root: Path,
    cwd: str | None = None,
    mode: str = "refresh",
    strict_final_report: bool = False,
) -> None:
    run_dir = _run_log_dir(ctx)
    run_dir.mkdir(parents=True, exist_ok=True)
    if mode in {"refresh", "flush"}:
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


def flush_logs_pre(
    *, runner: Runner,
    ctx: RunContext,
    cwd: str | None = None,
    strict_final_report: bool = False,
) -> RefreshSkip:
    """Pre-push refresh: may git-commit log batches (caller owns push)."""
    skip = _pre_push_probe(ctx)
    if skip.skipped:
        return skip
    recovery = load_or_recover_manifest_checked(ctx)
    if not recovery.recovery_ok:
        return RefreshSkip(skipped=True, reason=REFRESH_SKIP_RECOVERY_FAILED)
    manifest = recovery.manifest
    log_root = Path(ctx.tmpdir) / "larch-logs"
    try:
        _stage_pre_commit(
            runner=runner,
            ctx=ctx,
            log_root=log_root,
            cwd=cwd,
            mode="refresh",
            strict_final_report=strict_final_report,
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
    if cwd is None:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_NO_REPO_CWD)
    try:
        commit_result = _commit_run(log_root=log_root, skill="implement", run_id=effective_run_id(ctx), cwd=cwd)
    except (OSError, ShipError) as exc:
        return RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=str(exc).strip(),
        )
    if commit_result.returncode != 0:
        err = (commit_result.stderr or commit_result.stdout or "").strip()
        return RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=err,
        )
    if commit_result.argv in {("larch-log-volatile-only",), ("true",)}:
        return RefreshSkip(skipped=True, reason=config.REFRESH_SKIP_VOLATILE_ONLY)
    return RefreshSkip(skipped=False, reason="")


def flush_logs_post(
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RefreshSkip:
    """Post-merge tmpdir-only flush; never git-commits."""
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
    ctx: RunContext,
    *,
    merge_result: str | None = None,
    runner: Runner | None = None,
) -> RefreshSkip:
    """Central postmerge finalization path: recover, write done/pr, then report."""
    return flush_logs_post(ctx, merge_result=merge_result, runner=runner)


def capture_session_transcript(
    *, ctx: RunContext,
    runner: Runner,
    defer_commit: bool = False,
) -> Path | None:
    """Copy refresh transcript into run tree with redaction (defer-commit parity)."""
    _ = runner
    run_id = effective_run_id(ctx)
    if not run_id:
        return None
    log_root = Path(ctx.tmpdir) / "larch-logs"
    issue_log = Path(ctx.tmpdir) / "execution-issues.md"
    source = os.environ.get("LARCH_CLAUDE_SOURCE_FILE", "")
    no_logs = _read_state_kv(state_file=ctx.state_file, key="NO_LOGS_COMMIT") or ("true" if ctx.no_logs_commit else "false")
    if source:
        _ = capture_transcript_main([
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
            "pre-push-refresh",
            "--refresh-mode",
            "true",
            "--defer-commit",
            "true" if defer_commit else "false",
        ])
    # Do NOT copy session-transcript-refresh.txt into the run tree: it is a
    # volatile in-loop snapshot that duplicates the canonical batch in nearly
    # all runs (issue #3708 Phase 1).
    out = Path(ctx.tmpdir) / "session-transcript-refresh.txt"
    return out if out.is_file() else None


def _capture_transcript_append_warning(
    *, issues_log: Path | None,
    step_label: str,
    status: str,
    message: str,
) -> None:
    if issues_log is None:
        return
    entry = f"- **Step {step_label}: session-transcript status={status}:** {message}"
    with suppress(OSError):
        _append_execution_issue(log_file=issues_log, category="Warnings", entry=entry)


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
                message=f"session-transcript render failed; transcript was not committed: {msg}",
            )
        if not rendered.is_file() or rendered.stat().st_size == 0:
            return _capture_transcript_emit(
                issues_log=issues_log,
                step_label=args.warning_step_label,
                status="render-empty",
                message="session-transcript renderer produced an empty file; transcript was not committed.",
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
            message="--no-logs-commit was set; transcript was written under the staging log root but not committed.",
        )
    if args.defer_commit == "true":
        print("SESSION_TRANSCRIPT_STATUS=captured")
        return 0
    commit = _commit_run(log_root=log_root, skill=args.skill, run_id=args.run_id, cwd=str(Path.cwd()))
    if commit.returncode != 0:
        err = (commit.stderr or "larch-log commit failed").strip().replace("\n", " ")
        return _capture_transcript_emit(
            issues_log=issues_log,
            step_label=args.warning_step_label,
            status="commit-failed",
            message=err,
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
    )


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
    skip = flush_logs_pre(runner=proc, ctx=ctx, cwd=str(Path.cwd()))
    if skip.skipped:
        if skip.reason in {
            config.REFRESH_SKIP_COMMIT_FAILED,
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


def larch_log_flush_main(argv: list[str]) -> int:
    if argv:
        print(f"python3 python/cli.py run-log flush: unknown argument: {argv[0]}", file=sys.stderr)
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
        _stage_pre_commit(runner=proc, ctx=ctx, log_root=log_root, cwd=str(Path.cwd()), mode="flush")
        result = _commit_run(log_root=log_root, skill="implement", run_id=run_id, cwd=str(Path.cwd()))
        if result.returncode != 0:
            detail = result.stderr.strip()
            if detail:
                print(
                    f"WARN: larch-log flush failed: rc={result.returncode}: {detail}",
                    file=sys.stderr,
                )
            else:
                print(f"WARN: larch-log flush failed: rc={result.returncode}", file=sys.stderr)
        for line in result.stdout.splitlines():
            if line.startswith("SECRET_SCRUB_VIOLATIONS=") and not line.endswith("=0"):
                print(
                    "WARN: larch-log flush scrubbed secret-shaped values before commit",
                    file=sys.stderr,
                )
    except Exception as exc:
        print(f"WARN: larch-log flush failed: {exc}", file=sys.stderr)
    return 0
# pyright: reportArgumentType=false
