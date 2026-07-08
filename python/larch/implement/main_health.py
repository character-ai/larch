"""Default-branch push CI health helpers for /implement."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass

from larch.core import config
from larch.core.proc import Runner
from larch.errors import ShipError
from larch.git import gh

MAIN_HEALTH_STATUSES = frozenset({"pass", "fail", "pending", "error"})
_FAILURE_CONCLUSIONS = frozenset({
    "action_required",
    "cancelled",
    "failure",
    "startup_failure",
    "timed_out",
})
_PENDING_STATUSES = frozenset({"queued", "requested", "waiting", "pending", "in_progress"})

ClockFn = Callable[[], float]
SleepFn = Callable[[float], None]


@dataclass(frozen=True)
class MainHealthStatus:
    status: str
    failed_run_id: str = ""
    head_sha: str = ""
    detail: str = ""


@dataclass(frozen=True)
class MainHealthWaitResult:
    health: MainHealthStatus
    elapsed_seconds: int
    attempts: int


@dataclass(frozen=True)
class MainHealthQuery:
    repo: str
    base_branch: str
    workflow: str
    limit: int
    cwd: str | None = None
    head_sha: str | None = None
    upstream_repo: str | None = None
    skip_flap_check: bool = False


@dataclass(frozen=True)
class MainHealthWaitQuery:
    health: MainHealthQuery
    timeout: int
    interval: int


def _bounded_detail(text: str) -> str:
    compact = " ".join(text.replace("\r", " ").replace("\n", " ").split())
    return compact[: config.MAIN_HEALTH_DETAIL_MAX_CHARS]


def _failure_detail(run: gh.WorkflowRun, *, reason: str) -> str:
    return _bounded_detail(
        f"{reason}: run {run.database_id} status={run.status} conclusion={run.conclusion or ''}",
    )


def _has_named_repository_failure(
    runner: Runner,
    run: gh.WorkflowRun,
    *,
    repo: str,
    cwd: str | None,
) -> bool:
    jobs = gh.failed_jobs(runner, run.database_id, repo=repo, cwd=cwd)
    return any(job.name.strip() for job in jobs)


def _same_sha_failure_flap(
    runner: Runner,
    runs: tuple[gh.WorkflowRun, ...],
    *,
    repo: str,
    head_sha: str,
    cwd: str | None,
) -> MainHealthStatus | None:
    for run in runs:
        if run.head_sha != head_sha:
            continue
        conclusion = (run.conclusion or "").lower()
        if run.status.lower() != "completed" or conclusion not in _FAILURE_CONCLUSIONS:
            continue
        if _has_named_repository_failure(runner, run, repo=repo, cwd=cwd):
            return MainHealthStatus(
                status="fail",
                failed_run_id=str(run.database_id),
                head_sha=head_sha,
                detail=_failure_detail(run, reason="same-sha repository failure later passed"),
            )
    return None


def _matching_runs(
    runs: tuple[gh.WorkflowRun, ...],
    *,
    head_sha: str | None,
) -> tuple[gh.WorkflowRun, ...]:
    if head_sha:
        return tuple(run for run in runs if run.head_sha == head_sha)
    return runs


def _classify_runs(
    runner: Runner,
    runs: tuple[gh.WorkflowRun, ...],
    *,
    repo: str,
    query: MainHealthQuery,
) -> MainHealthStatus:
    requested_head_sha: str | None = query.head_sha
    cwd: str | None = query.cwd
    skip_flap_check: bool = query.skip_flap_check
    matching = _matching_runs(runs, head_sha=requested_head_sha)
    if not matching:
        detail = "no matching push workflow runs"
        if requested_head_sha:
            detail = f"no push workflow runs matched head SHA {requested_head_sha}"
        return MainHealthStatus(status="error", detail=_bounded_detail(detail))
    latest = matching[0]
    status = latest.status.lower()
    conclusion = (latest.conclusion or "").lower()
    matched_head_sha = latest.head_sha or (requested_head_sha or "")
    result = MainHealthStatus(
        status="error",
        head_sha=matched_head_sha,
        detail=_bounded_detail(
            f"ambiguous run {latest.database_id} status={latest.status} conclusion={latest.conclusion or ''}",
        ),
    )
    if status in _PENDING_STATUSES or (status != "completed" and not conclusion):
        result = MainHealthStatus(
            status="pending",
            head_sha=matched_head_sha,
            detail=_bounded_detail(f"run {latest.database_id} is {latest.status}"),
        )
    elif status == "completed" and conclusion == "success":
        if not matched_head_sha:
            result = MainHealthStatus(
                status="error",
                detail=_bounded_detail(
                    f"run {latest.database_id} completed successfully without a head SHA",
                ),
            )
        else:
            if not skip_flap_check:
                flap = _same_sha_failure_flap(
                    runner,
                    matching[1:],
                    repo=repo,
                    head_sha=matched_head_sha,
                    cwd=cwd,
                )
                if flap is not None:
                    return flap
            result = MainHealthStatus(
                status="pass",
                head_sha=matched_head_sha,
                detail=_bounded_detail(f"run {latest.database_id} completed successfully"),
            )
    elif status == "completed" and conclusion in _FAILURE_CONCLUSIONS:
        result = MainHealthStatus(
            status="fail",
            failed_run_id=str(latest.database_id),
            head_sha=matched_head_sha,
            detail=_failure_detail(latest, reason="default-branch push workflow failed"),
        )
    return result


def read_main_health(
    runner: Runner,
    query: MainHealthQuery,
) -> MainHealthStatus:
    query_repo = query.upstream_repo or query.repo
    try:
        runs = gh.run_list_filtered(
            runner,
            gh.WorkflowRunListFilters(
                repo=query_repo,
                branch=query.base_branch,
                workflow=query.workflow,
                event="push",
                commit=query.head_sha,
                limit=query.limit,
                cwd=query.cwd,
            ),
        )
        return _classify_runs(
            runner,
            runs,
            repo=query_repo,
            query=query,
        )
    except ShipError as exc:
        return MainHealthStatus(status="error", detail=_bounded_detail(str(exc)))


def wait_main_health(
    runner: Runner,
    query: MainHealthWaitQuery,
    *,
    clock: ClockFn = time.monotonic,
    sleep: SleepFn = time.sleep,
) -> MainHealthWaitResult:
    start = clock()
    attempts = 0
    head_sha = query.health.head_sha
    last = MainHealthStatus(status="pending", head_sha=head_sha or "", detail="waiting for matching push workflow run")
    while True:
        attempts += 1
        last = read_main_health(runner, query.health)
        elapsed = int(clock() - start)
        if last.status in {"pass", "fail"}:
            return MainHealthWaitResult(health=last, elapsed_seconds=elapsed, attempts=attempts)
        no_match_for_requested_sha = (
            last.status == "error"
            and bool(head_sha)
            and last.detail.startswith("no push workflow runs matched head SHA")
        )
        if elapsed >= query.timeout or (last.status == "error" and not no_match_for_requested_sha):
            if last.status == "pending":
                last = MainHealthStatus(
                    status="pending",
                    head_sha=last.head_sha,
                    detail=_bounded_detail(last.detail or "timed out waiting for main health"),
                )
            elif no_match_for_requested_sha:
                last = MainHealthStatus(
                    status="pending",
                    head_sha=head_sha or "",
                    detail=_bounded_detail(last.detail or "waiting for matching push workflow run"),
                )
            return MainHealthWaitResult(health=last, elapsed_seconds=elapsed, attempts=attempts)
        sleep(max(0, min(query.interval, query.timeout - elapsed)))
