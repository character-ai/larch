"""Resume planning and context hydration for ship-pr."""
# pyright: reportUnusedFunction=false, reportPrivateUsage=false

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path

from larch.core import config
from larch.core.proc import Runner
from larch.core.run_context import RunContext
from larch.git import git
from larch.git import gh
from larch.implement import ci_monitor
from larch.outcomes import Outcome
from larch.report import run_logs
from larch.implement.ship_state import (
    _truthy,
    _state_file_kv,
    _validate_ship_state_value,
    _valid_branch_name,
    _valid_pr_url,
    _valid_state_merge_result,
    _valid_merge_result,
    _state_bool_text,
    _valid_repo_slug,
    _MIN_GH_SKIPPED_MERGE_SIGNALS,
)


@dataclass(frozen=True)
class ResumePlan:
    start: str
    iteration: int
    rebase_count: int
    fix_attempts: int
    transient_retries: int
    pr_number: int | None
    pr_url: str
    merge_result: str
    branch_name: str
    repo: str
    durable: run_logs.DurableFlags
    detail: str = ""


def _is_active_pre_push_handoff(ctx: RunContext) -> bool:
    if not ctx.state_file:
        return False
    resume_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="RESUME_PHASE")
    caller_kind = run_logs.read_state_kv(state_file=ctx.state_file, key="CALLER_KIND")
    return (
        resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
        and caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
    )


def _context_with_state_overlay(ctx: RunContext) -> RunContext:
    state: dict[str, str] = _state_file_kv(ctx.state_file)
    changes: dict[str, object] = {}
    for key in ("BRANCH_NAME", "PR_URL"):
        value = state.get(key, "")
        if value:
            _validate_ship_state_value(key=key, value=value)
    for key, field in (
        ("BRANCH_NAME", "branch_name"),
        ("ISSUE_NUMBER", "issue_number"),
        ("RUN_ID", "run_id"),
        ("REPO", "repo"),
        ("PR_URL", "pr_url"),
        ("PR_TITLE", "pr_title"),
        ("MERGE_RESULT", "merge_result"),
        ("STALL_STEP", "stall_step"),
    ):
        value = state.get(key, "")
        if value:
            changes[field] = value
    pr_number: int | None = run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number)
    if pr_number is not None:
        changes["pr_number"] = pr_number
    for key, field in (
        ("FORKED_TARGET", "forked_target"),
        ("REPO_UNAVAILABLE", "repo_unavailable"),
        ("DRAFT", "draft"),
        ("MERGE", "merge"),
        ("STALL_TRACKING", "stall_tracking"),
        ("BAIL_NEEDS_USER_INPUT", "bail_needs_user_input"),
        ("PR_CLOSED", "pr_closed"),
        ("CI_FIX_REBASE_PENDING", "ci_fix_rebase_pending"),
        ("OOS_PENDING", "oos_pending"),
    ):
        value = state.get(key, "")
        if value:
            changes[field] = _truthy(value)
    return ctx.with_(**changes) if changes else ctx


def _try_current_branch(runner: Runner, *, cwd: str | None) -> str:
    try:
        return git.current_branch(runner, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        return ""


def _seed_last_monitored_head(
    *,
    ctx: RunContext,
    runner: Runner,
    cwd: str,
    fix_attempts: int,
) -> str | None:
    """Resume seed for post-push empty-checks grace (issue #4867).

    When the merge loop restarts after a head-changing push, the in-process
    ``last_monitored_head`` is lost. Rehydrate from durable state so the first
    monitor poll after resume still uses ``CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC``.
    """
    current: str | None = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    state: dict[str, str] = _state_file_kv(ctx.state_file)
    persisted = state.get("LAST_MONITORED_HEAD", "")
    pending_head = state.get("CI_FIX_REBASE_PENDING_HEAD", "")
    if persisted and current and persisted != current:
        return persisted
    if ctx.ci_fix_rebase_pending and current:
        if pending_head and pending_head != current:
            return pending_head
        return ""
    if fix_attempts > 0 and current and (not persisted or persisted == current):
        return ""
    return current


def _empty_checks_params_for_monitor(
    *,
    current_head: str | None,
    last_monitored_head: str | None,
    initial_startup_deadline_available: bool,
) -> tuple[int, int]:
    # Grant the full poll-based startup deadline both on the first poll and
    # whenever the head changed (rebase / force-push / CI-fix): a new head must
    # re-register checks from scratch, exactly like a brand-new PR head, so the
    # shorter post-fix grace expired before GitHub attached checks and produced a
    # false no-ci-checks-observed stall (issue #5217).
    if current_head != last_monitored_head or initial_startup_deadline_available:
        return 0, config.CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC
    return 0, 0


def _fresh_resume_plan(
    durable: run_logs.DurableFlags,
    *,
    branch_name: str = "",
    repo: str = "",
    counters: run_logs.ResumeCounters | None = None,
    detail: str = "",
) -> ResumePlan:
    if counters is None:
        counters = run_logs.ResumeCounters(0, 0, 0, 0)
    return ResumePlan(
        start="fresh",
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=None,
        pr_url="",
        merge_result="",
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _resume_from_state(
    *,
    start: str,
    counters: run_logs.ResumeCounters,
    durable: run_logs.DurableFlags,
    pr_number: int | None,
    pr_url: str,
    merge_result: str,
    branch_name: str,
    repo: str,
    detail: str = "",
) -> ResumePlan:
    return ResumePlan(
        start=start,
        iteration=counters.iteration,
        rebase_count=counters.rebase_count,
        fix_attempts=counters.fix_attempts,
        transient_retries=counters.transient_retries,
        pr_number=pr_number,
        pr_url=pr_url,
        merge_result=merge_result,
        branch_name=branch_name,
        repo=repo,
        durable=durable,
        detail=detail,
    )


def _invalid_state_plan(
    *,
    counters: run_logs.ResumeCounters,
    durable: run_logs.DurableFlags,
    branch_name: str,
    repo: str,
    detail: str,
) -> ResumePlan:
    return _resume_from_state(
        start="blocked-checkout-mismatch",
        counters=counters,
        durable=durable,
        pr_number=None,
        pr_url="",
        merge_result="",
        branch_name=branch_name,
        repo=repo,
        detail=detail,
    )


def _resume_plan(*, ctx: RunContext, runner: Runner, cwd: str | None) -> ResumePlan:
    counters: run_logs.ResumeCounters = run_logs.read_resume_counters(ctx.state_file)
    durable: run_logs.DurableFlags = run_logs.read_durable_flags(state_file=ctx.state_file, ctx=ctx)
    if not ctx.state_file or not Path(ctx.state_file).is_file():
        return _fresh_resume_plan(durable, repo=ctx.repo)

    state_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="PHASE")
    resume_phase = run_logs.read_state_kv(state_file=ctx.state_file, key="RESUME_PHASE")
    state_branch = run_logs.read_state_kv(state_file=ctx.state_file, key="BRANCH_NAME").strip()
    state_repo = run_logs.read_state_kv(state_file=ctx.state_file, key="REPO").strip() or ctx.repo
    state_pr_url = run_logs.read_state_kv(state_file=ctx.state_file, key="PR_URL")
    pr_url = (state_pr_url if _valid_pr_url(state_pr_url) else "") or (ctx.pr_url if _valid_pr_url(ctx.pr_url) else "")
    merge_result = run_logs.read_state_kv(state_file=ctx.state_file, key="MERGE_RESULT")

    caller_kind = run_logs.read_state_kv(state_file=ctx.state_file, key="CALLER_KIND")
    phase14_flag = Path(ctx.tmpdir) / config.SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME
    if (
        resume_phase == config.SHIP_PR_RRR_RESUME_PHASE
        and caller_kind == config.SHIP_PR_PRE_PUSH_CALLER_KIND
        and not phase14_flag.is_file()
        and not phase14_flag.is_symlink()
    ):
        with suppress(OSError):
            _ = phase14_flag.write_text("RESUME_PHASE=ship-pr-rrr-phase14\n", encoding="utf-8")
    if resume_phase == config.SHIP_PR_RRR_RESUME_PHASE and not phase14_flag.is_file():
        if not _valid_repo_slug(state_repo):
            state_repo = ctx.repo
        return _resume_from_state(
            start="blocked-rebase-continuation",
            counters=counters,
            durable=durable,
            pr_number=run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number),
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=state_branch or ctx.branch_name or ctx.branch,
            repo=state_repo,
            detail="Python ship driver cannot resume rebase-conflict continuation",
        )

    fallback_branch = ctx.branch_name or ctx.branch
    if state_branch and not _valid_branch_name(state_branch):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=fallback_branch,
            repo=ctx.repo,
            detail="invalid state BRANCH_NAME",
        )
    if state_pr_url and not _valid_pr_url(state_pr_url):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state PR_URL",
        )
    if not _valid_state_merge_result(merge_result):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state MERGE_RESULT",
        )
    if not _valid_repo_slug(state_repo):
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="invalid state REPO",
        )
    if state_repo != ctx.repo:
        return _invalid_state_plan(
            counters=counters,
            durable=durable,
            branch_name=state_branch or fallback_branch,
            repo=ctx.repo,
            detail="state REPO does not match context repo",
        )

    current_branch = _try_current_branch(runner, cwd=cwd)
    expected_branch = state_branch or ctx.branch_name or ctx.branch
    if not current_branch:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"cannot verify current checkout branch; expected {expected_branch or '<unknown>'}",
        )
    if expected_branch and current_branch != expected_branch:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=expected_branch,
            repo=state_repo,
            detail=f"checkout branch mismatch: expected {expected_branch}, current {current_branch}",
        )
    if current_branch in {"main", "master"} and not durable.forked_target and not durable.forked:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail=f"refusing to resume on protected branch {current_branch}",
        )
    gh_skipped = durable.repo_unavailable or durable.forked or durable.forked_target
    if not expected_branch and gh_skipped:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=current_branch,
            repo=state_repo,
            detail="cannot verify gh-skipped resume branch anchor",
        )
    branch_name = current_branch
    pr_number: int | None = run_logs.parse_pr_number(state_file=ctx.state_file, ctx_pr_number=ctx.pr_number)
    if gh_skipped and pr_number is not None and not pr_url:
        return _resume_from_state(
            start="blocked-checkout-mismatch",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url="",
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
            detail="cannot verify gh-skipped resume PR identity anchor",
        )
    if pr_number is None and state_phase in {"invariants-assessment", "guidelines-assessment"}:
        return _resume_from_state(
            start="pre-pr-compose",
            counters=counters,
            durable=durable,
            pr_number=None,
            pr_url="",
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
        )
    if pr_number is None and not durable.repo_unavailable:
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail="missing or invalid PR_NUMBER",
        )

    if not gh_skipped:
        if pr_number is None:
            return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)
        try:
            viewed: gh.PullRequest = gh.pr_view(runner, pr_number, repo=state_repo, cwd=cwd)
        except Exception:  # pylint: disable=broad-except
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail="gh pr view failed",
            )
        state = viewed.state.upper()
        if state == "MERGED":
            start = "done" if state_phase == "done" else "merged"
            return _resume_from_state(
                start=start,
                counters=counters,
                durable=durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=_valid_merge_result(merge_result),
                branch_name=branch_name,
                repo=state_repo,
            )
        if viewed.head_ref != branch_name:
            return _fresh_resume_plan(
                durable,
                branch_name=branch_name,
                repo=state_repo,
                counters=counters,
                detail=f"PR head {viewed.head_ref} does not match checkout {branch_name}",
            )
        if state == "OPEN":
            return _resume_from_state(
                start="open-pr",
                counters=counters,
                durable=durable,
                pr_number=viewed.number,
                pr_url=viewed.url or pr_url,
                merge_result=merge_result,
                branch_name=branch_name,
                repo=state_repo,
            )
        return _fresh_resume_plan(
            durable,
            branch_name=branch_name,
            repo=state_repo,
            counters=counters,
            detail=f"PR state {viewed.state} is not resumable",
        )

    pr_closed_signal = _state_bool_text(run_logs.read_state_kv(state_file=ctx.state_file, key="PR_CLOSED"))
    postmerge_phase_signal = state_phase == "postmerge"
    merge_result_signal = merge_result in config.POST_MERGE_MERGE_RESULTS
    postmerge_sentinel_signal = (Path(ctx.tmpdir) / "post-merge-sentinel").is_file()
    manifest_done_signal = run_logs.manifest_status(ctx) == config.MANIFEST_STATUS_DONE and postmerge_sentinel_signal
    local_merged_signal_count = sum(
        bool(signal)
        for signal in (
            pr_closed_signal,
            postmerge_phase_signal,
            merge_result_signal,
            manifest_done_signal,
        )
    )
    local_merged = local_merged_signal_count >= _MIN_GH_SKIPPED_MERGE_SIGNALS
    if state_phase == "done":
        if local_merged:
            return _resume_from_state(
                start="done",
                counters=counters,
                durable=durable,
                pr_number=pr_number,
                pr_url=pr_url,
                merge_result=_valid_merge_result(merge_result),
                branch_name=branch_name,
                repo=state_repo,
            )
        state_phase = "ci-initial"
    if local_merged:
        return _resume_from_state(
            start="merged",
            counters=counters,
            durable=durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=_valid_merge_result(merge_result),
            branch_name=branch_name,
            repo=state_repo,
        )
    if pr_number is not None or durable.repo_unavailable:
        return _resume_from_state(
            start="open-pr",
            counters=counters,
            durable=durable,
            pr_number=pr_number,
            pr_url=pr_url,
            merge_result=merge_result,
            branch_name=branch_name,
            repo=state_repo,
        )
    return _fresh_resume_plan(durable, branch_name=branch_name, repo=state_repo, counters=counters)


def _hydrate_resume_context(*, ctx: RunContext, resume: ResumePlan) -> RunContext:
    run_id = run_logs.effective_run_id(ctx) or ctx.run_id
    return ctx.with_(
        run_id=run_id,
        branch=resume.branch_name or ctx.branch,
        branch_name=resume.branch_name or ctx.branch_name or ctx.branch,
        repo=resume.repo or ctx.repo,
        pr_number=resume.pr_number,
        pr_url=resume.pr_url,
        merge_result=resume.merge_result,
        repo_unavailable=resume.durable.repo_unavailable,
        forked_target=resume.durable.forked_target,
        forked=resume.durable.forked,
        merge=resume.durable.merge,
        draft=resume.durable.draft,
    )


def _merge_loop_uses_resume_counters(resume: ResumePlan) -> bool:
    if resume.start == "open-pr":
        return True
    if resume.start == "fresh":
        return bool(
            resume.iteration
            or resume.rebase_count
            or resume.fix_attempts
            or resume.transient_retries
        )
    return False


def _hydrate_fresh_context(*, ctx: RunContext, resume: ResumePlan) -> RunContext:
    changes: dict[str, object] = {
        "repo": resume.repo or ctx.repo,
        "pr_number": None,
        "pr_url": "",
        "merge_result": "",
        "pr_closed": False,
        "repo_unavailable": resume.durable.repo_unavailable,
        "forked_target": resume.durable.forked_target,
        "forked": resume.durable.forked,
        "merge": resume.durable.merge,
        "draft": resume.durable.draft,
    }
    if resume.branch_name:
        changes["branch"] = resume.branch_name
        changes["branch_name"] = resume.branch_name
    return ctx.with_(**changes)


def _monitor_persisted_counters(
    *,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    transient_retries: int,
    monitor: ci_monitor.MonitorResult,
) -> tuple[int, int, int, int]:
    monitor_ok = monitor.result.outcome is Outcome.OK
    return (
        iteration,
        rebase_count + (1 if monitor_ok and monitor.goto_rebase else 0),
        fix_attempts,
        transient_retries + (1 if monitor.transient_rerun_attempted else 0),
    )
