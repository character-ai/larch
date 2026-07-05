"""Merge loop helpers, rebase phases, and CI-not-ready handling for ship-pr."""
# pyright: reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

from larch.core import config
from larch.core.proc import Runner
from larch.core.run_context import RunContext
from larch.errors import PrePushConflictHandoff, ShipError
from larch.git import gh
from larch.git import push
from larch.git import rebase
from larch.outcomes import Outcome
from larch.report import run_logs
from larch.implement.ship_state import _write_ship_state, _breadcrumb
from larch.implement.ship_result import ShipResult
from larch.implement.ship_pr import _write_terminal_state, _publish_post_pr_terminal_snapshot

if TYPE_CHECKING:
    from larch.implement.ship_resume import ResumePlan


_CI_NOT_READY_RACE_DETAILS = frozenset(
    {
        "no fail or pending PR checks remain",
    }
)


@dataclass
class _CiNotReadyGuard:
    last_detail: str = ""
    count: int = 0

    def reset(self) -> None:
        self.last_detail = ""
        self.count = 0

    def record(self, detail: str) -> int:
        if detail in _CI_NOT_READY_RACE_DETAILS:
            self.reset()
            return 0
        if detail == self.last_detail:
            self.count += 1
        else:
            self.last_detail = detail
            self.count = 1
        return self.count


@dataclass(frozen=True)
class _MergeLoopCounters:
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int


class ShipRebaseVariant(StrEnum):
    GOTO_REBASE = "goto_rebase"
    MAIN_ADVANCED = "main_advanced"


@dataclass(frozen=True)
class ShipRebasePhaseResult:
    rebase_count: int
    terminal: ShipResult | None = None


def _handle_merge_ci_not_ready(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
    counters: _MergeLoopCounters,
    guard: _CiNotReadyGuard,
) -> tuple[int, ShipResult | None]:
    ci_not_ready_detail = gh.pr_checks_not_ready_detail(
        runner,
        working.pr_number or 0,
        repo=working.repo,
        cwd=repo_root,
    )
    ci_not_ready_count = guard.record(ci_not_ready_detail)
    iteration = counters.iteration + 1
    if ci_not_ready_count < config.SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD:
        _write_ship_state(
            working,
            phase="ci-initial",
            iteration=iteration,
            rebase_count=counters.rebase_count,
            fix_attempts=counters.fix_attempts,
            transient_retries=counters.transient_retries,
        )
        return iteration, None

    detail = f"merge CI not ready after unchanged checks: {ci_not_ready_detail}"
    _write_terminal_state(
        ctx=working,
        result=Outcome.STALLED,
        step="merge-ci-not-ready",
        iteration=iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
    )
    _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
    return iteration, ShipResult(
        Outcome.STALLED,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        detail=detail,
    )


def _merge_loop_iteration_cap_stall(
    *,
    runner: Runner,
    working: RunContext,
    repo_root: str,
    counters: _MergeLoopCounters,
) -> ShipResult:
    _write_terminal_state(
        ctx=working,
        result=Outcome.STALLED,
        step="merge-loop-iteration-cap",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
    )
    _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=repo_root)
    return ShipResult(
        Outcome.STALLED,
        pr_number=working.pr_number,
        pr_url=working.pr_url,
        detail="merge loop iteration cap reached",
    )


def _ship_rebase_phase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    base_remote: str,
    base_ref: str,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    variant: ShipRebaseVariant,
) -> ShipRebasePhaseResult:
    _ = variant
    _write_ship_state(
        working,
        phase="rebase",
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        transient_retries=transient_retries,
    )
    _breadcrumb(step="rebase", detail="Flush+Push")
    pre_rebase: run_logs.RefreshSkip = run_logs.flush_logs_pre(runner=runner, ctx=working.with_(state_file=None), cwd=cwd)
    if (
        pre_rebase.skipped
        and pre_rebase.reason != run_logs.REFRESH_SKIP_RECOVERY_FAILED
        and pre_rebase.reason not in config.REFRESH_SKIP_POST_ENSURE_PR_OK
    ):
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="pre-rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
        )
        _publish_post_pr_terminal_snapshot(runner=runner, ctx=working, cwd=cwd)
        return ShipRebasePhaseResult(
            rebase_count,
            ShipResult(
                Outcome.STALLED,
                detail=f"pre-rebase flush skipped: {pre_rebase.reason}",
            ),
        )
    try:
        result = rebase.rebase_and_push(
            runner=runner,
            repo=working.repo,
            run_id=working.run_id,
            cwd=cwd,
            tmpdir=working.tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
            allow_conflict_fix=True,
            enable_pre_push_handoff=True,
        )
    except PrePushConflictHandoff as exc:
        _write_ship_state(
            working,
            phase="rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase=exc.resume_phase,
            caller_kind=exc.caller_kind,
            extra_fields={"CONFLICT_FILES": exc.conflict_csv},
        )
        raise
    rebase_count += 1
    _ = result.rebased
    return ShipRebasePhaseResult(rebase_count)


def _ship_phase14_rebase(
    *,
    runner: Runner,
    working: RunContext,
    cwd: str,
    base_remote: str,
    base_ref: str,
    phase14_flag: Path,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    last_monitored_head: str | None,
) -> int:
    try:
        result = rebase.rebase_and_push(
            runner=runner,
            repo=working.repo,
            run_id=working.run_id,
            cwd=cwd,
            tmpdir=working.tmpdir,
            base_remote=base_remote,
            base_ref=base_ref,
            allow_conflict_fix=True,
            enable_pre_push_handoff=True,
        )
        phase14_flag.unlink(missing_ok=True)
        rebase_count += 1
        _ = result.rebased
        _write_ship_state(
            working,
            phase="ci-initial",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase="",
            caller_kind="",
            last_monitored_head=last_monitored_head or "",
        )
        return rebase_count
    except PrePushConflictHandoff as exc:
        _write_ship_state(
            working,
            phase="rebase",
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
            transient_retries=transient_retries,
            resume_phase=exc.resume_phase,
            caller_kind=exc.caller_kind,
            extra_fields={"CONFLICT_FILES": exc.conflict_csv},
        )
        raise
    except Exception:
        phase14_flag.unlink(missing_ok=True)
        raise


def _post_ensure_flush_and_push(
    runner: Runner,
    *,
    working: RunContext,
    resume: ResumePlan,
    repo_root: str,
) -> ShipResult | None:
    """Push the post-PR head without re-flushing run logs.

    The run logs are flushed exactly once, before the PR is created (the
    ``pr-prep`` phase), so ``final-summary.md`` with placeholder PR fields plus
    the token/timing/transcript data ride the PR's initial push in a single
    commit and land in the squash merge. The live PR URL is refreshed into the
    tracking issue via API only (``write_final_report_comment``), per the Step 7a
    "Pre-ship log flush" contract in ``skills/implement/SKILL.md`` ("no second
    commit, no second push").

    Re-flushing here would commit a brand-new log-churn commit, move HEAD, and
    re-trigger CI: a redundant head-moving push on a fresh run (issue #5217) and
    the perpetual no-ci-checks-observed loop on open-pr resume (issue #5186). So
    this step never re-flushes; it only pushes. The push is idempotent (a no-op
    when the remote already has this head, a one-time reconcile when a prior
    invocation committed but failed to push), so first-try CI success yields
    exactly one push for the whole run and CI converges on a stable head.

    Returns a terminal ``ShipResult`` on push failure, or ``None`` to continue
    into the merge loop.
    """
    _breadcrumb(step="post-ensure-pr", detail="Push")
    try:
        post_ensure_push = push.push_branch(runner=runner, ctx=working, cwd=repo_root)
    except ShipError as exc:
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="post-ensure-pr-push",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=f"post-ensure-pr push failed: {str(exc).strip()}",
        )
    if post_ensure_push.status != "pushed":
        _write_terminal_state(
            ctx=working,
            result=Outcome.STALLED,
            step="post-ensure-pr-push",
            iteration=resume.iteration,
            rebase_count=resume.rebase_count,
            fix_attempts=resume.fix_attempts,
            transient_retries=resume.transient_retries,
        )
        return ShipResult(
            Outcome.STALLED,
            pr_number=working.pr_number,
            pr_url=working.pr_url,
            detail=f"post-ensure-pr push failed: {post_ensure_push.status}",
        )
    return None
