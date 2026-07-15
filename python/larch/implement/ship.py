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
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch import io as larch_io
from larch.core import architectural_guidelines
from larch.core.assessment_kind import AssessmentKind, GUIDELINES, INVARIANTS
from larch.implement import ci_monitor
from larch.implement import ci
from larch.implement import main_health
from larch.implement import scope_disposition
from larch.core import config
from larch.issue import file_oos
from larch.state import finalize
from larch import io as larch_io
from larch.git import gh
from larch.git import git
from larch.core import logging_util
from larch.report import progress_file
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
    _progress_note,
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
    validate_ship_result_env_path,
)
from larch.implement.ship_guidelines import (
    GuidelinesGateResult,
    GuidelinesShipOutcome,
    InvariantsGateResult,
    InvariantsShipOutcome,
    _pin_and_load_guidelines_note,
    _clear_ship_outcome_sidecar,
    guideline_deviation_exception_present,
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


@dataclass(frozen=True)
class _AssessmentGatePair:
    invariants: InvariantsGateResult
    guidelines: GuidelinesGateResult


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


def _normalize_hook_fixed_bytes(content: bytes) -> bytes:
    try:
        text = content.decode("utf-8")
    except UnicodeDecodeError:
        return content
    lines: list[str] = [line.rstrip() for line in text.splitlines()]
    if not lines:
        return b""
    return ("\n".join(lines) + "\n").encode("utf-8")


def _committed_outcome_matches(
    *, ctx: RunContext, cwd: str, kind: AssessmentKind
) -> bool:
    run_id = run_logs.effective_run_id(ctx)
    if not run_id:
        return False
    sidecar = Path(ctx.tmpdir) / kind.ship_outcome_sidecar
    committed = Path(cwd) / "larch-logs" / "implement" / run_id / kind.ship_outcome_sidecar
    try:
        return (
            sidecar.is_file()
            and committed.is_file()
            and _normalize_hook_fixed_bytes(sidecar.read_bytes())
            == _normalize_hook_fixed_bytes(committed.read_bytes())
        )
    except OSError:
        return False


def _pre_pr_reentry_phase(resume: ResumePlan) -> str:
    if resume.start == "fresh":
        return "pr-prep"
    return config.SHIP_ROUTE_ACTION_ASSESSMENTS


def _destall_pre_pr_reentry(
    *,
    ctx: RunContext,
    resume: ResumePlan,
    runner: Runner,
    repo_root: str,
) -> RunContext | ShipResult:
    _ = (runner, repo_root)
    if resume.start not in {"fresh", "pre-pr-compose", "open-pr"}:
        return ctx
    if not ctx.state_file:
        return ctx
    prior_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="PHASE")
    if prior_phase != "stalled":
        return ctx
    tmpdir = Path(ctx.tmpdir)
    if not _tmpdir_under_allowed_root(ctx.tmpdir):
        return ShipResult(Outcome.STALLED, detail="invalid tmpdir")
    finalize_state = tmpdir / "finalize-state.sh"
    if finalize_state.exists() or finalize_state.is_symlink():
        try:
            resolved = finalize_state.resolve(strict=False)
            _ = resolved.relative_to(tmpdir.resolve(strict=False))
        except (OSError, ValueError):
            return ShipResult(Outcome.STALLED, detail="invalid finalize-state path")
        if finalize_state.is_symlink() or not finalize_state.is_file():
            return ShipResult(Outcome.STALLED, detail="non-regular finalize-state on pre-PR reentry")
        try:
            finalize_state.unlink()
        except OSError as exc:
            return ShipResult(Outcome.STALLED, detail=f"cannot remove stale finalize-state: {exc}")
    phase = _pre_pr_reentry_phase(resume)
    reset_ctx = ctx.with_(stall_tracking=False, stall_step="")
    _write_ship_state(
        reset_ctx,
        phase=phase,
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
    )
    _breadcrumb(step="pre-pr-reentry", detail=f"de-terminalized prior phase {prior_phase} -> {phase}")
    return reset_ctx


def _flush_guideline_outcome_before_pr(
    *,
    runner: Runner,
    ctx: RunContext,
    cwd: str,
    resume: ResumePlan,
    require_invariant_match: bool = False,
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
    if refresh.reason == config.REFRESH_SKIP_RUN_LOG_INCOMPLETE:
        _breadcrumb(step="warning", detail=f"guideline outcome refresh skipped: {reason}")
        return
    if (
        refresh.reason == config.REFRESH_SKIP_VOLATILE_ONLY
        and _committed_outcome_matches(ctx=ctx, cwd=cwd, kind=GUIDELINES)
        and (
            not require_invariant_match
            or _committed_outcome_matches(ctx=ctx, cwd=cwd, kind=INVARIANTS)
        )
    ):
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
        implement_tmpdir=Path(pr_context.tmpdir) if pr_context.tmpdir else None,
        repo_root=_persisted_repo_root_for_pr(pr_context),
        manifest_path=Path(pr_context.manifest_path) if pr_context.manifest_path else None,
    )


def _persisted_repo_root_for_pr(pr_context: RunContext) -> Path:
    if pr_context.tmpdir:
        persisted = progress_file.resolve_persisted_repo_root(tmpdir=pr_context.tmpdir)
        if persisted is not None:
            return persisted
        if scope_disposition.load_coverage(Path(pr_context.tmpdir)) is not None:
            raise ShipError("persisted repository root is required for PR coverage validation")
    return Path.cwd().resolve()


def _assessment_gate_before_pr(
    *, runner: Runner, pr_context: RunContext, repo_root: str, base_ref: str,
    resume: ResumePlan, kind: AssessmentKind, flush_outcome: bool = True,
    compose_snapshot_factory: Callable[[], architectural_guidelines.ComposeAssessmentSnapshot] | None = None,
) -> GuidelinesGateResult | InvariantsGateResult:
    compose_head_sha = git.try_rev_parse(runner, "HEAD", cwd=repo_root) or ""
    compose_base_ref = (
        f"{'upstream' if pr_context.forked or pr_context.forked_target else 'origin'}/{base_ref}"
    )
    _clear_ship_outcome_sidecar(implement_tmpdir=pr_context.tmpdir, kind=kind)
    if kind.is_invariant:
        invariant_file = architectural_guidelines.read_invariants(repo_root=repo_root)
        if invariant_file.status == "absent":
            result: GuidelinesGateResult | InvariantsGateResult = InvariantsGateResult(
                invariants_status="absent", reason=kind.absent_reason
            )
        elif invariant_file.status == "invalid":
            result = InvariantsGateResult(
                invariants_status="invalid", reason=kind.invalid_reason,
                detail=invariant_file.warning,
            )
        elif not invariant_file.content.strip():
            result = InvariantsGateResult(
                invariants_status="present", assessment_kind="clean", reason=kind.empty_reason
            )
        else:
            result = load_or_prepare_invariants_note(
                implement_tmpdir=pr_context.tmpdir, head_sha=compose_head_sha,
                base_ref=compose_base_ref, repo_root=repo_root,
                forked_target=pr_context.forked or pr_context.forked_target,
                compose_snapshot_factory=compose_snapshot_factory,
            )
    else:
        result = load_or_prepare_guidelines_note(
            implement_tmpdir=pr_context.tmpdir, head_sha=compose_head_sha,
            base_ref=compose_base_ref, repo_root=repo_root,
            forked_target=pr_context.forked or pr_context.forked_target,
            compose_snapshot_factory=compose_snapshot_factory,
        )
    if result.needs_assessment:
        return result
    if kind.is_invariant and not compose_head_sha and not result.note:
        return result
    if not flush_outcome:
        return result
    outcome: GuidelinesShipOutcome | InvariantsShipOutcome | None
    try:
        if kind.is_invariant:
            assert isinstance(result, InvariantsGateResult)
            outcome = write_invariant_ship_outcome(
                implement_tmpdir=pr_context.tmpdir, result=result,
                head_sha=compose_head_sha, base_ref=compose_base_ref,
            )
        else:
            assert isinstance(result, GuidelinesGateResult)
            outcome = write_guideline_ship_outcome(
                implement_tmpdir=pr_context.tmpdir, result=result,
                head_sha=compose_head_sha, base_ref=compose_base_ref,
            )
    except OSError as exc:
        if pr_context.no_logs_commit:
            _breadcrumb(
                step="warning",
                detail=(
                    f"{kind.singular} outcome sidecar write skipped: "
                    f"{logging_util.sanitize_diagnostic_line(str(exc))}"
                ),
            )
            return result
        step = f"pr-create-{kind.singular}-outcome-write"
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step=step),
            result=Outcome.STALLED, step=step, iteration=resume.iteration,
            rebase_count=resume.rebase_count, fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        detail = logging_util.sanitize_diagnostic_line(str(exc))
        raise Stalled(
            f"architectural-{kind.key} outcome sidecar write failed: {detail}"
        ) from exc
    if pr_context.no_logs_commit:
        return result
    if kind.flush_outcome:
        _flush_guideline_outcome_before_pr(
            runner=runner, ctx=pr_context, cwd=repo_root, resume=resume
        )
    # A dropped outcome (any reason) cannot proceed to PR creation; stall rather
    # than replay an identical reship. The legacy `unavailable` exemption was
    # removed because the operator routing it relied on no longer exists (#7216).
    if outcome is not None and outcome.outcome == "dropped":
        step = f"pr-create-{kind.singular}-outcome-dropped"
        _write_terminal_state(
            ctx=pr_context.with_(stall_tracking=True, stall_step=step),
            result=Outcome.STALLED, step=step, iteration=resume.iteration,
            rebase_count=resume.rebase_count, fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        raise Stalled(f"architectural-{kind.key} outcome dropped: {outcome.reason}")
    return result


def _invariants_gate_before_pr(
    *, runner: Runner, pr_context: RunContext, repo_root: str, base_ref: str,
    resume: ResumePlan, flush_outcome: bool = True,
    compose_snapshot_factory: Callable[[], architectural_guidelines.ComposeAssessmentSnapshot] | None = None,
) -> InvariantsGateResult:
    result = _assessment_gate_before_pr(
        runner=runner, pr_context=pr_context, repo_root=repo_root, base_ref=base_ref,
        resume=resume, flush_outcome=flush_outcome,
        compose_snapshot_factory=compose_snapshot_factory, kind=INVARIANTS,
    )
    assert isinstance(result, InvariantsGateResult)
    return result


def _guidelines_gate_before_pr(
    *, runner: Runner, pr_context: RunContext, repo_root: str, base_ref: str,
    resume: ResumePlan, flush_outcome: bool = True,
    compose_snapshot_factory: Callable[[], architectural_guidelines.ComposeAssessmentSnapshot] | None = None,
) -> GuidelinesGateResult:
    result = _assessment_gate_before_pr(
        runner=runner, pr_context=pr_context, repo_root=repo_root, base_ref=base_ref,
        resume=resume, flush_outcome=flush_outcome,
        compose_snapshot_factory=compose_snapshot_factory, kind=GUIDELINES,
    )
    assert isinstance(result, GuidelinesGateResult)
    return result


def _compose_snapshot_factory(
    *,
    runner: Runner,
    pr_context: RunContext,
    repo_root: str,
) -> Callable[[], architectural_guidelines.ComposeAssessmentSnapshot]:
    snapshot: architectural_guidelines.ComposeAssessmentSnapshot | None = None
    snapshot_error: str = ""
    expected_head_sha = git.try_rev_parse(runner, "HEAD", cwd=repo_root) or ""
    forked_target = pr_context.forked or pr_context.forked_target

    def materialize() -> architectural_guidelines.ComposeAssessmentSnapshot:
        nonlocal snapshot, snapshot_error
        if snapshot is not None:
            return snapshot
        if snapshot_error:
            raise RuntimeError(snapshot_error)
        try:
            snapshot = architectural_guidelines.materialize_compose_assessment_snapshot(
                repo_root=repo_root,
                forked_target=forked_target,
                expected_head_sha=expected_head_sha,
            )
        except (OSError, RuntimeError) as exc:
            snapshot_error = str(exc).replace("\n", " ")
            raise RuntimeError(snapshot_error) from exc
        return snapshot

    return materialize


def _combined_assessment_result(
    *,
    gates: _AssessmentGatePair,
    pr_context: RunContext,
) -> ShipResult | None:
    if gates.invariants.assessment_kind == "violation":
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="architectural-invariants-violation",
            detail=gates.invariants.note or gates.invariants.detail,
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    assessment_kinds: list[str] = []
    if gates.invariants.needs_assessment:
        assessment_kinds.append(config.ASSESSMENT_KIND_INVARIANTS)
    if gates.guidelines.needs_assessment:
        assessment_kinds.append(config.ASSESSMENT_KIND_GUIDELINES)
    if assessment_kinds:
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_ARCHITECTURAL_ASSESSMENTS,
            detail=",".join(assessment_kinds),
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    # A guideline deviation is accepted only when its durable note carries the
    # documented-exception block recorded by the fix ladder. A bare deviation
    # (ladder did not run or declined without recording) fails closed: the run
    # must not proceed to PR (#7193 item 6).
    if (
        gates.guidelines.assessment_kind == config.ASSESSMENT_OUTCOME_DEVIATION
        and not guideline_deviation_exception_present(gates.guidelines.note)
    ):
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason="architectural-guideline-deviation-unresolved",
            detail=gates.guidelines.note or gates.guidelines.detail,
            pr_number=pr_context.pr_number,
            pr_url=pr_context.pr_url,
        )
    return None


def _compose_assessment_gate_before_pr(
    *,
    runner: Runner,
    pr_context: RunContext,
    repo_root: str,
    base_ref: str,
    resume: ResumePlan,
) -> tuple[_AssessmentGatePair, ShipResult | None]:
    compose_snapshot_factory = _compose_snapshot_factory(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
    )
    invariants_gate = _invariants_gate_before_pr(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
        base_ref=base_ref,
        resume=resume,
        flush_outcome=True,
        compose_snapshot_factory=compose_snapshot_factory,
    )
    if invariants_gate.assessment_kind == "violation":
        gates = _AssessmentGatePair(
            invariants=invariants_gate,
            guidelines=GuidelinesGateResult(),
        )
        return gates, _combined_assessment_result(gates=gates, pr_context=pr_context)
    guidelines_gate = _guidelines_gate_before_pr(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
        base_ref=base_ref,
        resume=resume,
        flush_outcome=True,
        compose_snapshot_factory=compose_snapshot_factory,
    )
    gates = _AssessmentGatePair(invariants=invariants_gate, guidelines=guidelines_gate)
    assessment_result = _combined_assessment_result(gates=gates, pr_context=pr_context)
    return gates, assessment_result


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
    _write_ship_state(
        pr_context,
        phase=config.SHIP_ROUTE_ACTION_ASSESSMENTS,
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
    )
    gates, assessment_result = _compose_assessment_gate_before_pr(
        runner=runner,
        pr_context=pr_context,
        repo_root=repo_root,
        base_ref=base_ref,
        resume=resume,
    )
    if assessment_result is not None:
        return assessment_result
    body = _compose_pr_body_for_pr_create(
        pr_context=pr_context,
        architectural_invariants_note=gates.invariants.note,
        architectural_guidelines_note=gates.guidelines.note,
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


def _missing_main_health_sidecar_result(
    *,
    ctx: RunContext,
    step: str,
    counters: ShipReconciliationCounters,
    failed_run_id: str = "",
) -> ShipResult:
    detail = "missing main-health.env; cannot verify default-branch CI health"
    _write_terminal_state(
        ctx=ctx.with_(stall_tracking=True, stall_step=step),
        result=Outcome.STALLED,
        step=step,
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        failed_run_id=failed_run_id,
    )
    return ShipResult(
        Outcome.STALLED,
        failed_run_id=failed_run_id,
        pr_number=ctx.pr_number,
        pr_url=ctx.pr_url,
        merge_result=ctx.merge_result,
        detail=detail,
    )


def _main_health_sidecar_bootstrapped(tmpdir: str) -> bool:
    base = Path(tmpdir)
    return (base / "preflight-tmpdir.env").is_file()


def _resolve_premerge_main_health_sha(*, runner: Runner, repo_root: str, base_ref: str) -> str:
    fetch = git.fetch(runner, "origin", base_ref, cwd=repo_root)
    if fetch.returncode != 0:
        return ""
    return git.try_rev_parse(runner, f"origin/{base_ref}", cwd=repo_root) or ""


def _merged_pr_commit_sha(*, runner: Runner, working: RunContext, cwd: str) -> str:
    if working.pr_number is None:
        return ""
    result = gh.pr_view_field_read(
        runner,
        working.pr_number,
        "mergeCommit",
        repo=working.repo,
        cwd=cwd,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return ""
    try:
        loaded: object = json.loads(result.stdout)
    except json.JSONDecodeError:
        return ""
    if not isinstance(loaded, dict):
        return ""
    merge_commit = cast("dict[str, object]", loaded).get("mergeCommit")
    if not isinstance(merge_commit, dict):
        return ""
    oid = cast("dict[str, object]", merge_commit).get("oid")
    return str(oid).strip() if isinstance(oid, str) else ""


def _postmerge_main_health_gate(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    counters: ShipReconciliationCounters,
) -> ShipResult | None:
    main_health_path = Path(working.tmpdir) / "main-health.env"
    if not main_health_path.is_file():
        if not _main_health_sidecar_bootstrapped(working.tmpdir):
            return None
        return _missing_main_health_sidecar_result(
            ctx=working.with_(stall_tracking=True, stall_step="postmerge-push-watch"),
            step="postmerge-push-watch",
            counters=counters,
        )
    _write_ship_state(
        working,
        phase="postmerge-push-watch",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
    )
    merged_head = _merged_pr_commit_sha(runner=runner, working=working, cwd=cwd)
    if not merged_head:
        fetch = git.fetch(runner, "origin", "main", cwd=cwd)
        if fetch.returncode != 0:
            detail = "post-merge push watch could not refresh origin/main"
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
        merged_head = git.try_rev_parse(runner, "origin/main", cwd=cwd)
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
                skip_flap_check=counters.transient_retries > 0,
            ),
            timeout=config.MAIN_HEALTH_WAIT_TIMEOUT_SEC,
            interval=config.MAIN_HEALTH_WAIT_POLL_INTERVAL_SEC,
        ),
    )
    health = waited.health
    if health.status in {"pass", "skip"}:
        return None
    if health.status == "fail":
        repair_head = health.head_sha or merged_head
        detail = health.detail
        if health.failed_run_id and counters.transient_retries < config.MAIN_HEALTH_MAX_TRANSIENT_RETRIES:
            rerun = ci_monitor.rerun_failed(
                runner,
                run_id=health.failed_run_id,
                repo=working.repo,
                cwd=cwd,
            )
            if rerun.submitted:
                _write_ship_state(
                    working,
                    phase="postmerge-push-watch",
                    iteration=counters.iteration,
                    rebase_count=counters.rebase_count,
                    fix_attempts=counters.fix_attempts,
                    transient_retries=counters.transient_retries + 1,
                    extra_fields={
                        "MAIN_REPAIR_RUN_ID": health.failed_run_id,
                        "MAIN_REPAIR_HEAD": repair_head,
                        "MAIN_HEALTH_HEAD_SHA": repair_head,
                        "MAIN_HEALTH_REPAIR_FAILED_RUN_ID": health.failed_run_id,
                        "MAIN_HEALTH_REPAIR_BASE_SHA": repair_head,
                        "MAIN_HEALTH_REPAIR_HEAD": repair_head,
                    },
                )
                retry_detail = "post-merge push CI failed; rerun already running"
                if not rerun.already_running:
                    retry_detail = "post-merge push CI failed; rerun submitted"
                return ShipResult(
                    Outcome.TRANSIENT,
                    failed_run_id=health.failed_run_id,
                    pr_number=working.pr_number,
                    pr_url=working.pr_url,
                    merge_result=working.merge_result,
                    detail=retry_detail,
                    main_repair_run_id=health.failed_run_id,
                    main_repair_head=repair_head,
                )
            if rerun.error:
                detail = redact.redact(f"{health.detail}; transient rerun failed: {rerun.error}")
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
                "MAIN_REPAIR_HEAD": repair_head,
                "MAIN_HEALTH_HEAD_SHA": repair_head,
                "MAIN_HEALTH_REPAIR_COMMITTED": "false",
                "MAIN_HEALTH_REPAIR_FAILED_RUN_ID": health.failed_run_id,
                "MAIN_HEALTH_REPAIR_BASE_SHA": repair_head,
                "MAIN_HEALTH_REPAIR_HEAD": repair_head,
            },
        )
        return ShipResult(
            Outcome.NEEDS_USER_INPUT,
            needs_user_reason=config.NEEDS_USER_POSTMERGE_MAIN_CI_FAIL,
            failed_run_id=health.failed_run_id,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            merge_result=working.merge_result,
            detail=detail,
            main_health_head_sha=repair_head,
            main_health_repair_committed="false",
            main_health_repair_failed_run_id=health.failed_run_id,
            main_health_repair_base_sha=repair_head,
            main_health_repair_head=repair_head,
            original_branch_forbidden="true",
            main_repair_run_id=health.failed_run_id,
            main_repair_head=repair_head,
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
    return larch_io.read_kvs(
        path,
        first_wins=False,
        errors="replace",
        reject_symlink=True,
        cr_strip="strip",
        on_error_default=True,
    )


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
    main_health_path = Path(working.tmpdir) / "main-health.env"
    if not main_health_path.is_file():
        if not _main_health_sidecar_bootstrapped(working.tmpdir):
            return None
        return _missing_main_health_sidecar_result(
            ctx=working.with_(stall_tracking=True, stall_step="main-ci"),
            step="main-ci",
            counters=counters,
        )
    base_head = _resolve_premerge_main_health_sha(
        runner=runner,
        repo_root=repo_root,
        base_ref=base_ref,
    )
    if not base_head:
        detail = f"pre-merge main-health gate could not resolve origin/{base_ref} HEAD"
        _write_terminal_state(
            ctx=working.with_(stall_tracking=True, stall_step="main-ci"),
            result=Outcome.STALLED,
            step="main-ci",
            iteration=counters.iteration,
            rebase_count=counters.rebase_count,
            fix_attempts=counters.fix_attempts,
            transient_retries=counters.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=detail,
        )
    health = main_health.read_main_health(
        runner,
        main_health.MainHealthQuery(
            repo=working.repo,
            base_branch=base_ref,
            workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
            limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
            cwd=repo_root,
            head_sha=base_head,
        ),
    )
    if health.status in {"pending", "error"}:
        waited = main_health.wait_main_health(
            runner,
            main_health.MainHealthWaitQuery(
                health=main_health.MainHealthQuery(
                    repo=working.repo,
                    base_branch=base_ref,
                    workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
                    limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
                    cwd=repo_root,
                    head_sha=base_head,
                ),
                timeout=config.MAIN_HEALTH_WAIT_TIMEOUT_SEC,
                interval=config.MAIN_HEALTH_WAIT_POLL_INTERVAL_SEC,
            ),
        )
        health = waited.health
    if health.status == "pass":
        return None
    if health.status == "skip":
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
            main_health_head_sha=health.head_sha or base_head,
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
        main_health_head_sha=health.head_sha or base_head,
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


def _emergency_repair_transient_recovery_result(
    *,
    runner: Runner,
    working: RunContext,
    resume: ResumePlan,
    repo_root: str,
) -> ShipResult | None:
    repair_branch = run_logs.read_state_kv(
        state_file=working.state_file,
        key="EMERGENCY_REPAIR_BRANCH",
    ).strip()
    repair_head = run_logs.read_state_kv(
        state_file=working.state_file,
        key="MAIN_REPAIR_HEAD",
    ).strip()
    if repair_branch or not repair_head:
        return None
    health = main_health.read_main_health(
        runner,
        main_health.MainHealthQuery(
            repo=working.repo,
            base_branch="main",
            workflow=config.MAIN_HEALTH_DEFAULT_WORKFLOW,
            limit=config.MAIN_HEALTH_RUN_LIST_LIMIT,
            cwd=repo_root,
            head_sha=repair_head,
            skip_flap_check=True,
        ),
    )
    if health.status != "pass":
        return None
    _write_ship_state(
        working,
        phase="postmerge",
        iteration=resume.iteration,
        rebase_count=resume.rebase_count,
        fix_attempts=resume.fix_attempts,
        transient_retries=resume.transient_retries,
    )
    post = run_postmerge_phase(runner=runner, ctx=working, cwd=repo_root)
    if post.outcome is Outcome.OK:
        _write_ship_state(
            working,
            phase="done",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
    return ShipResult(
        post.outcome,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        merge_result=working.merge_result,
        detail=post.detail,
    )


def run_ship(
    ctx: RunContext,
    *,
    runner: Runner = proc,
    cwd: str | None = None,
) -> ShipResult:
    prior_state_file = os.environ.get("SHIP_PR_STATE_FILE")
    state_file = ctx.state_file or (str(Path(ctx.tmpdir) / "ship-pr-state.sh") if ctx.tmpdir else "")
    if state_file:
        os.environ["SHIP_PR_STATE_FILE"] = state_file
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
        if resume.start == "postmerge-push-watch":
            working = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
            return _ship_postmerge_phase(
                runner=runner,
                working=working,
                cwd=repo_root,
                iteration=resume.iteration,
                rebase_count=resume.rebase_count,
                fix_attempts=resume.fix_attempts,
                transient_retries=resume.transient_retries,
            )
        if resume.start == "emergency-repair":
            working = _hydrate_resume_context(ctx=ctx, resume=resume).with_(pr_closed=True)
            recovered = _emergency_repair_transient_recovery_result(
                runner=runner,
                working=working,
                resume=resume,
                repo_root=repo_root,
            )
            if recovered is not None:
                return recovered
            return ShipResult(
                Outcome.NEEDS_USER_INPUT,
                needs_user_reason=config.NEEDS_USER_POSTMERGE_MAIN_CI_FAIL,
                failed_run_id=run_logs.read_state_kv(state_file=ctx.state_file, key="MAIN_REPAIR_RUN_ID"),
                pr_number=working.pr_number,
                pr_url=working.pr_url,
                merge_result=working.merge_result,
                detail=resume.detail or "post-merge emergency repair remains in progress",
            )

        if resume.start == "fresh":
            fresh_context = _hydrate_fresh_context(ctx=ctx, resume=resume)
            destalled = _destall_pre_pr_reentry(ctx=fresh_context, resume=resume, runner=runner, repo_root=repo_root)
            if isinstance(destalled, ShipResult):
                return destalled
            fresh_context = destalled
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
            destalled = _destall_pre_pr_reentry(ctx=pr_context, resume=resume, runner=runner, repo_root=repo_root)
            if isinstance(destalled, ShipResult):
                return destalled
            pr_context = destalled

        _write_ship_state(
            pr_context,
            phase=config.SHIP_ROUTE_ACTION_ASSESSMENTS,
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        gates, assessment_result = _compose_assessment_gate_before_pr(
            runner=runner,
            pr_context=pr_context,
            repo_root=repo_root,
            base_ref=base_ref,
            resume=resume,
        )
        if assessment_result is not None:
            return assessment_result
        _write_ship_state(
            pr_context,
            phase="pr-create",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        _breadcrumb(step="pr-create", detail="PR")
        _progress_note(step="8", text="creating PR")
        body = _compose_pr_body_for_pr_create(
            pr_context=pr_context,
            architectural_invariants_note=gates.invariants.note,
            architectural_guidelines_note=gates.guidelines.note,
        )
        title = _pr_title(ctx=pr_context, runner=runner, cwd=repo_root)
        ensured: pr.PrResult = pr.ensure_pr(runner=runner, ctx=pr_context, body=body, title=title, cwd=repo_root, base=base_ref)
        working = pr_context.with_(
            pr_number=ensured.number or pr_context.pr_number,
            pr_url=ensured.url or pr_context.pr_url,
            pr_title=title,
            pr_closed=False,
        )
        if working.pr_number:
            _progress_note(step="8", text=f"PR #{working.pr_number} created")
        _write_ship_state(
            working,
            phase="ci-initial" if working.merge and not working.draft else "done",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        if working.merge and not working.draft and working.pr_number:
            _progress_note(step="8", text=f"CI running for PR #{working.pr_number}")
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
                if (monitor.result.detail or "").startswith("ci-fix-exhausted:"):
                    first_line = (monitor.result.detail or "").splitlines()[0]
                    _progress_note(step="8", text=first_line)
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
                _progress_note(step="8", text="CI-fix rebase running")
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
            _progress_note(step="8", text=f"merged PR #{working.pr_number}" if working.pr_number else "merged")
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
    finally:
        if prior_state_file is None:
            _ = os.environ.pop("SHIP_PR_STATE_FILE", None)
        else:
            os.environ["SHIP_PR_STATE_FILE"] = prior_state_file


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
    _ = parser.add_argument("--result-env-path")
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


_CI_FIX_AUTONOMOUS_REASONS = frozenset({
    config.NEEDS_USER_FIRST_FIXER_NON_HEALTH,
    config.NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
    config.NEEDS_USER_LOCAL_UNFIXABLE,
    config.NEEDS_USER_MAIN_CI_FAIL,
    config.NEEDS_USER_FLAKY_DEFECT_UNFIXED,
})


def _distill_ci_errors_for_result(*, ctx: RunContext, result: ShipResult) -> tuple[str, str, int]:
    """Distill CI failure evidence for a ci-fix ``NEEDS_USER`` result.

    Returns ``(ci_errors_file, distill_class, failed_jobs_count)``: the absolute
    digest path with an empty class and the failing-job count on success; an
    empty path with a bail class and the count (zero when unknown) when distill
    is skipped (no run id, non-ci-fix reason) or fails. Distill failure never
    blocks the bail. The count is forwarded into the ci-fix route-exit handoff as
    ``FAILED_JOBS_COUNT`` evidence for the main agent (#7192, #7219).
    """
    reason = result.needs_user_reason
    run_id = result.failed_run_id
    eligible = (
        result.outcome is Outcome.NEEDS_USER_INPUT
        and run_id.isdigit()
        and (reason in _CI_FIX_AUTONOMOUS_REASONS or reason.startswith(f"{config.NEEDS_USER_CI_LOCAL_UNFIXABLE}:"))
        and bool(ctx.repo)
        and "/" in ctx.repo
        and _tmpdir_under_allowed_root(ctx.tmpdir)
    )
    if not eligible:
        return "", "", 0
    output = Path(ctx.tmpdir) / f"ci-errors-{run_id}.md"
    try:
        outcome = ci.distill_log(run_id=run_id, repo=ctx.repo, output=output)
    except Exception as exc:  # pylint: disable=broad-exception-caught  # distill must never block the ci-fix bail
        logging_util.BreadcrumbWriter().emit(f"ship.py: ci distill-log failed: {exc}")
        return "", "distill-exception", 0
    if outcome.status == "ok":
        return str(output), "", outcome.failed_jobs_count
    return "", outcome.bail_class or "distill-failed", outcome.failed_jobs_count


def main(argv: list[str] | None = None) -> int:
    ctx = RunContext.from_env(env={})
    result: ShipResult
    result_env_path: Path | None = None
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
        # Prevalidate a supplied result-env sink before logging setup, run_ship,
        # stall persistence, or CI distillation so invalid config fails closed.
        raw_result_env = getattr(args, "result_env_path", None)
        if raw_result_env not in (None, ""):
            result_env_path = validate_ship_result_env_path(
                tmpdir=ctx.tmpdir,
                path=str(raw_result_env),
            )
        if _tmpdir_under_allowed_root(ctx.tmpdir):
            os.environ[config.ENV_IMPLEMENT_TMPDIR] = ctx.tmpdir
            logging_util.quiet_init(argv0="ship.py")
        result = run_ship(ctx, runner=proc, cwd=str(Path.cwd()))
    except Exception as exc:  # top-level contract envelope
        # Prevalidation raises before assigning result_env_path, so the sink stays
        # None and no result-env write is attempted. A later failure keeps a
        # previously validated path for exception result emission.
        logging_util.BreadcrumbWriter().emit(
            f"ship.py: internal error\n{traceback.format_exc()}",
        )
        result = ShipResult(Outcome.INTERNAL_ERROR, detail=f"{type(exc).__name__}: {exc}")
    _persist_stall_metadata_if_needed(ctx=ctx, result=result, tmpdir=Path(ctx.tmpdir))
    ci_errors_file, ci_errors_distill_class, failed_jobs_count = _distill_ci_errors_for_result(ctx=ctx, result=result)
    try:
        emit_result(
            ctx=ctx,
            result=result,
            ci_errors_file=ci_errors_file,
            ci_errors_distill_class=ci_errors_distill_class,
            failed_jobs_count=failed_jobs_count,
            result_env_path=result_env_path,
        )
    except Exception:  # required result-env write must not publish JSON then succeed
        logging_util.BreadcrumbWriter().emit(
            f"ship.py: result-env emit failed\n{traceback.format_exc()}",
        )
        return config.OUTCOME_EXIT_MAP[Outcome.INTERNAL_ERROR]
    return config.OUTCOME_EXIT_MAP[result.outcome]


if __name__ == "__main__":
    raise SystemExit(main())
