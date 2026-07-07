"""Top-level ship-pr Python driver and CLI."""
# ruff: noqa: E402, F401
# pylint: disable=unused-import
# pyright: reportPrivateUsage=false, reportUnusedImport=false

from __future__ import annotations

import json
import sys


def _version_supported(version_info: object) -> bool:
    return tuple(version_info) >= (3, 11)  # type: ignore[arg-type]


if not _version_supported(sys.version_info):
    _VERSION_ERROR = "Python ship driver requires Python 3.11 or newer"
    print(
        json.dumps(
            {
                "detail": _VERSION_ERROR,
                "failed_run_id": "",
                "ledger_dispatcher": "",
                "ledger_exit_code": None,
                "ledger_failure_detail_log": "",
                "ledger_phase": "",
                "ledger_ready": False,
                "ledger_site": "",
                "ledger_step": "",
                "ledger_trigger": "",
                "merge_result": "",
                "needs_user_reason": "",
                "outcome": "STALLED",
                "pr_number": None,
                "pr_url": "",
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
    )
    print(f"ERROR: {_VERSION_ERROR}", file=sys.stderr)
    raise SystemExit(4)

import argparse
import os
import re
import traceback
from contextlib import suppress
from pathlib import Path
from typing import cast

from larch.core import architectural_guidelines
from larch.implement import ci_monitor
from larch.implement import main_health
from larch.core import config
from larch.issue import file_oos
from larch.state import finalize
from larch.git import gh
from larch.git import git
from larch.core import logging_util
from larch.git import merge
from larch.git import pr
from larch.git import pr_body
from larch.core import proc
from larch.git import push
from larch.core import redact
from larch.git import rebase
from larch.report import run_logs
from larch.errors import NeedsUserInput, PrePushConflictHandoff, ShipError, Stalled, TransientNetworkError
from larch.outcomes import Outcome, StepResult
from larch.core.proc import Runner
from larch.core.run_context import RunContext

# Re-exports from sibling modules — preserves `ship.X` access for callers and tests.
from larch.implement.ship_state import (
    INITIAL_SHIP_STATE_KEYS,
    _PYTHON_TRANSIENT_STALL_ATTEMPT,
    _breadcrumb,
    _patch_ship_state_keys,
    _state_file_kv,
    _state_file_under_tmpdir,
    _terminal_overlay_fields,
    _tmpdir_under_allowed_root,
    _truthy,
    _valid_pr_url,
    _write_ship_state,
)
from larch.implement.ship_result import (
    ShipResult,
    _error_to_result,
    _redacted_result_payload,
    _step_result_to_ship,
    _write_terminal_finalize_if_terminal,
    emit_result,
)
from larch.implement.ship_guidelines import (
    GuidelinesGateResult,
    GuidelinesShipOutcome,
    InvariantsGateResult,
    InvariantsShipOutcome,
    _pin_and_load_guidelines_note,
    clear_guideline_ship_outcome_sidecar,
    clear_invariant_ship_outcome_sidecar,
    load_or_prepare_guidelines_note,
    load_or_prepare_invariants_note,
    write_guideline_ship_outcome,
    write_invariant_ship_outcome,
)
from larch.implement.ship_pr import (
    _postmerge_should_flush,
    _pr_title,
    _publish_post_pr_terminal_snapshot,
    ShipReconciliationCounters,
    reconcile_committed_stalled_summary_if_recovered,
    _summary_from_manifest,
    _write_ci_fix_detail_log,
    _write_terminal_state,
    run_postmerge_phase,
)
from larch.implement.ship_merge import (
    ShipRebasePhaseResult,
    ShipRebaseVariant,
    _CiNotReadyGuard,
    _MergeLoopCounters,
    _handle_merge_ci_not_ready,
    _merge_loop_iteration_cap_stall,
    _post_ensure_flush_and_push,
    _ship_phase14_rebase,
    _ship_rebase_phase,
)
from larch.implement.ship_resume import (
    ResumePlan,
    _context_with_state_overlay,
    _empty_checks_params_for_monitor,
    _hydrate_fresh_context,
    _hydrate_resume_context,
    _is_active_pre_push_handoff,
    _merge_loop_uses_resume_counters,
    _monitor_persisted_counters,
    _resume_plan,
    _seed_last_monitored_head,
)
from larch.implement.ship_seed import (
    build_seed_initial_state_parser,
    seed_initial_state_main,
)


def _invalid_context_result(ctx: RunContext) -> ShipResult | None:
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return ShipResult(Outcome.STALLED, detail="invalid tmpdir")
    if not _state_file_under_tmpdir(ctx):
        return ShipResult(Outcome.STALLED, detail="invalid state_file")
    return None


def _resume_reconciliation_counters(resume: ResumePlan) -> ShipReconciliationCounters:
    return ShipReconciliationCounters(
        resume.iteration,
        resume.rebase_count,
        resume.fix_attempts,
        resume.transient_retries,
    )


def _blocked_resume_result(resume: ResumePlan) -> ShipResult | None:
    if resume.start == "blocked-rebase-continuation":
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="unsupported-rebase-continuation",
            detail=resume.detail,
            pr_number=resume.pr_number,
            pr_url=resume.pr_url,
        )
    if resume.start == "blocked-checkout-mismatch":
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="checkout-mismatch",
            detail=resume.detail,
        )
    return None


def _no_checks_phase14_reason(*, runner: Runner, working: RunContext, cwd: str) -> str:
    if working.pr_number is None:
        return ""
    state = gh.pr_merge_state_read(
        runner, working.pr_number, repo=working.repo, cwd=cwd
    )
    if state.returncode != 0:
        return ""
    try:
        data: object = json.loads(state.stdout or "{}")
    except json.JSONDecodeError:
        return ""
    if not isinstance(data, dict):
        return ""
    typed = cast("dict[str, object]", data)
    merge_state = str(typed.get("mergeStateStatus") or "")
    if merge_state in {"DIRTY", "BEHIND"}:
        return f"mergeStateStatus={merge_state}"
    return ""


def _write_phase14_flag(tmpdir: str, *, reason: str) -> None:
    phase14_flag = Path(tmpdir) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    with suppress(OSError):
        _ = phase14_flag.write_text(
            f"RESUME_PHASE={config.SHIP_PR_RRR_RESUME_PHASE}\nREASON={reason}\n",
            encoding="utf-8",
        )


def _committed_guideline_outcome_matches(*, ctx: RunContext, cwd: str) -> bool:
    run_id = run_logs.effective_run_id(ctx)
    if not run_id:
        return False
    sidecar = architectural_guidelines.guideline_ship_outcome_path(Path(ctx.tmpdir))
    committed = Path(cwd) / "larch-logs" / "implement" / run_id / architectural_guidelines.GUIDELINE_SHIP_OUTCOME_SIDECAR
    try:
        return sidecar.is_file() and committed.is_file() and sidecar.read_bytes() == committed.read_bytes()
    except OSError:
        return False


def _committed_invariant_outcome_matches(*, ctx: RunContext, cwd: str) -> bool:
    run_id = run_logs.effective_run_id(ctx)
    if not run_id:
        return False
    sidecar = architectural_guidelines.invariant_ship_outcome_path(Path(ctx.tmpdir))
    committed = Path(cwd) / "larch-logs" / "implement" / run_id / architectural_guidelines.INVARIANT_SHIP_OUTCOME_SIDECAR
    try:
        return sidecar.is_file() and committed.is_file() and sidecar.read_bytes() == committed.read_bytes()
    except OSError:
        return False


def _flush_guideline_outcome_before_pr(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str,
    resume: ResumePlan,
) -> None:
    step = "pr-create-guideline-outcome-refresh"
    try:
        refresh = run_logs.flush_logs_pre(
            runner=runner,
            ctx=ctx.with_(state_file=None),
            cwd=cwd,
        )
    except (OSError, ShipError) as exc:
        detail = logging_util.sanitize_diagnostic_line(str(exc).strip())
        refresh = run_logs.RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=detail,
        )
    if not refresh.skipped:
        return
    reason = refresh.reason or "unknown"
    if refresh.error:
        reason = f"{reason}: {logging_util.sanitize_diagnostic_line(refresh.error)}"
    if refresh.reason == config.REFRESH_SKIP_NO_LOGS_COMMIT:
        _breadcrumb(
            step="warning",
            detail=f"guideline outcome refresh skipped: {reason} (outcome cannot be committed)",
        )
        return
    if refresh.reason == config.REFRESH_SKIP_VOLATILE_ONLY and _committed_guideline_outcome_matches(ctx=ctx, cwd=cwd):
        _breadcrumb(step="warning", detail="guideline outcome refresh skipped: volatile-only with matching committed artifact")
        return
    _breadcrumb(step="warning", detail=f"guideline outcome refresh skipped: {reason}")
    _write_terminal_state(
        ctx=ctx.with_(stall_tracking=True, stall_step=step),
        result=Outcome.STALLED,
        step=step,
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
    )
    raise Stalled(f"architectural-guidelines outcome run-log refresh skipped: {reason}")


def _flush_invariant_outcome_before_pr(  # type: ignore[reportUnusedFunction]
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str,
    resume: ResumePlan,
) -> None:
    step = "pr-create-invariant-outcome-refresh"
    try:
        refresh = run_logs.flush_logs_pre(
            runner=runner,
            ctx=ctx.with_(state_file=None),
            cwd=cwd,
        )
    except (OSError, ShipError) as exc:
        detail = logging_util.sanitize_diagnostic_line(str(exc).strip())
        refresh = run_logs.RefreshSkip(
            skipped=True,
            reason=config.REFRESH_SKIP_COMMIT_FAILED,
            error=detail,
        )
    if not refresh.skipped:
        return
    reason = refresh.reason or "unknown"
    if refresh.error:
        reason = f"{reason}: {logging_util.sanitize_diagnostic_line(refresh.error)}"
    if refresh.reason == config.REFRESH_SKIP_NO_LOGS_COMMIT:
        _breadcrumb(
            step="warning",
            detail=f"invariant outcome refresh skipped: {reason} (outcome cannot be committed)",
        )
        return
    if refresh.reason == config.REFRESH_SKIP_VOLATILE_ONLY and _committed_invariant_outcome_matches(ctx=ctx, cwd=cwd):
        _breadcrumb(step="warning", detail="invariant outcome refresh skipped: volatile-only with matching committed artifact")
        return
    _breadcrumb(step="warning", detail=f"invariant outcome refresh skipped: {reason}")
    _write_terminal_state(
        ctx=ctx.with_(stall_tracking=True, stall_step=step),
        result=Outcome.STALLED,
        step=step,
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
    )
    raise Stalled(f"architectural-invariants outcome run-log refresh skipped: {reason}")


def _compose_pr_body_for_pr_create(
    *,
    pr_context: RunContext,
    architectural_invariants_note: str = "",
    architectural_guidelines_note: str = "",
) -> str:
    return pr_body.compose_pr_body(
        summary=_summary_from_manifest(pr_context),
        mermaid=pr_context.mermaid,
        test_plan=pr_context.test_plan or "- [ ] `make py-lint`\n- [ ] `make py-test`\n",
        issue_number=int(pr_context.issue_number or pr_context.issue)
        if (pr_context.issue_number or pr_context.issue).isdigit()
        else None,
        architectural_invariants_note=architectural_invariants_note,
        architectural_guidelines_note=architectural_guidelines_note,
    )


def _invariants_gate_before_pr(
    *,
    runner: Runner,
    pr_context: RunContext,
    repo_root: str,
    base_ref: str,
    resume: ResumePlan,
    flush_outcome: bool = True,
) -> InvariantsGateResult:
    compose_head_sha = git.try_rev_parse(runner, "HEAD", cwd=repo_root) or ""
    compose_base_ref = f"{'upstream' if pr_context.forked or pr_context.forked_target else 'origin'}/{base_ref}"
    clear_invariant_ship_outcome_sidecar(implement_tmpdir=pr_context.tmpdir)
    invariant_file = architectural_guidelines.read_invariants(repo_root=repo_root)
    if invariant_file.status == "absent":
        result = InvariantsGateResult(invariants_status="absent", reason="invariants-absent")
    elif invariant_file.status == "invalid":
        result = InvariantsGateResult(invariants_status="invalid", reason="invariants-invalid", detail=invariant_file.warning)
    elif not invariant_file.content.strip():
        result = InvariantsGateResult(invariants_status="present", assessment_kind="clean", reason="invariants-empty")
    else:
        result = load_or_prepare_invariants_note(
            implement_tmpdir=pr_context.tmpdir,
            head_sha=compose_head_sha,
            base_ref=compose_base_ref,
            repo_root=repo_root,
            forked_target=pr_context.forked or pr_context.forked_target,
        )
    if result.needs_assessment:
        return result
    if not compose_head_sha and not result.note:
        return result
    if not flush_outcome:
        return result
    outcome: InvariantsShipOutcome | None = None
    try:
        outcome = write_invariant_ship_outcome(
            implement_tmpdir=pr_context.tmpdir,
            result=result,
            head_sha=compose_head_sha,
            base_ref=compose_base_ref,
        )
    except OSError as exc:
        if pr_context.no_logs_commit:
            _breadcrumb(step="warning", detail=f"invariant outcome sidecar write skipped: {logging_util.sanitize_diagnostic_line(str(exc))}")
            return result
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step="pr-create-invariant-outcome-write"),
            result=Outcome.STALLED,
            step="pr-create-invariant-outcome-write",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        raise Stalled(f"architectural-invariants outcome sidecar write failed: {logging_util.sanitize_diagnostic_line(str(exc))}") from exc
    if pr_context.no_logs_commit:
        return result
    if outcome is not None and outcome.outcome == "dropped":
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step="pr-create-invariant-outcome-dropped"),
            result=Outcome.STALLED,
            step="pr-create-invariant-outcome-dropped",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        raise Stalled(f"architectural-invariants outcome dropped: {outcome.reason}")
    return result


def _guidelines_gate_before_pr(
    *,
    runner: Runner,
    pr_context: RunContext,
    repo_root: str,
    base_ref: str,
    resume: ResumePlan,
    flush_outcome: bool = True,
) -> GuidelinesGateResult:
    compose_head_sha = git.try_rev_parse(runner, "HEAD", cwd=repo_root) or ""
    compose_base_ref = f"{'upstream' if pr_context.forked or pr_context.forked_target else 'origin'}/{base_ref}"
    clear_guideline_ship_outcome_sidecar(implement_tmpdir=pr_context.tmpdir)
    result = load_or_prepare_guidelines_note(
        implement_tmpdir=pr_context.tmpdir,
        head_sha=compose_head_sha,
        base_ref=compose_base_ref,
        repo_root=repo_root,
        forked_target=pr_context.forked or pr_context.forked_target,
    )
    if result.needs_assessment:
        return result
    if not flush_outcome:
        return result
    outcome: GuidelinesShipOutcome | None = None
    try:
        outcome = write_guideline_ship_outcome(
            implement_tmpdir=pr_context.tmpdir,
            result=result,
            head_sha=compose_head_sha,
            base_ref=compose_base_ref,
        )
    except OSError as exc:
        if pr_context.no_logs_commit:
            _breadcrumb(step="warning", detail=f"guideline outcome sidecar write skipped: {logging_util.sanitize_diagnostic_line(str(exc))}")
            return result
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step="pr-create-guideline-outcome-write"),
            result=Outcome.STALLED,
            step="pr-create-guideline-outcome-write",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        raise Stalled(f"architectural-guidelines outcome sidecar write failed: {logging_util.sanitize_diagnostic_line(str(exc))}") from exc
    if pr_context.no_logs_commit:
        return result
    _flush_guideline_outcome_before_pr(
        runner=runner,
        ctx=pr_context,
        cwd=repo_root,
        resume=resume,
    )
    if outcome is not None and outcome.outcome == "dropped":
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step="pr-create-guideline-outcome-dropped"),
            result=Outcome.STALLED,
            step="pr-create-guideline-outcome-dropped",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        raise Stalled(f"architectural-guidelines outcome dropped: {outcome.reason}")
    return result


def _refresh_guidelines_gate_after_rebase(
    *,
    runner: Runner,
    pr_context: RunContext,
    repo_root: str,
    base_ref: str,
    resume: ResumePlan,
) -> ShipResult | None:
    if pr_context.pr_number is None:
        return None
    invariants_gate = _invariants_gate_before_pr(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
        base_ref=base_ref,
        resume=resume,
        flush_outcome=True,
    )
    if invariants_gate.needs_assessment:
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="architectural-invariants-assessment",
            detail=invariants_gate.detail,
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    if invariants_gate.assessment_kind == "violation":
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="architectural-invariants-violation",
            detail=invariants_gate.note or invariants_gate.detail,
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    guidelines_gate = _guidelines_gate_before_pr(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
        base_ref=base_ref,
        resume=resume,
        flush_outcome=True,
    )
    if guidelines_gate.needs_assessment:
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="architectural-guidelines-assessment",
            detail=guidelines_gate.detail,
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    body = _compose_pr_body_for_pr_create(
        pr_context=pr_context,
        architectural_invariants_note=invariants_gate.note,
        architectural_guidelines_note=guidelines_gate.note,
    )
    title = _pr_title(ctx=pr_context, runner=runner, cwd=repo_root)
    _ = pr.ensure_pr(
        runner=runner,
        ctx=pr_context,
        body=body,
        title=title,
        cwd=repo_root,
        base=base_ref,
    )
    return None


def _ship_postmerge_phase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
) -> ShipResult:
    _breadcrumb(step="post-merge")
    postmerge_watch = _postmerge_main_health_gate(
        runner=runner,
        working=working,
        cwd=cwd,
        counters=ShipReconciliationCounters(
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
        ),
    )
    if postmerge_watch is not None:
        return postmerge_watch
    post = run_postmerge_phase(runner=runner, ctx=working, cwd=cwd)
    if post.outcome is Outcome.OK:
        _write_ship_state(
            working,
            phase="done",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
        )
    return ShipResult(
        post.outcome,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        merge_result=working.merge_result,
        detail=post.detail,
    )


def _postmerge_main_health_gate(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    counters: ShipReconciliationCounters,
) -> ShipResult | None:
    if not (Path(working.tmpdir) / "main-health.env").is_file():
        return None
    _write_ship_state(
        working,
        phase="postmerge-push-watch",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
    )
    merged_head = git.try_rev_parse(runner, "origin/main", cwd=cwd) or git.try_rev_parse(runner, "HEAD", cwd=cwd)
    if not merged_head:
        detail = "post-merge push watch could not resolve merged main HEAD"
        _write_terminal_state(
            ctx=working.with_(stall_tracking=True, stall_step="postmerge-push-watch"),
            result=Outcome.STALLED,
            step="postmerge-push-watch",
            iteration=counters.iteration,
            rebase_count=counters.rebase_count,
            fix_attempts=counters.fix_attempts,
            transient_retries=counters.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            merge_result=working.merge_result,
            detail=detail,
        )
    waited = main_health.wait_main_health(
        runner,
        main_health.MainHealthWaitQuery(
            health=main_health.MainHealthQuery(
                repo=working.repo,
                base_branch="main",
                workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
                limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
                cwd=cwd,
                head_sha=merged_head,
            ),
            timeout=config.MAIN_HEALTH_WAIT_TIMEOUT_SEC,
            interval=config.MAIN_HEALTH_WAIT_POLL_INTERVAL_SEC,
        ),
    )
    health = waited.health
    if health.status == "pass":
        return None
    if health.status == "fail":
        _write_ship_state(
            working,
            phase="emergency-repair",
            iteration=counters.iteration,
            rebase_count=counters.rebase_count,
            fix_attempts=counters.fix_attempts,
            transient_retries=counters.transient_retries,
            extra_fields={
                "ORIGINAL_BRANCH_FORBIDDEN": "true",
                "MAIN_REPAIR_RUN_ID": health.failed_run_id,
                "MAIN_REPAIR_HEAD": health.head_sha or merged_head,
                "MAIN_HEALTH_HEAD_SHA": health.head_sha or merged_head,
            },
        )
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_POSTMERGE_MAIN_CI_FAIL,
            failed_run_id=health.failed_run_id,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            merge_result=working.merge_result,
            detail=health.detail,
        )
    _write_terminal_state(
        ctx=working.with_(stall_tracking=True, stall_step="postmerge-push-watch"),
        result=Outcome.STALLED,
        step="postmerge-push-watch",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        failed_run_id=health.failed_run_id,
    )
    return ShipResult(
        Outcome.STALLED,
        failed_run_id=health.failed_run_id,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        merge_result=working.merge_result,
        detail=health.detail or f"post-merge push CI health is {health.status}",
    )


def _read_main_health_sidecar(ctx: RunContext) -> dict[str, str]:
    path = Path(ctx.tmpdir) / "main-health.env"
    if not path.is_file() or path.is_symlink():
        return {}
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return {}
    data: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition("=")
        if sep and "\n" not in value and "\r" not in value:
            data[key] = value
    return data


def _main_health_repair_covers_active_failure(
    *,
    ctx: RunContext,
    health: main_health.MainHealthStatus,
) -> bool:
    sidecar = _read_main_health_sidecar(ctx)
    return (
        sidecar.get("MAIN_HEALTH_REPAIR_COMMITTED") == "true"
        and bool(health.failed_run_id)
        and sidecar.get("MAIN_HEALTH_REPAIR_FAILED_RUN_ID") == health.failed_run_id
        and bool(health.head_sha)
        and sidecar.get("MAIN_HEALTH_REPAIR_BASE_SHA") == health.head_sha
    )


def _premerge_main_health_gate(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
    base_ref: str,
    counters: ShipReconciliationCounters,
) -> ShipResult | None:
    if not (Path(working.tmpdir) / "main-health.env").is_file():
        return None
    health = main_health.read_main_health(
        runner,
        main_health.MainHealthQuery(
            repo=working.repo,
            base_branch=base_ref,
            workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
            limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
            cwd=repo_root,
        ),
    )
    if health.status == "pending":
        waited = main_health.wait_main_health(
            runner,
            main_health.MainHealthWaitQuery(
                health=main_health.MainHealthQuery(
                    repo=working.repo,
                    base_branch=base_ref,
                    workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
                    limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
                    cwd=repo_root,
                ),
                timeout=config.MAIN_HEALTH_WAIT_TIMEOUT_SEC,
                interval=config.MAIN_HEALTH_WAIT_POLL_INTERVAL_SEC,
            ),
        )
        health = waited.health
    if health.status == "pass":
        return None
    if health.status == "fail" and _main_health_repair_covers_active_failure(
        ctx=working,
        health=health,
    ):
        return None
    if health.status == "fail":
        _write_terminal_state(
            ctx=working.with_(
                stall_tracking=True,
                stall_step="main-ci",
                final_bail_reason=config.NEEDS_USER_MAIN_CI_FAIL,
            ),
            result=Outcome.NEEDS_USER_INPUT,
            step="main-ci",
            iteration=counters.iteration,
            rebase_count=counters.rebase_count,
            fix_attempts=counters.fix_attempts,
            transient_retries=counters.transient_retries,
            failed_run_id=health.failed_run_id,
        )
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_MAIN_CI_FAIL,
            failed_run_id=health.failed_run_id,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=health.detail,
        )
    _write_terminal_state(
        ctx=working.with_(stall_tracking=True, stall_step="main-ci"),
        result=Outcome.STALLED,
        step="main-ci",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        failed_run_id=health.failed_run_id,
    )
    return ShipResult(
        Outcome.STALLED,
        failed_run_id=health.failed_run_id,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        detail=health.detail or f"default-branch CI health is {health.status}",
    )


def _complete_pr_created_without_merge(
    *,
    runner: Runner,
    working: RunContext,
    resume: ResumePlan,
    ensured_status: str,
    repo_root: str,
) -> ShipResult:
    _write_terminal_finalize_if_terminal(ctx=working, result=Outcome.OK, step="")
    _write_ship_state(
        working,
        phase="done",
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
        terminal_outcome=Outcome.OK,
    )
    return reconcile_committed_stalled_summary_if_recovered(
        runner=runner,
        ctx=working,
        cwd=repo_root,
        counters=_resume_reconciliation_counters(resume),
    ) or ShipResult(
        Outcome.OK,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        detail=ensured_status,
    )


def _merge_pr_after_log_reconciliation(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
    base_ref: str,
    counters: ShipReconciliationCounters,
) -> merge.MergeResult | ShipResult:
    _breadcrumb(step="merge")
    main_health_terminal = _premerge_main_health_gate(
        runner=runner,
        working=working,
        repo_root=repo_root,
        base_ref=base_ref,
        counters=counters,
    )
    if main_health_terminal is not None:
        return main_health_terminal
    reconciliation = reconcile_committed_stalled_summary_if_recovered(
        runner=runner,
        ctx=working,
        cwd=repo_root,
        counters=counters,
    )
    if reconciliation is not None:
        return reconciliation
    return merge.merge_pr(runner=runner, ctx=working, cwd=repo_root, post_flush=False)


def _review_required_merge_state_detail(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
) -> str:
    if working.pr_number is None:
        return ""
    try:
        merge_state = gh.pr_merge_state(
            runner,
            working.pr_number,
            repo=working.repo,
            cwd=repo_root,
        ).merge_state_status.strip()
    except ShipError:
        return ""
    if not merge_state:
        return ""
    return f" (mergeStateStatus={merge_state})"


def _ci_not_ready_review_required_result(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
    original_error: str,
) -> merge.MergeResult | None:
    if not working.no_admin_fallback:
        return None
    review_decision = gh.pr_review_decision(
        runner,
        working.pr_number or 0,
        repo=working.repo,
        cwd=repo_root,
    )
    if review_decision != "REVIEW_REQUIRED":
        return None
    merge_state_detail = _review_required_merge_state_detail(
        runner=runner,
        working=working,
        repo_root=repo_root,
    )
    return merge.MergeResult(
        result=config.MERGE_RESULT_REVIEW_REQUIRED,
        error=(
            f"PR requires approving review{merge_state_detail}: "
            f"approve the PR or merge manually with --admin. "
            f"Original: {original_error}"
        ),
    )


def _resume_done_result(
    *,
    runner: Runner,
    ctx: RunContext,
    resume: ResumePlan,
    repo_root: str,
) -> ShipResult:
    done_ctx = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
    _write_terminal_finalize_if_terminal(ctx=done_ctx, result=Outcome.OK, step="done")
    return reconcile_committed_stalled_summary_if_recovered(
        runner=runner,
        ctx=done_ctx,
        cwd=repo_root,
        counters=_resume_reconciliation_counters(resume),
        allow_post_merge_skip=True,
    ) or ShipResult(
        Outcome.OK,
        pr_number=resume.pr_number,
        pr_url=resume.pr_url,
        merge_result=resume.merge_result,
        detail="already done",
    )


def run_ship(
    ctx: RunContext,
    *,
    runner: Runner = proc,
    cwd: str | None = None,
) -> ShipResult:
    try:
        repo_root = cwd or str(Path.cwd())
        invalid = _invalid_context_result(ctx)
        if invalid is not None:
            return invalid
        base_ref = "main"
        resume = _resume_plan(ctx=ctx, runner=runner, cwd=repo_root)
        blocked = _blocked_resume_result(resume)
        if blocked is not None:
            return blocked
        if "\n" in ctx.pr_url or "\r" in ctx.pr_url:
            raise Stalled("invalid newline in ship state value: PR_URL")
        if resume.start == "done":
            return _resume_done_result(runner=runner, ctx=ctx, resume=resume, repo_root=repo_root)
        if resume.start == "merged":
            working = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
            merged_reconciliation = reconcile_committed_stalled_summary_if_recovered(
                runner=runner,
                ctx=working,
                cwd=repo_root,
                counters=_resume_reconciliation_counters(resume),
                allow_post_merge_skip=True,
            )
            if merged_reconciliation is not None:
                return merged_reconciliation
            _write_ship_state(
                working,
                phase="postmerge",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            return _ship_postmerge_phase(
                runner=runner,
                working=working,
                cwd=repo_root,
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )

        if resume.start == "fresh":
            fresh_context = _hydrate_fresh_context(ctx=ctx, resume=resume)
            # Upfront local lint/tests phase removed by request: open the PR
            # immediately and let CI surface failures (no pre-PR `make py-test`
            # / relevant-checks run). The post-CI fix path is unaffected; only
            # this fresh-run pre-PR checks gate is skipped.
            _write_ship_state(
                fresh_context,
                phase="pr-prep",
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
            _breadcrumb(step="pr-prep", detail="postbump/Flush+Push")
            preflight: finalize.PostbumpPreflight = finalize.postbump_preflight(runner=runner, ctx=fresh_context, cwd=repo_root)
            if not preflight.ok:
                postbump = finalize.FinalizeResult(Outcome.STALLED, preflight.status, preflight.detail)
            else:
                refresh: run_logs.RefreshSkip = run_logs.flush_logs_pre(runner=runner, ctx=fresh_context.with_(state_file=None), cwd=repo_root)
                if refresh.skipped and refresh.reason not in config.REFRESH_SKIP_MERGE_OK:
                    _breadcrumb(step="warning", detail=f"postbump refresh skipped: {refresh.reason}")
                postbump = finalize.postbump(runner=runner, ctx=fresh_context, cwd=repo_root)
            if postbump.outcome is not Outcome.OK:
                postbump_ctx = fresh_context.with_(
                    stall_tracking=postbump.outcome is Outcome.STALLED,
                    stall_step=postbump.status if postbump.outcome is Outcome.STALLED else "",
                )
                conflict_files = getattr(postbump, "conflict_files", "")
                if postbump.outcome is Outcome.STALLED and conflict_files:
                    _write_phase14_flag(
                        fresh_context.tmpdir, reason="postbump-rebase-conflict"
                    )
                    _write_ship_state(
                        postbump_ctx,
                        phase="rebase",
                        iteration=resume.iteration,
                        rebase_count=resume.rebase_count,
                        fix_attempts=resume.fix_attempts,
                        transient_retries=resume.transient_retries,
                        resume_phase=config.SHIP_PR_RRR_RESUME_PHASE,
                        caller_kind=config.SHIP_PR_PRE_PUSH_CALLER_KIND,
                        extra_fields={"CONFLICT_FILES": str(conflict_files)},
                    )
                else:
                    _write_terminal_finalize_if_terminal(
                        ctx=postbump_ctx, result=postbump.outcome, step=postbump.status
                    )
                    _write_ship_state(
                        postbump_ctx,
                        phase=postbump.status,
                        iteration=resume.iteration,
                        rebase_count=resume.rebase_count,
                        fix_attempts=resume.fix_attempts,
                        transient_retries=resume.transient_retries,
                        terminal_outcome=postbump.outcome,
                    )
                return ShipResult(postbump.outcome, detail=postbump.detail or postbump.status)

            tmp_path = Path(fresh_context.tmpdir)
            for manifest in (
                tmp_path / "manifest-raw.json",
                tmp_path / "manifest.json",
                Path(fresh_context.manifest_path) if fresh_context.manifest_path else None,
            ):
                if manifest and manifest.is_file():
                    with suppress(Exception):
                        _ = file_oos.materialize_manifest_oos(manifest, tmp_path)
                    break

            security_sidecar = tmp_path / "security-oos-observations.md"
            if (
                not fresh_context.forked_target
                and not fresh_context.repo_unavailable
                and security_sidecar.is_file()
                and security_sidecar.stat().st_size > 0
            ):
                return ShipResult(
                    Outcome.NEEDS_USER_INPUT, needs_user_reason="oos-filing"
                )

            pr_context = fresh_context
        else:
            pr_context = _hydrate_resume_context(ctx=ctx, resume=resume)

        _write_ship_state(
            pr_context,
            phase="invariants-assessment",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        invariants_gate = _invariants_gate_before_pr(
            runner=runner,
            pr_context=pr_context,
            repo_root=repo_root,
            base_ref=base_ref,
            resume=resume,
            flush_outcome=True,
        )
        if invariants_gate.needs_assessment:
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="architectural-invariants-assessment",
                detail=invariants_gate.detail,
                pr_number=pr_context.pr_number,
                pr_url=pr_context.pr_url,
            )
        if invariants_gate.assessment_kind == "violation":
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="architectural-invariants-violation",
                detail=invariants_gate.note or invariants_gate.detail,
                pr_number=pr_context.pr_number,
                pr_url=pr_context.pr_url,
            )
        _write_ship_state(
            pr_context,
            phase="guidelines-assessment",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        guidelines_gate = _guidelines_gate_before_pr(
            runner=runner,
            pr_context=pr_context,
            repo_root=repo_root,
            base_ref=base_ref,
            resume=resume,
            flush_outcome=True,
        )
        if guidelines_gate.needs_assessment:
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason="architectural-guidelines-assessment",
                detail=guidelines_gate.detail,
                pr_number=pr_context.pr_number,
                pr_url=pr_context.pr_url,
            )
        _write_ship_state(
            pr_context,
            phase="pr-create",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        _breadcrumb(step="pr-create", detail="PR")
        body = _compose_pr_body_for_pr_create(
            pr_context=pr_context,
            architectural_invariants_note=invariants_gate.note,
            architectural_guidelines_note=guidelines_gate.note,
        )
        title = _pr_title(ctx=pr_context, runner=runner, cwd=repo_root)
        ensured: pr.PrResult = pr.ensure_pr(runner=runner, ctx=pr_context, body=body, title=title, cwd=repo_root, base=base_ref)
        working = pr_context.with_(
            pr_number=ensured.number or pr_context.pr_number,
            pr_url=ensured.url or pr_context.pr_url,
            pr_title=title,
            pr_closed=False,
        )
        _write_ship_state(
            working,
            phase="ci-initial" if working.merge and not working.draft else "done",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        if resume.start == "fresh":
            try:
                run_logs.write_final_report_comment(runner=runner, ctx=working)
            except ShipError as exc:
                _breadcrumb(step="warning", detail=str(exc))
        if not working.merge or working.draft or working.forked or working.forked_target or working.repo_unavailable:
            return _complete_pr_created_without_merge(
                runner=runner,
                working=working,
                resume=resume,
                ensured_status=ensured.status,
                repo_root=repo_root,
            )

        post_ensure_terminal = _post_ensure_flush_and_push(runner, working=working, resume=resume, repo_root=repo_root)
        if post_ensure_terminal is not None:
            return post_ensure_terminal

        base_remote = "upstream" if working.forked or working.forked_target else "origin"
        preserve_counters = _merge_loop_uses_resume_counters(resume)
        iteration: int = resume.iteration if preserve_counters else 0
        rebase_count: int = resume.rebase_count if preserve_counters else 0
        fix_attempts: int = resume.fix_attempts if preserve_counters else 0
        transient_retries: int = resume.transient_retries if preserve_counters else 0
        initial_startup_deadline_available = (
            iteration == rebase_count == fix_attempts == transient_retries == 0
        )
        # Head observed by the previous monitor poll. When a loop iteration pushes
        # a new head (CI-fix or rebase) the next monitor expects a fresh CI run; if
        # none starts we must detect it within a bounded window rather than poll the
        # full budget (issue #4867). Seed from durable state on resume so a
        # head-changing push before restart still gets bounded empty-checks grace.
        last_monitored_head = _seed_last_monitored_head(
            ctx=working,
            runner=runner,
            cwd=repo_root,
            fix_attempts=fix_attempts,
        )
        ci_not_ready_guard = _CiNotReadyGuard()
        while True:
            if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:
                return _merge_loop_iteration_cap_stall(
                    runner=runner,
                    working=working,
                    repo_root=repo_root,
                    counters=_MergeLoopCounters(
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                    ),
                )
            _write_ship_state(
                working,
                phase="ci-initial",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
                ci_fix_rebase_pending_head=(git.try_rev_parse(runner, "HEAD", cwd=repo_root) or "")
                if working.ci_fix_rebase_pending
                else "",
                last_monitored_head=last_monitored_head or "",
            )
            phase14_flag = Path(working.tmpdir) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
            if phase14_flag.is_file():
                ci_not_ready_guard.reset()
                rebase_count = _ship_phase14_rebase(
                    runner=runner,
                    working=working,
                    cwd=repo_root,
                    base_remote=base_remote,
                    base_ref=base_ref,
                    phase14_flag=phase14_flag,
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    last_monitored_head=last_monitored_head,
                )
                continue
            pre_monitor_head = last_monitored_head
            current_head = git.try_rev_parse(runner, "HEAD", cwd=repo_root)
            empty_checks_grace, empty_checks_startup_deadline_sec = (
                _empty_checks_params_for_monitor(
                    current_head=current_head,
                    last_monitored_head=last_monitored_head,
                    initial_startup_deadline_available=initial_startup_deadline_available,
                )
            )
            monitor: ci_monitor.MonitorResult = ci_monitor.monitor(
                runner,
                pr=working.pr_number or 0,
                repo=working.repo,
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                base_remote=base_remote,
                base_ref=base_ref,
                empty_checks_grace=empty_checks_grace,
                empty_checks_startup_deadline_sec=empty_checks_startup_deadline_sec,
                ci_fix_rebase_pending=working.ci_fix_rebase_pending,
                cwd=repo_root,
            )
            initial_startup_deadline_available = False
            last_monitored_head = current_head
            monitor_pending = getattr(monitor, "ci_fix_rebase_pending", working.ci_fix_rebase_pending)
            if monitor_pending != working.ci_fix_rebase_pending:
                working = working.with_(ci_fix_rebase_pending=monitor_pending)
                pending_head = git.try_rev_parse(runner, "HEAD", cwd=repo_root) if monitor_pending else ""
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    ci_fix_rebase_pending_head=pending_head or "",
                    last_monitored_head=last_monitored_head or "",
                )
            if monitor.result.outcome is not Outcome.OK:
                persisted = _monitor_persisted_counters(
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    monitor=monitor,
                )
                if (
                    monitor.result.outcome is Outcome.TRANSIENT
                    and persisted[3] >= _PYTHON_TRANSIENT_STALL_ATTEMPT
                    and not working.expected_session_id
                ):
                    _write_terminal_state(
                        ctx=working,
                        result=Outcome.STALLED,
                        step="transient-retry-cap",
                        iteration=persisted[0],
                        rebase_count=persisted[1],
                        fix_attempts=persisted[2],
                        transient_retries=persisted[3],
                        failed_run_id=monitor.failed_run_id or "",
                    )
                    _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                    return ShipResult(
                        Outcome.STALLED,
                        failed_run_id=monitor.failed_run_id or "",
                        pr_number=working.pr_number,
                        pr_url=working.pr_url,
                        detail=monitor.result.detail or "transient retry cap",
                    )
                _bail_ctx = working
                _bail_detail_log = ""
                _bail_step = monitor.result.detail or "ci-monitor"
                if (
                    monitor.result.outcome is Outcome.NEEDS_USER_INPUT
                    and (monitor.result.detail or "").startswith("ci-fix-exhausted")
                ):
                    _bail_ctx = working.with_(final_bail_reason=config.NEEDS_USER_CI_FIX_EXHAUSTED)
                    _bail_detail_log = _write_ci_fix_detail_log(ctx=working, detail=monitor.result.detail or "")
                    _bail_step = "10"
                terminal_last_head: str | None = None
                bounded_empty_checks = (
                    empty_checks_grace > 0 or empty_checks_startup_deadline_sec > 0
                )
                no_checks_stall = (
                    (monitor.result.detail or "") == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
                    and bounded_empty_checks
                )
                if no_checks_stall:
                    terminal_last_head = pre_monitor_head or ""
                    phase14_reason = _no_checks_phase14_reason(
                        runner=runner,
                        working=working,
                        cwd=repo_root,
                    )
                    if phase14_reason:
                        _write_phase14_flag(working.tmpdir, reason=phase14_reason)
                _write_terminal_state(
                    ctx=_bail_ctx,
                    result=monitor.result.outcome,
                    step=_bail_step,
                    iteration=persisted[0],
                    rebase_count=persisted[1],
                    fix_attempts=persisted[2],
                    transient_retries=persisted[3],
                    failed_run_id=monitor.failed_run_id or "",
                    bail_failure_detail_log=_bail_detail_log,
                    last_monitored_head=terminal_last_head,
                )
                # A no-ci-checks-observed stall is recoverable: the main agent
                # re-invokes ship-pr, which may rebase first when the PR merge state
                # is dirty or behind. Publishing a
                # terminal snapshot here would flush a fresh larch-logs commit and
                # push it, moving HEAD and re-triggering CI before checks can attach
                # -- the perpetual stall loop of issue #5186. Skip the snapshot so
                # HEAD stays put and CI converges on a stable head; it is published
                # once the run reaches a genuinely terminal state.
                if not no_checks_stall:
                    _publish_post_pr_terminal_snapshot(runner=runner, ctx=_bail_ctx, cwd=repo_root)
                return _step_result_to_ship(
                    monitor.result,
                    failed_run_id=monitor.failed_run_id or "",
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    default_ledger_phase="ci-initial",
                    default_ledger_failure_detail_log=_bail_detail_log,
                )
            if monitor.action not in {"merge", "already_merged"}:
                ci_not_ready_guard.reset()
                if iteration > config.SHIP_MERGE_LOOP_MAX_ITERATIONS:
                    return _merge_loop_iteration_cap_stall(
                        runner=runner,
                        working=working,
                        repo_root=repo_root,
                        counters=_MergeLoopCounters(
                            iteration=iteration,
                            rebase_count=rebase_count,
                            fix_attempts=fix_attempts,
                            transient_retries=transient_retries,
                        ),
                    )
                if monitor.goto_rebase:
                    rebase_phase = _ship_rebase_phase(
                        runner=runner,
                        working=working,
                        cwd=repo_root,
                        base_remote=base_remote,
                        base_ref=base_ref,
                        iteration=iteration,
                        rebase_count=rebase_count,
                        fix_attempts=fix_attempts,
                        transient_retries=transient_retries,
                        variant=ShipRebaseVariant.GOTO_REBASE,
                    )
                    rebase_count = rebase_phase.rebase_count
                    if rebase_phase.terminal is not None:
                        return rebase_phase.terminal
                    refreshed = _refresh_guidelines_gate_after_rebase(
                        runner=runner,
                        pr_context=working,
                        repo_root=repo_root,
                        base_ref=base_ref,
                        resume=resume,
                    )
                    if refreshed is not None:
                        return refreshed
                if monitor.transient_rerun_attempted:
                    transient_retries += 1
                if monitor.action == "wait" or monitor.goto_rebase:
                    iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    last_monitored_head=last_monitored_head or "",
                )
                continue

            merged_or_terminal = _merge_pr_after_log_reconciliation(
                runner=runner,
                working=working,
                repo_root=repo_root,
                base_ref=base_ref,
                counters=ShipReconciliationCounters(iteration, rebase_count, fix_attempts, transient_retries),
            )
            if isinstance(merged_or_terminal, ShipResult):
                return merged_or_terminal
            merged = merged_or_terminal
            if merged.result == config.MERGE_RESULT_CI_NOT_READY:
                review_required_result = _ci_not_ready_review_required_result(
                    runner=runner,
                    working=working,
                    repo_root=repo_root,
                    original_error=merged.error,
                )
                if review_required_result is not None:
                    merged = review_required_result
                else:
                    iteration, ci_not_ready_stall = _handle_merge_ci_not_ready(
                        runner=runner,
                        working=working,
                        repo_root=repo_root,
                        counters=_MergeLoopCounters(
                            iteration=iteration,
                            rebase_count=rebase_count,
                            fix_attempts=fix_attempts,
                            transient_retries=transient_retries,
                        ),
                        guard=ci_not_ready_guard,
                    )
                    if ci_not_ready_stall is not None:
                        return ci_not_ready_stall
                    continue
            if merged.result == config.MERGE_RESULT_MAIN_ADVANCED:
                ci_not_ready_guard.reset()
                rebase_phase = _ship_rebase_phase(
                    runner=runner,
                    working=working,
                    cwd=repo_root,
                    base_remote=base_remote,
                    base_ref=base_ref,
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                    variant=ShipRebaseVariant.MAIN_ADVANCED,
                )
                rebase_count = rebase_phase.rebase_count
                if rebase_phase.terminal is not None:
                    return rebase_phase.terminal
                refreshed = _refresh_guidelines_gate_after_rebase(
                    runner=runner,
                    pr_context=working,
                    repo_root=repo_root,
                    base_ref=base_ref,
                    resume=resume,
                )
                if refreshed is not None:
                    return refreshed
                iteration += 1
                _write_ship_state(
                    working,
                    phase="ci-initial",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                continue
            if merged.result == config.MERGE_RESULT_REVIEW_REQUIRED:
                _write_terminal_state(
                    ctx=working.with_(
                        stall_tracking=True,
                        stall_step="merge",
                        final_bail_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    ),
                    result=Outcome.NEEDS_USER_INPUT,
                    step="merge",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(
                    runner=runner,
                    ctx=working.with_(
                        stall_tracking=True,
                        stall_step="merge",
                        final_bail_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    ),
                    cwd=repo_root,
                )
                return ShipResult(
                    Outcome.NEEDS_USER_INPUT,
                    needs_user_reason=config.NEEDS_USER_REVIEW_REQUIRED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    detail=merged.error or "PR requires approving review",
                )
            pr_closed = merged.result in config.POST_MERGE_MERGE_RESULTS
            working = working.with_(
                merge_result=merged.result,
                pr_closed=pr_closed,
            )
            _write_ship_state(
                working,
                phase="postmerge" if pr_closed else "merge",
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
            if merged.result == config.MERGE_RESULT_ERROR or merged.result not in config.POST_MERGE_MERGE_RESULTS:
                merge_stall_detail = (
                    merged.error
                    if merged.result == config.MERGE_RESULT_ERROR
                    else merged.error or f"merge did not complete: {merged.result}"
                )
                _write_terminal_state(
                    ctx=working.with_(stall_tracking=True, stall_step="merge"),
                    result=Outcome.STALLED,
                    step="merge",
                    iteration=iteration,
                    rebase_count=rebase_count,
                    fix_attempts=fix_attempts,
                    transient_retries=transient_retries,
                )
                _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
                return ShipResult(
                    Outcome.STALLED,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=merged.result,
                    detail=merge_stall_detail,
                )
            return _ship_postmerge_phase(
                runner=runner,
                working=working,
                cwd=repo_root,
                iteration=iteration,
                rebase_count=rebase_count,
                fix_attempts=fix_attempts,
                transient_retries=transient_retries,
            )
    except (NeedsUserInput, ShipError, Stalled, TransientNetworkError) as exc:
        result = _error_to_result(exc)
        if result.outcome is Outcome.STALLED and not isinstance(exc, PrePushConflictHandoff):
            latest_ctx = _context_with_state_overlay(ctx)
            if "\n" in latest_ctx.pr_url or "\r" in latest_ctx.pr_url:
                latest_ctx = latest_ctx.with_(pr_url="")
            step = latest_ctx.stall_step or _slug_from_detail(result.detail)
            _write_terminal_state(ctx=latest_ctx.with_(stall_tracking=True, stall_step=step), result=Outcome.STALLED, step=step)
        return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Python ship-pr driver")
    _ = parser.add_argument("--branch")
    _ = parser.add_argument("--issue")
    _ = parser.add_argument("--repo")
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--tmpdir")
    _ = parser.add_argument("--manifest-path")
    _ = parser.add_argument("--state-file")
    _ = parser.add_argument("--tool-label")
    _ = parser.add_argument("--merge")
    _ = parser.add_argument("--draft")
    _ = parser.add_argument("--forked")
    _ = parser.add_argument("--repo-unavailable")
    _ = parser.add_argument("--no-admin-fallback")
    _ = parser.add_argument("--no-logs-commit", nargs="?", const="true", default=None)
    _ = parser.add_argument("--expected-session-id")
    _ = parser.add_argument("--expected-tmpdir-basename-prefix")
    return parser


def _first_present(*values: object) -> str:
    for value in values:
        if value is None:
            continue
        if isinstance(value, int):
            if value != 0:
                return str(value)
            continue
        text = str(value)
        if text:
            return text
    return ""


def _slug_from_detail(detail: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "-", detail.strip().lower()).strip("-")
    return slug[:80] or "stalled"


def _fill_if_empty(data: dict[str, str], key: str, *values: object) -> None:  # lint-keyword-only: ok *values vararg prevents bare-star separator
    if data.get(key):
        return
    value = _first_present(*values)
    if value:
        data[key] = value


def _persist_stall_metadata_if_needed(*, ctx: RunContext, result: ShipResult, tmpdir: Path) -> None:
    if result.outcome is not Outcome.STALLED:
        return
    if _is_active_pre_push_handoff(ctx):
        return
    if not _tmpdir_under_allowed_root(str(tmpdir)):
        return
    path = tmpdir / "finalize-state.sh"
    try:
        data: dict[str, str] = finalize.read_finalize_state(path)
        if _truthy(data.get("STALL_TRACKING", "")):
            return
        state = _state_file_kv(ctx.state_file)
        _fill_if_empty(data, "BRANCH_NAME", state.get("BRANCH_NAME"), ctx.branch)
        _fill_if_empty(data, "ISSUE_NUMBER", state.get("ISSUE_NUMBER"), ctx.issue_number, ctx.issue)
        _fill_if_empty(data, "REPO", state.get("REPO"), ctx.repo)
        _fill_if_empty(data, "RUN_ID", state.get("RUN_ID"), ctx.run_id)
        _fill_if_empty(data, "PR_NUMBER", result.pr_number, state.get("PR_NUMBER"), ctx.pr_number)
        state_pr_url = state.get("PR_URL", "")
        if state_pr_url and not _valid_pr_url(state_pr_url):
            state_pr_url = ""
        _fill_if_empty(data, "PR_URL", result.pr_url, state_pr_url, ctx.pr_url)
        _fill_if_empty(data, "PR_TITLE", state.get("PR_TITLE"), ctx.pr_title)
        _fill_if_empty(data, "MERGE_RESULT", result.merge_result, state.get("MERGE_RESULT"), ctx.merge_result)
        _fill_if_empty(data, "FORKED_TARGET", state.get("FORKED_TARGET"), "true" if ctx.forked else "false")
        _fill_if_empty(data, "REPO_UNAVAILABLE", state.get("REPO_UNAVAILABLE"), "true" if ctx.repo_unavailable else "false")
        _fill_if_empty(data, "DRAFT", state.get("DRAFT"), "true" if ctx.draft else "false")
        _fill_if_empty(data, "MERGE", state.get("MERGE"), "true" if ctx.merge else "false")
        data["STALL_TRACKING"] = "true"
        _fill_if_empty(data, "STALL_STEP", state.get("STALL_STEP"), ctx.stall_step, _slug_from_detail(result.detail))
        finalize.write_finalize_state_merged(path=path, data=data)
    except Exception as exc:
        logging_util.BreadcrumbWriter().emit(f"ship.py: stall metadata gap-fill failed: {exc}")


def _ctx_from_args(args: argparse.Namespace) -> RunContext:
    env_ctx = RunContext.from_env()
    changes: dict[str, object] = {}
    for arg_name, field_name in (
        ("branch", "branch"),
        ("issue", "issue"),
        ("issue", "issue_number"),
        ("repo", "repo"),
        ("run_id", "run_id"),
        ("tmpdir", "tmpdir"),
        ("manifest_path", "manifest_path"),
        ("state_file", "state_file"),
        ("tool_label", "tool_label"),
        ("expected_session_id", "expected_session_id"),
        ("expected_tmpdir_basename_prefix", "expected_tmpdir_basename_prefix"),
    ):
        value = getattr(args, arg_name)
        if value not in (None, ""):
            changes[field_name] = value
    for arg_name, field_name in (
        ("merge", "merge"),
        ("draft", "draft"),
        ("forked", "forked"),
        ("repo_unavailable", "repo_unavailable"),
        ("no_admin_fallback", "no_admin_fallback"),
    ):
        value = getattr(args, arg_name)
        if value is not None:
            changes[field_name] = str(value).strip().lower() in {"1", "true", "yes", "on"}
    if args.no_logs_commit is not None:
        changes["no_logs_commit"] = str(args.no_logs_commit).strip().lower() in {"1", "true", "yes", "on"}
    ctx = env_ctx.with_(**changes)
    if ctx.state_file:
        ctx = _context_with_state_overlay(ctx)
    return ctx


def main(argv: list[str] | None = None) -> int:
    ctx = RunContext.from_env(env={})
    result: ShipResult
    parser = build_parser()
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        if code == 0:
            return 0
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"argparse failed with exit {code}")
        with suppress(Exception):
            emit_result(ctx=ctx, result=result)
        return config.OUTCOME_EXIT_MAP[Outcome.INTERNAL_ERROR]
    try:
        ctx = _ctx_from_args(args)
        if _tmpdir_under_allowed_root(ctx.tmpdir):
            os.environ[config.ENV_IMPLEMENT_TMPDIR] = ctx.tmpdir
            logging_util.quiet_init(argv0="ship.py")
        result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    except Exception as exc:  # top-level contract envelope
        logging_util.BreadcrumbWriter().emit(
            f"ship.py: internal error\n{traceback.format_exc()}",
        )
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"{type(exc).__name__}: {exc}")
    _persist_stall_metadata_if_needed(ctx=ctx, result=result, tmpdir=Path(ctx.tmpdir))
    emit_result(ctx=ctx, result=result)
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
