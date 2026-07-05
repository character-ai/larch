"""CI monitor loop: poll, classify, collect logs, fixer waterfall, GOTO-Rebase signal."""

from __future__ import annotations

import json
import math
import os
import re
import sys
import tempfile
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import cast

from larch.agents import agents
from larch.implement import ship_guidelines
from larch.core import config
from larch.core import external_defaults
from larch.git import gh
from larch.git import git
from larch import io as larch_io
from larch.core import logging_util
from larch.git import rebase
from larch.core import redact
from larch.core import retry
from larch.report import run_logs
from larch.agents.agents import TierAttempt
from larch.errors import ShipError
from larch.git.gh import FailedJob
from larch.outcomes import Outcome, StepResult
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext

_IN_PROGRESS_MSG = "is still in progress; logs will be available"
_CI_SUSPEND_THRESHOLD_SEC = 60.0
_RUN_ID_RE = re.compile(r"runs/(\d+)")
_MATRIX_SLICE_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s+\((\d+)\)$")
_MATRIX_ANY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s+\(([^)]*)\)$")
_JOB_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_PR_CHECKS_STATUS_FIELD_MIN_PARTS = 2

SleepFn = Callable[[float], None]
ClockFn = Callable[[], float]
LaunchFn = Callable[[str], TierAttempt]
PrePushLogRefreshFn = Callable[[], bool]


@dataclass(frozen=True)
class CiStatus:
    status: str
    behind_count: int
    failed_run_id: str | None
    conflicted: bool = False
    pr_view_ok: bool = True
    checks_empty: bool = False
    checks_observed: bool = False


@dataclass(frozen=True)
class BehindProbe:
    count: int | None
    timed_out: bool = False


@dataclass(frozen=True)
class ChecksObservation:
    status: str
    failed_run_id: str | None
    rollup_empty: bool = False
    observed: bool = True


@dataclass(frozen=True)
class Decision:
    action: str
    bail_reason: str | None = None


@dataclass(frozen=True)
class JobClass:
    name: str
    shard: str
    klass: str


@dataclass(frozen=True)
class ClassifiedJobs:
    count: int
    jobs: tuple[JobClass, ...]
    fixable: tuple[JobClass, ...]
    unfixable: tuple[JobClass, ...]


@dataclass(frozen=True)
class StagePushContext:
    classified: ClassifiedJobs | None = None
    run_context: RunContext | None = None
    pre_push_log_refresh: PrePushLogRefreshFn | None = None


@dataclass(frozen=True)
class RerunResult:
    submitted: bool
    already_running: bool
    error: str | None


@dataclass(frozen=True)
class LogCollectResult:
    text: str
    state: str


@dataclass(frozen=True)
class FixResult:
    status: str
    winning_tier: str | None = None
    delta_paths: tuple[str, ...] = ()
    unfixable: tuple[str, ...] = ()
    failed_verify: tuple[str, ...] = ()
    detail: str | None = None
    rerun_already_running: bool = False
    code_fix_attempted_on_ready_log: bool = False
    did_rebase: bool = False
    ci_fix_rebase_pending: bool = False


@dataclass(frozen=True)
class MonitorResult:
    action: str
    ci_status: str
    behind_count: int
    failed_run_id: str | None
    goto_rebase: bool
    iterations: int
    result: StepResult
    rerun_already_running: bool = False
    transient_rerun_attempted: bool = False
    ci_fix_rebase_pending: bool = False


def _conflicted_from_merge_state(merge_state: str | None) -> bool:
    """Mirror ci status CONFLICTED derivation (conservative for UNKNOWN/empty)."""
    if not merge_state:
        return True
    if merge_state == "DIRTY":
        return True
    if merge_state in ("CLEAN", "BEHIND", "BLOCKED", "UNSTABLE", "HAS_HOOKS"):
        return False
    if merge_state == "UNKNOWN":
        return True
    return True


def decide(
    status: CiStatus,
    *,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
) -> Decision:
    """Pure port of ci decide decision matrix."""
    if status.status == "merged":
        return Decision(action="already_merged")
    if status.status == "error":
        return Decision(
            action="bail",
            bail_reason=config.CI_DECIDE_BAIL_STATUS_ERROR,
        )
    behind = status.behind_count > 0
    if status.status == "pass" and (not behind or not status.conflicted):
        return Decision(action="merge")
    if iteration >= config.CI_MONITOR_MAX_ITERATIONS:
        return Decision(
            action="bail",
            bail_reason=config.CI_DECIDE_BAIL_TIMEOUT,
        )
    if rebase_count >= config.CI_MONITOR_MAX_REBASES:
        return Decision(
            action="bail",
            bail_reason=config.CI_DECIDE_BAIL_TOO_MANY_REBASES,
        )
    if fix_attempts >= config.CI_MONITOR_MAX_FIX_ATTEMPTS:
        return Decision(action="bail", bail_reason=config.CI_DECIDE_BAIL_FIX_ATTEMPTS_EXHAUSTED)
    if status.status == "pending":
        # Wait out an in-flight run on the current head even when behind main. A
        # behind-but-unconflicted branch is squash-mergeable, so rebasing a
        # pending run would only discard healthy CI and force-push a new head
        # that must re-register checks from scratch -- the false
        # no-ci-checks-observed stall of issue #5217. A genuine conflict still
        # rebases once the run resolves to pass+behind+conflicted above.
        return Decision(action="wait")
    if status.status == "pass":
        return Decision(action="rebase")
    if status.status == "fail":
        return Decision(
            action="rebase_then_evaluate" if behind else "evaluate_failure",
        )
    return Decision(action="wait")


def _extract_run_id(link: str) -> str | None:
    match = _RUN_ID_RE.search(link)
    return match.group(1) if match else None


def _gh_pr_checks(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None,
    required: bool = False,
) -> CommandResult:
    argv = [
        "gh",
        "pr",
        "checks",
        str(pr),
        "--repo",
        repo,
        "--json",
        "name,state,bucket,link",
    ]
    if required:
        argv.append("--required")
    return runner.run(argv, cwd=cwd, timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC)


def _warn_stderr(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _raise_on_status_query_timeout(result: CommandResult, *, label: str) -> None:
    if result.returncode == config.EXIT_TIMEOUT:
        msg = (
            f"{label} timed out after {config.CI_STATUS_QUERY_TIMEOUT_SEC:.0f}s "
            f"({' '.join(result.argv)})"
        )
        raise gh.GhReadTimeout(msg)


def _ci_status_for_query_timeout(
    *,
    conflicted: bool,
    pr_view_ok: bool,
    label: str,
) -> CiStatus:
    _warn_stderr(
        f"gather_status: {label} timed out after "
        f"{config.CI_STATUS_QUERY_TIMEOUT_SEC:.0f}s; treating as CI status failure",
    )
    return CiStatus(
        status="error",
        behind_count=0,
        failed_run_id=None,
        conflicted=conflicted,
        pr_view_ok=pr_view_ok,
        checks_observed=False,
    )


def _behind_count(
    runner: Runner,
    *,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> BehindProbe:
    base = f"{base_remote}/{base_ref}"
    result = runner.run(
        ["git", "rev-list", "--count", f"HEAD..{base}"],
        cwd=cwd,
        timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC,
    )
    if result.returncode == config.EXIT_TIMEOUT:
        _warn_stderr(
            "gather_status: git rev-list --count timed out; treating branch as pending",
        )
        return BehindProbe(count=None, timed_out=True)
    if result.returncode != 0:
        _warn_stderr(
            "gather_status: git rev-list --count failed; treating branch as pending",
        )
        return BehindProbe(count=None)
    text = result.stdout.strip() or "0"
    try:
        return BehindProbe(count=int(text))
    except ValueError:
        _warn_stderr(
            "gather_status: git rev-list --count returned non-integer; treating as pending",
        )
        return BehindProbe(count=None)


def behind_count(
    runner: Runner,
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
    fetch: bool = True,
    cwd: str | None = None,
) -> int:
    """Public ci behind-count parity: validate labels, fail open to 0."""
    if git.validate_base_remote_ref(base_remote=base_remote, base_ref=base_ref) is not None:
        return 0
    if fetch:
        fetched = git.fetch(runner, base_remote, base_ref, cwd=cwd)
        if fetched.returncode != 0:
            return 0
    probe = _behind_count(
        runner,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    )
    return probe.count if probe.count is not None else 0


def _squash_merge_race(
    runner: Runner,
    *,
    pr: int,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> bool:
    base = f"{base_remote}/{base_ref}"
    subjects = git.try_log_subjects(runner, f"HEAD..{base}", cwd=cwd)
    needle = f"(#{pr})"
    return any(needle in subject for subject in subjects.subjects)


def _parse_check_rows(parsed: object) -> list[dict[str, object]]:
    if not isinstance(parsed, list):
        return []
    raw_list = cast("list[object]", parsed)
    out: list[dict[str, object]] = [
        cast("dict[str, object]", item) for item in raw_list if isinstance(item, dict)
    ]
    return out


def _checks_json_is_array(checks_json: str) -> bool:
    if not checks_json or checks_json.strip() in ("", "null"):
        return False
    try:
        parsed: object = json.loads(checks_json)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def _row_run_id(row: dict[str, object]) -> str | None:
    link = str(row.get("link", ""))
    return _extract_run_id(link)


def _classify_checks_json(checks_json: str, *, required: bool = False) -> tuple[str, str | None]:
    try:
        parsed: object = json.loads(checks_json or "[]")
    except json.JSONDecodeError:
        return "pending", None
    rows = _parse_check_rows(parsed)
    if not rows:
        return "empty", None
    if required:
        pending = [row for row in rows if row.get("bucket") == "pending"]
        if pending:
            return "pending", None
        failed = [row for row in rows if row.get("bucket") == "fail"]
        if failed:
            return "fail", _row_run_id(failed[0])
        non_pass = [row for row in rows if row.get("bucket") != "pass"]
        if non_pass:
            return "fail", _row_run_id(non_pass[0])
        return "pass", None
    failed = [row for row in rows if row.get("bucket") == "fail"]
    pending = [row for row in rows if row.get("bucket") == "pending"]
    if failed:
        return "fail", _row_run_id(failed[0])
    if pending:
        return "pending", None
    return "pass", None


def _pr_checks_text_status_field(line: str) -> str:
    parts = line.split("\t")
    if len(parts) >= _PR_CHECKS_STATUS_FIELD_MIN_PARTS:
        return parts[1].strip()
    return line.strip()


def _checks_json_from_result(checks: CommandResult) -> str:
    if _checks_json_is_array(checks.stdout):
        return checks.stdout
    return checks.stdout if checks.returncode == 0 else ""


def _classify_checks_text(text: str, *, required: bool = False) -> tuple[str, str | None]:
    if not text.strip():
        return "empty", None
    if required:
        fail_re = (
            r"\b(fail(?:ed|ure|ing)?|error|cancel(?:led|ed)?|skip(?:ped|ping)?|"
            r"unknown|timed?\s*out|action\s+required|neutral|stale)\b"
        )
        pending_re = r"\b(pending|in_progress|in progress|queued|waiting|requested|expected)\b"
        pass_re = r"\b(pass(?:ed|ing)?|success(?:ful)?|succeed(?:ed)?|completed)\b"
    else:
        fail_re = r"\bfail"
        pending_re = r"\b(pending|in_progress|in progress|queued)\b"
        pass_re = r"\b(pass(?:ed|ing)?|success(?:ful)?|succeed(?:ed)?|completed)\b"

    lines = [line for line in text.splitlines() if line.strip()]

    def _classify_field(line: str) -> str:
        return _pr_checks_text_status_field(line) if required else line

    failed_line = next(
        (line for line in lines if re.search(fail_re, _classify_field(line), flags=re.IGNORECASE)),
        "",
    )
    if failed_line:
        link_match: re.Match[str] | None = re.search(r"https://\S+", failed_line)
        run_id = _extract_run_id(link_match.group(0)) if link_match else None
        return "fail", run_id
    if any(re.search(pending_re, _classify_field(line), flags=re.IGNORECASE) for line in lines):
        return "pending", None
    if required and not any(
        re.search(pass_re, _classify_field(line), flags=re.IGNORECASE) for line in lines
    ):
        return "fail", None
    return "pass", None


def _read_pr_checks_text(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None,
    required: bool = False,
) -> str:
    if required:
        result = runner.run(
            ["gh", "pr", "checks", str(pr), "--repo", repo, "--required"],
            cwd=cwd,
            timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC,
        )
    else:
        result = gh.pr_checks_text_read(
            runner,
            pr,
            repo=repo,
            cwd=cwd,
            timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC,
        )
    _raise_on_status_query_timeout(result, label="gh pr checks")
    if result.returncode == 0:
        return result.stdout
    return ""


def _resolve_checks_status(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    empty_checks_grace: int,
    sleep_fn: SleepFn,
    cwd: str | None,
    required: bool = False,
) -> tuple[str, str | None]:
    """Classify PR checks with JSON-first and text fallback (ci status parity)."""
    observation = _resolve_checks_observation(
        runner,
        pr=pr,
        repo=repo,
        empty_checks_grace=empty_checks_grace,
        sleep_fn=sleep_fn,
        cwd=cwd,
        required=required,
    )
    return observation.status, observation.failed_run_id


def _resolve_checks_observation(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    empty_checks_grace: int,
    sleep_fn: SleepFn,
    cwd: str | None,
    required: bool = False,
) -> ChecksObservation:
    """Classify PR checks and derive rollup emptiness from the same read."""
    checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd, required=required)
    _raise_on_status_query_timeout(checks, label="gh pr checks")
    checks_json = _checks_json_from_result(checks)

    if _checks_json_is_array(checks_json):
        bucket_status, run_id = _classify_checks_json(checks_json, required=required)
        if bucket_status == "empty" and empty_checks_grace > 0:
            sleep_fn(float(empty_checks_grace))
            checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd, required=required)
            _raise_on_status_query_timeout(checks, label="gh pr checks")
            checks_json = _checks_json_from_result(checks)
            if _checks_json_is_array(checks_json):
                bucket_status, run_id = _classify_checks_json(checks_json, required=required)
        if bucket_status == "empty":
            text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd, required=required)
            if text.strip():
                text_status, text_run_id = _classify_checks_text(text, required=required)
                return ChecksObservation(
                    status=text_status,
                    failed_run_id=text_run_id,
                    rollup_empty=False,
                )
            return ChecksObservation(
                status="NO_CHECKS" if empty_checks_grace > 0 else "pending",
                failed_run_id=None,
                rollup_empty=True,
            )
        return ChecksObservation(status=bucket_status, failed_run_id=run_id, rollup_empty=False)

    text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd, required=required)
    if not text.strip() and empty_checks_grace > 0:
        sleep_fn(float(empty_checks_grace))
        text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd, required=required)
    if text.strip():
        text_status, text_run_id = _classify_checks_text(text, required=required)
        return ChecksObservation(
            status=text_status,
            failed_run_id=text_run_id,
            rollup_empty=False,
        )
    if empty_checks_grace > 0:
        return ChecksObservation(status="NO_CHECKS", failed_run_id=None, rollup_empty=True)
    return ChecksObservation(status="pending", failed_run_id=None, rollup_empty=True)


def _checks_rollup_empty(  # pyright: ignore[reportUnusedFunction]
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None,
    required: bool = False,
) -> bool:
    checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd, required=required)
    checks_json = _checks_json_from_result(checks)
    if _checks_json_is_array(checks_json):
        bucket_status, _run_id = _classify_checks_json(checks_json, required=required)
        if bucket_status != "empty":
            return False
    text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd, required=required)
    return not text.strip()


def checks_status(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    empty_checks_grace: int = 0,
    sleep_fn: SleepFn = time.sleep,
    cwd: str | None = None,
    required: bool = False,
) -> tuple[str, str | None]:
    """Checks-only status classifier without PR/git merge-state probes."""
    return _resolve_checks_status(
        runner,
        pr=pr,
        repo=repo,
        empty_checks_grace=empty_checks_grace,
        sleep_fn=sleep_fn,
        cwd=cwd,
        required=required,
    )


@dataclass(frozen=True)
class _AfterPrViewQuery:
    pr: int
    repo: str
    base_remote: str
    base_ref: str
    empty_checks_grace: int
    sleep_fn: SleepFn
    cwd: str | None
    required: bool
    conflicted: bool
    pr_view_ok: bool


def _gather_git_checks_and_behind(
    *, runner: Runner,
    query: _AfterPrViewQuery,
) -> CiStatus | tuple[ChecksObservation, BehindProbe]:
    try:
        fetch = git.fetch(
            runner,
            query.base_remote,
            query.base_ref,
            cwd=query.cwd,
            timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC,
        )
        _raise_on_status_query_timeout(fetch, label="git fetch")
        if fetch.returncode != 0:
            return CiStatus(
                status="pending",
                behind_count=0,
                failed_run_id=None,
                conflicted=query.conflicted,
                checks_empty=False,
                checks_observed=False,
            )
        observation = _resolve_checks_observation(
            runner,
            pr=query.pr,
            repo=query.repo,
            empty_checks_grace=query.empty_checks_grace,
            sleep_fn=query.sleep_fn,
            cwd=query.cwd,
            required=query.required,
        )
        behind_probe = _behind_count(
            runner,
            base_remote=query.base_remote,
            base_ref=query.base_ref,
            cwd=query.cwd,
        )
    except gh.GhReadTimeout as exc:
        label = str(exc).split(" timed out after ", maxsplit=1)[0]
        return _ci_status_for_query_timeout(
            conflicted=query.conflicted,
            pr_view_ok=query.pr_view_ok,
            label=label,
        )
    return observation, behind_probe


def gather_status(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    base_remote: str = "origin",
    base_ref: str = "main",
    empty_checks_grace: int = 0,
    sleep_fn: SleepFn = time.sleep,
    cwd: str | None = None,
    required: bool = False,
) -> CiStatus:
    """Port of ci status."""
    conflicted = True
    pr_view_ok = True
    try:
        pr_info = gh.pr_view(
            runner,
            pr,
            repo=repo,
            cwd=cwd,
            timeout=config.CI_STATUS_QUERY_TIMEOUT_SEC,
        )
    except gh.GhReadTimeout:
        return _ci_status_for_query_timeout(
            conflicted=True,
            pr_view_ok=False,
            label="gh pr view",
        )
    except Exception:  # pylint: disable=broad-except
        pr_info = None
        pr_view_ok = False
    if pr_info is not None:
        if pr_info.state.upper() == "MERGED":
            return CiStatus(status="merged", behind_count=0, failed_run_id=None, conflicted=False)
        conflicted = _conflicted_from_merge_state(pr_info.merge_state_status)

    gathered = _gather_git_checks_and_behind(runner=runner, query=_AfterPrViewQuery(
            pr=pr,
            repo=repo,
            base_remote=base_remote,
            base_ref=base_ref,
            empty_checks_grace=empty_checks_grace,
            sleep_fn=sleep_fn,
            cwd=cwd,
            required=required,
            conflicted=conflicted,
            pr_view_ok=pr_view_ok,
        ))
    if isinstance(gathered, CiStatus):
        return gathered
    observation, behind_probe = gathered
    if behind_probe.timed_out:
        return CiStatus(
            status="pending",
            behind_count=0,
            failed_run_id=observation.failed_run_id,
            conflicted=conflicted,
            pr_view_ok=pr_view_ok,
            checks_empty=observation.rollup_empty,
            checks_observed=observation.observed,
        )
    behind = behind_probe.count if behind_probe.count is not None else 0
    if behind > 0 and _squash_merge_race(
        runner,
        pr=pr,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    ):
        return CiStatus(
            status="merged",
            behind_count=0,
            failed_run_id=None,
            conflicted=False,
            checks_empty=observation.rollup_empty,
            checks_observed=observation.observed,
        )
    return CiStatus(
        status=observation.status,
        behind_count=behind,
        failed_run_id=observation.failed_run_id,
        conflicted=conflicted,
        pr_view_ok=pr_view_ok,
        checks_empty=observation.rollup_empty,
        checks_observed=observation.observed,
    )


def _coerce_status_failure(
    *, status: CiStatus,
    ci_failures: int,
) -> tuple[CiStatus, int, Decision | None]:
    """Track consecutive status failures: bail past the threshold, else degrade to pending."""
    if status.status and status.status != "error":
        return status, 0, None
    ci_failures += 1
    if ci_failures >= config.CI_MONITOR_STATUS_FAILURE_BAIL:
        return (
            CiStatus(status="error", behind_count=0, failed_run_id=None),
            ci_failures,
            Decision(action="bail", bail_reason=config.CI_WAIT_BAIL_STATUS_STALE),
        )
    degraded = CiStatus(
        status="pending",
        behind_count=status.behind_count,
        failed_run_id=status.failed_run_id,
        conflicted=status.conflicted,
        pr_view_ok=status.pr_view_ok,
        checks_empty=status.checks_empty,
        checks_observed=status.checks_observed,
    )
    return degraded, ci_failures, None


def _startup_deadline_step(
    status: CiStatus,
    *,
    active: bool,
    empty_since: float | None,
    deadline_sec: int,
    clock: ClockFn,
) -> tuple[bool, float | None, tuple[CiStatus, Decision] | None]:
    """Advance the empty-checks startup-deadline state machine for one poll.

    Returns the next (active, empty_since) state plus a terminal
    (status, decision) pair when the deadline elapses, else None.
    """
    if not active:
        return active, empty_since, None
    if status.checks_observed and status.checks_empty:
        now = clock()
        if empty_since is None:
            empty_since = now
        if now - empty_since >= deadline_sec:
            decision = Decision(
                action="bail",
                bail_reason=config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED,
            )
            terminal = CiStatus(
                status="NO_CHECKS",
                behind_count=status.behind_count,
                failed_run_id=status.failed_run_id,
                conflicted=status.conflicted,
                pr_view_ok=status.pr_view_ok,
                checks_empty=True,
                checks_observed=status.checks_observed,
            )
            return active, empty_since, (terminal, decision)
        return active, empty_since, None
    if status.checks_observed:
        return False, None, None
    return active, empty_since, None


def poll_ci(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    base_remote: str,
    base_ref: str,
    empty_checks_grace: int,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    empty_checks_startup_deadline_sec: int = 0,
    timeout: float = config.CI_WAIT_TIMEOUT_SEC,
    sleep_fn: SleepFn = time.sleep,
    clock: ClockFn = time.monotonic,
    cwd: str | None = None,
    required: bool = False,  # Callers that restrict to required checks must pass required=True.
) -> tuple[CiStatus, Decision]:
    """Port of ci wait poll loop."""
    max_polls = max(1, math.ceil(timeout / config.CI_WAIT_POLL_INTERVAL_SEC))
    checks = 0
    ci_failures = 0
    poll_interval = float(config.CI_WAIT_POLL_INTERVAL_SEC)
    started_at = clock()
    last_status = CiStatus(status="pending", behind_count=0, failed_run_id=None)
    startup_deadline_active = empty_checks_startup_deadline_sec > 0
    startup_empty_since: float | None = None

    def _emit_exit(*, label: str, decision: Decision) -> None:
        # Transition breadcrumb so the operator can see polling ended and why,
        # instead of a stale "poll N pending" being the last visible line (#5066).
        elapsed = max(0.0, clock() - started_at)
        suffix = f" ({decision.bail_reason})" if decision.bail_reason else ""
        _warn_stderr(
            f"ci_monitor: CI {label} after {elapsed:.0f}s -> {decision.action}{suffix}",
        )

    while True:
        if checks >= max_polls:
            decision = Decision(
                action="bail",
                bail_reason=config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED,
            )
            _emit_exit(label=last_status.status, decision=decision)
            return last_status, decision

        # Heartbeat before the in-flight status query so a hang inside
        # gather_status is visible (last line is "CI status query #N in
        # progress") rather than masquerading as a normal "poll N pending;
        # sleeping" line (#5066).
        query_elapsed = max(0.0, clock() - started_at)
        _warn_stderr(
            f"ci_monitor: CI status query #{checks + 1} in progress "
            f"after {query_elapsed:.0f}s",
        )
        status = gather_status(
            runner,
            pr=pr,
            repo=repo,
            base_remote=base_remote,
            base_ref=base_ref,
            empty_checks_grace=empty_checks_grace,
            sleep_fn=sleep_fn,
            cwd=cwd,
            required=required,
        )

        status, ci_failures, fail_decision = _coerce_status_failure(status=status, ci_failures=ci_failures)
        if fail_decision is not None:
            _emit_exit(label="error", decision=fail_decision)
            return status, fail_decision

        last_status = status

        if status.status == "NO_CHECKS":
            decision = Decision(
                action="bail",
                bail_reason=config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED,
            )
            _emit_exit(label="NO_CHECKS", decision=decision)
            return status, decision

        decision = decide(
            status,
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
        )
        if decision.action != "wait":
            _emit_exit(label=status.status, decision=decision)
            return status, decision

        startup_deadline_active, startup_empty_since, startup_terminal = _startup_deadline_step(
            status,
            active=startup_deadline_active,
            empty_since=startup_empty_since,
            deadline_sec=empty_checks_startup_deadline_sec,
            clock=clock,
        )
        if startup_terminal is not None:
            _emit_exit(label="NO_CHECKS", decision=startup_terminal[1])
            return startup_terminal

        checks += 1
        elapsed = max(0.0, clock() - started_at)
        _warn_stderr(
            f"ci_monitor: poll {checks}/{max_polls} pending after {elapsed:.0f}s; "
            f"sleeping {poll_interval:.0f}s",
        )
        iter_start = clock()
        sleep_fn(poll_interval)
        iter_delta = clock() - iter_start
        if iter_delta > _CI_SUSPEND_THRESHOLD_SEC:
            # A large real-time gap means the process was suspended (e.g. host
            # sleep) with time.monotonic paused; explain the non-advancing poll
            # counter instead of leaving it silent (#5066).
            _warn_stderr(
                f"ci_monitor: detected {iter_delta:.0f}s real-time gap during poll "
                f"{checks} (threshold {_CI_SUSPEND_THRESHOLD_SEC:.0f}s); probable "
                "host suspend, not counting this poll",
            )
            checks -= 1


def _parse_job_name_shard(raw_name: str) -> tuple[str, str, bool]:
    raw_name = logging_util.sanitize_diagnostic_line(raw_name)
    if not raw_name:
        return "", "", True
    match = _MATRIX_SLICE_RE.match(raw_name)
    if match:
        return match.group(1), match.group(2), False
    match = _MATRIX_ANY_RE.match(raw_name)
    if match:
        return match.group(1), "", False
    if _JOB_NAME_RE.match(raw_name):
        return raw_name, "", False
    return raw_name, "", True


def classify_failed_jobs(jobs: tuple[FailedJob, ...]) -> ClassifiedJobs:
    """Port of ci failed-jobs classification."""
    parsed: list[JobClass] = []
    fixable: list[JobClass] = []
    unfixable: list[JobClass] = []
    for job in jobs:
        sanitized = logging_util.sanitize_diagnostic_line(job.name)
        if not sanitized:
            continue
        name, shard, malformed = _parse_job_name_shard(sanitized)
        # Aggregator gate jobs (e.g. test-harnesses-gate) mirror their matrix and
        # have no local fix; skip them so a redundant gate failure does not force
        # local-unfixable when the underlying matrix leg is fixable.
        if name.endswith("-gate"):
            continue
        if malformed or not _JOB_NAME_RE.match(name):
            row = JobClass(name=name, shard=shard, klass="no-local-equivalent")
        elif name in config.CI_FIXABLE_JOBS:
            row = JobClass(name=name, shard=shard, klass="fixable")
        else:
            row = JobClass(name=name, shard=shard, klass="no-local-equivalent")
        parsed.append(row)
        if row.klass == "fixable" and not malformed and _JOB_NAME_RE.match(name):
            fixable.append(row)
        else:
            unfixable.append(row)
    return ClassifiedJobs(
        count=len(parsed),
        jobs=tuple(parsed),
        fixable=tuple(fixable),
        unfixable=tuple(unfixable),
    )


def read_failed_jobs(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None = None,
) -> tuple[tuple[FailedJob, ...], str]:
    """Parity wrapper over gh.failed_jobs_read."""
    result = gh.failed_jobs_read(runner, int(run_id), repo=repo, cwd=cwd)
    combined = result.stdout + result.stderr
    if result.returncode == 0:
        try:
            return gh.parse_failed_jobs_json(result.stdout), "ready"
        except Exception:  # pylint: disable=broad-except
            return (), "error"
    if _IN_PROGRESS_MSG in combined:
        return (), "in_progress"
    _warn_stderr(
        f"read_failed_jobs: gh run view jobs failed (exit {result.returncode}): "
        f"{combined.strip()}",
    )
    return (), "error"


def collect_failed_logs(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None = None,
) -> LogCollectResult:
    """Port of gh run-logs."""
    pointer = (
        f"--- CI log (run {run_id}, repo {repo}): last "
        f"{config.CI_MONITOR_LOG_TAIL_LINES} lines shown. "
        f"Full log: https://github.com/{repo}/actions/runs/{run_id} ---"
    )
    result = runner.run(
        ["gh", "run", "view", run_id, "--repo", repo, "--log-failed"],
        cwd=cwd,
    )
    combined = result.stdout + result.stderr
    lines = combined.splitlines()
    tail = lines[-config.CI_MONITOR_LOG_TAIL_LINES :]
    body = "\n".join(tail)
    if body and not body.endswith("\n"):
        body += "\n"
    text = f"{pointer}\n{body}" if body.strip() else pointer + "\n"
    text = redact.redact(text)
    if result.returncode != 0 and _IN_PROGRESS_MSG in combined:
        return LogCollectResult(text=text, state="in_progress")
    if result.returncode != 0:
        return LogCollectResult(text=text, state="error")
    return LogCollectResult(text=text, state="ready")


def is_transient_failed_log(logs: LogCollectResult) -> bool:
    """Return True when the log points at a transient network failure."""
    return logs.state == "ready" and retry.is_transient_net_signature(logs.text)


def rerun_failed(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None = None,
) -> RerunResult:
    """Port of ci rerun-failed."""
    result = gh.run_rerun(runner, int(run_id), repo=repo, failed_only=True, cwd=cwd)
    if result.returncode == 0:
        return RerunResult(submitted=True, already_running=False, error=None)
    combined = result.stdout + result.stderr
    if "already running" in combined.lower():
        return RerunResult(submitted=True, already_running=True, error=None)
    return RerunResult(
        submitted=False,
        already_running=False,
        error=f"gh run rerun failed (exit {result.returncode}): {combined.strip()}",
    )


def per_job_command(*, name: str, shard: str) -> tuple[str, ...] | None:
    """Port of _per_job_argv."""
    if name == "lint":
        return (
            "env",
            "SKIP=agnix,lint-mermaid-fences,shellcheck",
            "make",
            "lint-only",
        )
    if name == "lint-mermaid":
        return ("make", "lint-mermaid")
    if name == "shellcheck":
        return ("make", "shellcheck")
    if name == "test-harnesses":
        if shard.isdigit():
            return ("make", f"test-harnesses-{shard}")
        return ("make", "test-harnesses")
    if name == "agent-lint":
        return ("make", "agent-lint")
    if name == "agnix":
        return ("make", "agnix")
    if name == "agent-sync":
        return ("make", "agent-sync")
    if name == "python-lint":
        return ("make", "py-lint-main")
    if name == "python-pyright":
        return ("make", "py-typecheck")
    if name == "python-lint-duplicate-code":
        return ("make", "py-lint-duplicate-code")
    if name == "python-tests":
        return ("make", "py-test")
    return None


def prepare_python_toolchain(*, runner: Runner, name: str, cwd: str | None = None) -> bool:
    """Port of _prepare_python_job_toolchain."""
    if name in ("python-lint", "python-pyright", "python-lint-duplicate-code"):
        req = _REPO_ROOT / "python" / "requirements-dev.txt"
        if req.is_file():
            _ = runner.run(
                ["python3", "-m", "pip", "install", "-q", "-r", str(req)],
                cwd=cwd,
            )
        # Each split Python lint job verifies only the tools it runs.
        if name == "python-lint-duplicate-code":
            tools = ("pylint",)
        elif name == "python-pyright":
            tools = ("pyright",)
        else:
            tools = ("ruff", "pylint")
        for tool in tools:
            which = runner.run(["command", "-v", tool], cwd=cwd)
            if which.returncode != 0:
                return False
        return True
    if name == "python-tests":
        req = _REPO_ROOT / "python" / "requirements-test.txt"
        if req.is_file():
            _ = runner.run(
                ["python3", "-m", "pip", "install", "-q", "-r", str(req)],
                cwd=cwd,
            )
        which = runner.run(["command", "-v", "pytest"], cwd=cwd)
        return which.returncode == 0
    return True


def verify_job_locally(
    *, runner: Runner,
    name: str,
    shard: str,
    cwd: str | None = None,
) -> bool:
    argv = per_job_command(name=name, shard=shard)
    if argv is None:
        return False
    result = runner.run(list(argv), cwd=cwd)
    return result.returncode == 0


def _job_token(*, name: str, shard: str) -> str:
    if shard:
        return f"{name}-{shard}"
    return name


def _diff_name_only(
    runner: Runner,
    *,
    cached: bool = False,
    cwd: str | None = None,
) -> tuple[str, ...]:
    argv = ["git", "diff", "--name-only"]
    if cached:
        argv.append("--cached")
    result = runner.run(argv, cwd=cwd)
    if result.returncode != 0:
        return ()
    return tuple(line for line in result.stdout.splitlines() if line)


def _ls_untracked(runner: Runner, *, cwd: str | None = None) -> tuple[str, ...]:
    result = runner.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return ()
    return tuple(line for line in result.stdout.splitlines() if line)


def _capture_baseline(  # pyright: ignore[reportUnusedFunction]  # used by ci_agentic_fix
    runner: Runner,
    *,
    cwd: str | None,
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...], str]:
    tracked = _diff_name_only(runner, cwd=cwd)
    untracked = _ls_untracked(runner, cwd=cwd)
    staged = _diff_name_only(runner, cached=True, cwd=cwd)
    head = git.rev_parse(runner, "HEAD", cwd=cwd)
    return tracked, untracked, staged, head


def _implement_tmpdir() -> str | None:
    raw = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "").strip()
    return raw or None


def _run_pre_push_log_refresh(callback: PrePushLogRefreshFn | None) -> bool:
    if callback is None:
        return False
    try:
        return bool(callback())
    except Exception as exc:  # pylint: disable=broad-exception-caught
        detail = logging_util.sanitize_diagnostic_line(redact.redact(str(exc)))
        _warn_stderr(f"ship-pr: pre-push log refresh callback failed: {detail}")
        return False


def _warn_refresh_skip_before_ci_push(*, skip: run_logs.RefreshSkip, warning_logged: bool) -> bool:
    if skip.skipped and warning_logged:
        reason = skip.reason or "unknown"
        if skip.error:
            reason = f"{reason}: {logging_util.sanitize_diagnostic_line(skip.error)}"
        if skip.reason == config.REFRESH_SKIP_NO_LOGS_COMMIT:
            _warn_stderr(
                f"ship-pr: run-log refresh skipped before CI-fix push: {reason} "
                "(warning cannot be committed)"
            )
            return True
        _warn_stderr(f"ship-pr: run-log refresh skipped before CI-fix push: {reason}")
        return False
    if skip.skipped and skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED:
        _warn_stderr("ship-pr: run-log refresh skipped before force-push: manifest recovery failed")
        return False
    return True


def _refresh_run_logs_before_ci_push(
    *,
    runner: Runner,
    ctx: RunContext | None,
    cwd: str | None,
    warning_logged: bool,
    refresh_required: bool,
) -> bool:
    if not refresh_required:
        return True
    if ctx is None:
        if warning_logged:
            _warn_stderr("ship-pr: run-log refresh skipped before CI-fix push: missing run context")
            return False
        return True
    try:
        skip = run_logs.flush_logs_pre(runner=runner, ctx=ctx.with_(state_file=None), cwd=cwd)
    except (OSError, ShipError) as exc:
        if warning_logged:
            detail = logging_util.sanitize_diagnostic_line(redact.redact(str(exc)))
            _warn_stderr(f"ship-pr: run-log refresh failed before CI-fix push: {detail}")
            return False
        return True
    return _warn_refresh_skip_before_ci_push(skip=skip, warning_logged=warning_logged)


def _refresh_before_stage_push(
    *,
    runner: Runner,
    context: StagePushContext | None,
    cwd: str | None,
    did_rebase: bool,
    ci_fix_rebase_pending: bool,
) -> bool:
    pre_push_log_refresh = context.pre_push_log_refresh if context is not None else None
    ctx = context.run_context if context is not None else None
    warning_logged = _run_pre_push_log_refresh(pre_push_log_refresh)
    return _refresh_run_logs_before_ci_push(
        runner=runner,
        ctx=ctx,
        cwd=cwd,
        warning_logged=warning_logged,
        refresh_required=did_rebase or ci_fix_rebase_pending or warning_logged,
    )


def _resolve_plan_file(plan_file: str | None) -> str | None:
    if not plan_file:
        return None
    tmpdir = _implement_tmpdir()
    if tmpdir is None:
        return None
    try:
        impl_abs = Path(tmpdir).resolve()
        path_abs = Path(plan_file).resolve()
        _ = path_abs.relative_to(impl_abs)
    except (OSError, ValueError):
        return None
    if not path_abs.is_file():
        return None
    return str(path_abs)


def _path_unsafe_for_rollback(path: str) -> bool:
    return any(part == ".." for part in path.split("/"))


def _is_submodule_gitlink(*, runner: Runner, path: str, cwd: str | None) -> bool:
    result = runner.run(["git", "ls-files", "--stage", "--", path], cwd=cwd)
    if result.returncode != 0:
        return False
    return any(line.startswith("160000 ") for line in result.stdout.splitlines())


def _rollback_to_baseline(  # pyright: ignore[reportUnusedFunction]  # used by ci_agentic_fix
    runner: Runner,
    *,
    baseline_tracked: tuple[str, ...],
    baseline_untracked: tuple[str, ...],
    baseline_staged: tuple[str, ...],
    cwd: str | None,
) -> None:
    tracked_now = _diff_name_only(runner, cwd=cwd)
    untracked_now = _ls_untracked(runner, cwd=cwd)
    staged_now = _diff_name_only(runner, cached=True, cwd=cwd)
    baseline_tracked_set = set(baseline_tracked)
    baseline_untracked_set = set(baseline_untracked)
    baseline_staged_set = set(baseline_staged)
    for path in tracked_now:
        if path in baseline_tracked_set:
            continue
        if _path_unsafe_for_rollback(path) or _is_submodule_gitlink(runner=runner, path=path, cwd=cwd):
            continue
        _ = runner.run(["git", "checkout", "--", path], cwd=cwd)
    for path in untracked_now:
        if path in baseline_untracked_set:
            continue
        if _path_unsafe_for_rollback(path):
            continue
        _ = runner.run(["rm", "-f", "--", path], cwd=cwd)
    for path in staged_now:
        if path in baseline_staged_set:
            continue
        if _path_unsafe_for_rollback(path) or _is_submodule_gitlink(runner=runner, path=path, cwd=cwd):
            continue
        _ = runner.run(["git", "restore", "--staged", "--", path], cwd=cwd)
        if path not in baseline_tracked_set and path not in baseline_untracked_set:
            _ = runner.run(["rm", "-f", "--", path], cwd=cwd)


def _delta_paths(  # pyright: ignore[reportUnusedFunction]  # used by ci_agentic_fix
    runner: Runner,
    *,
    baseline_tracked: tuple[str, ...],
    baseline_untracked: tuple[str, ...],
    cwd: str | None,
) -> tuple[str, ...]:
    tracked_now = _diff_name_only(runner, cwd=cwd)
    untracked_now = _ls_untracked(runner, cwd=cwd)
    baseline_tracked_set = set(baseline_tracked)
    baseline_untracked_set = set(baseline_untracked)
    delta: set[str] = set()
    for path in tracked_now:
        if path not in baseline_tracked_set:
            delta.add(path)
    for path in untracked_now:
        if path not in baseline_untracked_set:
            delta.add(path)
    return tuple(sorted(delta))


def _resolve_launcher_exit(
    *,
    combined: str,
    output: str | Path,
    process_rc: int = 0,
) -> int:
    """Prefer the launcher `.done` sentinel; failed wrappers without metadata fail closed."""
    return agents.resolve_launcher_exit(
        captured_text=combined,
        output_file=output,
        process_rc=process_rc,
    )


def _available_tiers() -> tuple[str, ...]:  # pyright: ignore[reportUnusedFunction]
    return external_defaults.tool_order("implement.ci_recovery_fixer")


def _write_failure_log(text: str, *, tmpdir: str | None = None) -> str | None:
    if not text.strip():
        return None
    root = Path(tmpdir) if tmpdir else Path(tempfile.gettempdir())
    root.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(suffix=".redacted.log", dir=str(root))
    os.close(fd)
    redacted = redact.redact(text)
    log_path = Path(path)
    _ = log_path.write_text(redacted, encoding="utf-8")
    log_path.chmod(0o600)
    return path


def _on_named_branch(runner: Runner, *, cwd: str | None) -> bool:
    result = runner.run(["git", "symbolic-ref", "--quiet", "HEAD"], cwd=cwd)
    return result.returncode == 0


def _outer_backoff_seconds(attempt_index: int) -> float:
    base = 2 * (2 ** max(0, attempt_index - 1))
    return max(1.0, float(base))


def _wait_for_ci_ready(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None = None,
    sleep_fn: SleepFn = time.sleep,
    clock: ClockFn = time.monotonic,
) -> LogCollectResult:
    """Poll collect_failed_logs every CI_MONITOR_IN_PROGRESS_POLL_INTERVAL seconds
    until the run is no longer in_progress, or CI_MONITOR_IN_PROGRESS_TIMEOUT elapses.
    """
    deadline = clock() + config.CI_MONITOR_IN_PROGRESS_TIMEOUT
    while True:
        remaining = deadline - clock()
        if remaining <= 0:
            return collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
        sleep_fn(min(config.CI_MONITOR_IN_PROGRESS_POLL_INTERVAL, float(remaining)))
        logs = collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
        if logs.state != "in_progress":
            return logs


def _make_default_launch_fn(  # pyright: ignore[reportUnusedFunction]
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    plan_file: str | None,
    logs: LogCollectResult,
    output_dir: str | None,
    cwd: str | None,
    failure_log_paths: list[str],
) -> LaunchFn:
    implement_tmpdir = _implement_tmpdir()
    failure_log_path: str | None = None
    if logs.state == "ready" and logs.text.strip():
        failure_log_path = _write_failure_log(logs.text, tmpdir=implement_tmpdir)
        if failure_log_path is not None:
            failure_log_paths.append(failure_log_path)
    prefix = output_dir or implement_tmpdir or tempfile.gettempdir()
    safe_plan = _resolve_plan_file(plan_file)
    seen_token_records: set[str] = set()

    def launch_fn(tier: str) -> TierAttempt:
        tier_out = str(Path(prefix) / f"ci-fix-{tier}.out")
        if tier in {"codex", "cursor"}:
            Path(f"{tier_out}.token-record").unlink(missing_ok=True)
        argv = agents.build_launch_argv(
            tier,
            role=config.CI_FIX_ROLE,
            output=tier_out,
            run_id=run_id,
            repo=repo,
            plan_file=safe_plan,
            failure_log=failure_log_path,
            timeout_sec=config.SUBPROCESS_DEFAULT_TIMEOUT_SEC,
        )
        result = runner.run(
            argv,
            timeout=float(config.SUBPROCESS_DEFAULT_TIMEOUT_SEC),
            cwd=cwd,
        )
        combined = result.stdout + result.stderr
        _ = agents.ingest_launcher_token_sidecar(
            runner,
            launcher_stdout=combined,
            output=tier_out,
            tmpdir=implement_tmpdir,
            implement_tmpdir=implement_tmpdir,
            seen=seen_token_records,
            cwd=cwd,
            allow_output_fallback=tier in {"codex", "cursor"},
        )
        launcher_exit = _resolve_launcher_exit(
            combined=combined,
            output=tier_out,
            process_rc=result.returncode,
        )
        failure = agents.classify_launch_failure(
            launcher_exit=launcher_exit,
            sidecar=tier_out,
            tool=tier,  # type: ignore[arg-type]
            output_file=tier_out,
        )
        return TierAttempt(
            tier=tier,
            wrapper_rc=result.returncode,
            launcher_exit=launcher_exit,
            failure=failure,
            failure_log=tier_out,
        )

    return launch_fn


def stage_and_push(
    runner: Runner,
    *,
    cwd: str | None,
    commit_label: str,
    delta_paths: tuple[str, ...],
    base_remote: str = "origin",
    base_ref: str = "main",
    ci_fix_rebase_pending: bool = False,
    context: StagePushContext | None = None,
) -> tuple[bool, str | None, tuple[str, ...], bool, bool]:
    """Stage delta paths, commit, then push; force-push only after a rebase."""
    classified = context.classified if context is not None else None
    head: str | None
    branch: str
    did_rebase = False
    if delta_paths:
        for path in delta_paths:
            _ = runner.run(["git", "add", "--", path], cwd=cwd)
        commit_msg = f"Apply CI fixes ({commit_label})"
        commit = git.commit_with_trailer(
            runner,
            commit_msg,
            no_trailer=True,
            cwd=cwd,
        )
        if commit.returncode != 0:
            return False, None, delta_paths, False, ci_fix_rebase_pending
        head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
        branch = git.current_branch(runner, cwd=cwd) if head else "HEAD"
    elif ci_fix_rebase_pending:
        head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
        branch = git.current_branch(runner, cwd=cwd) if head else "HEAD"
    else:
        return False, None, (), False, ci_fix_rebase_pending
    if not ci_fix_rebase_pending:
        try:
            fetch = git.fetch(runner, base_remote, base_ref, cwd=cwd)
        except AssertionError:
            return False, head, delta_paths, False, ci_fix_rebase_pending
        if fetch.returncode != 0:
            return False, head, delta_paths, False, ci_fix_rebase_pending
        try:
            behind = runner.run(["git", "rev-list", "--count", f"HEAD..{base_remote}/{base_ref}"], cwd=cwd)
        except AssertionError:
            return False, head, delta_paths, False, ci_fix_rebase_pending
        try:
            behind_count = int((behind.stdout or "0").strip())
        except ValueError:
            behind_count = 0
        if behind.returncode == 0 and behind_count > 0:
            known_failed_jobs = classified is not None and classified.count > 0
            if not known_failed_jobs:
                _warn_stderr("ship-pr: behind main but failed-jobs unknown; skipping defer-rebase")
            else:
                rebased = rebase.rebase_push(
                    runner,
                    no_push=True,
                    keep_on_conflict=True,
                    base_remote=base_remote,
                    base_ref=base_ref,
                    cwd=cwd,
                )
                did_rebase = rebased.exit_code == 0
                if not did_rebase:
                    if rebased.conflict_files:
                        return False, head, delta_paths, False, True
                    _ = git.rebase(runner, "--abort", cwd=cwd)
                    return False, head, delta_paths, False, False
    if did_rebase or ci_fix_rebase_pending:
        if ci_fix_rebase_pending and not (classified and classified.fixable):
            _warn_stderr("ship-pr: pending CI-fix rebase lacks local verification targets; preserving pending retry")
            return False, head, delta_paths, did_rebase, True
        if (did_rebase or ci_fix_rebase_pending) and classified and classified.fixable:
            failed_verify = [
                _job_token(name=job.name, shard=job.shard)
                for job in classified.fixable
                if not verify_job_locally(runner=runner, name=job.name, shard=job.shard, cwd=cwd)
            ]
            if failed_verify:
                return False, head, delta_paths, did_rebase, False
    if not _refresh_before_stage_push(
        runner=runner,
        context=context,
        cwd=cwd,
        did_rebase=did_rebase,
        ci_fix_rebase_pending=ci_fix_rebase_pending,
    ):
        return False, head, delta_paths, did_rebase, did_rebase or ci_fix_rebase_pending
    if did_rebase or ci_fix_rebase_pending:
        remote = runner.run(
            ["git", "ls-remote", "--exit-code", "--heads", "origin", branch],
            cwd=cwd,
        )
        expected_remote_oid = ""
        if remote.returncode == 0:
            fields = remote.stdout.split()
            expected_remote_oid = fields[0] if fields else ""
        if not expected_remote_oid:
            _warn_stderr("ship-pr: remote branch OID unavailable after CI-fix rebase; preserving pending retry")
            return False, head, delta_paths, did_rebase, did_rebase or ci_fix_rebase_pending
        force = git.force_push_recovery(
            runner,
            branch=branch,
            remote="origin",
            expected_remote_oid=expected_remote_oid,
            cwd=cwd,
        )
        pushed = force.pushed
    else:
        push = git.push(runner, "origin", branch, cwd=cwd)
        pushed = push.returncode == 0
    sha = git.try_rev_parse(runner, "HEAD", cwd=cwd) if pushed else head
    pending = (did_rebase or ci_fix_rebase_pending) and not pushed
    return pushed, sha, delta_paths, did_rebase, pending


def run_ci_fix(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    classified: ClassifiedJobs,
    logs: LogCollectResult,
    plan_file: str | None,
    cwd: str | None,
    launch_fn: LaunchFn | None = None,
    output_dir: str | None = None,
    base_remote: str = "origin",
    base_ref: str = "main",
    ci_fix_rebase_pending: bool = False,
    ctx: RunContext | None = None,
) -> FixResult:
    """Retry a pending CI-fix rebase push; normal fixing is delegated."""
    def _pin_or_invalidate_guidelines_before_push() -> bool:
        if ctx is None:
            return False
        head_sha = git.try_rev_parse(runner, "HEAD", cwd=cwd) or ""
        return ship_guidelines._pin_or_invalidate_guidelines_note(  # noqa: SLF001  # pyright: ignore[reportPrivateUsage]
            implement_tmpdir=ctx.tmpdir,
            head_sha=head_sha,
            base_ref=f"{base_remote}/{base_ref}",
            repo_root=cwd,
        )

    if ci_fix_rebase_pending:
        pushed, _post_head, delta_paths, did_rebase, pending = stage_and_push(
            runner,
            cwd=cwd,
            commit_label="pending-retry",
            delta_paths=(),
            base_remote=base_remote,
            base_ref=base_ref,
            ci_fix_rebase_pending=True,
            context=StagePushContext(
                classified=classified,
                run_context=ctx,
                pre_push_log_refresh=_pin_or_invalidate_guidelines_before_push,
            ),
        )
        if not pushed:
            return FixResult(
                status="waterfall-failed",
                detail="push failed",
                did_rebase=did_rebase,
                ci_fix_rebase_pending=pending,
            )
        return FixResult(
            status="pushed",
            delta_paths=delta_paths,
            did_rebase=did_rebase,
            ci_fix_rebase_pending=False,
        )
    _ = run_id, repo, classified, logs, plan_file, launch_fn, output_dir, base_remote, base_ref, ctx
    return FixResult(
        status="waterfall-failed",
        detail="run_ci_fix: non-pending calls not supported",
    )


def _fix_exhausted_detail(
    *, classified: ClassifiedJobs | None,
    logs: LogCollectResult | None,
) -> str:
    """Compose the diagnostic detail surfaced when the CI-fix loop exhausts.

    Carries the stable ``ci-fix-exhausted`` reason token, the failing job
    name(s), and the already-redacted CI log tail for Step 12d operator bail.
    The job names come from the closed CI-job enum and the log tail is redacted
    upstream in ``collect_failed_logs``.
    """
    jobs = ""
    if classified is not None:
        jobs = ", ".join(_job_token(name=job.name, shard=job.shard) for job in classified.jobs)
    header = f"ci-fix-exhausted: {jobs}" if jobs else "ci-fix-exhausted"
    tail = logs.text if logs is not None and logs.state == "ready" else ""
    if tail.strip():
        return f"{header}\n{redact.redact(tail).rstrip()}\n"
    return header


def _agentic_output_dir(ctx: RunContext | None) -> str:
    if ctx is not None and ctx.tmpdir:
        path = Path(ctx.tmpdir) / "ci-agentic-fix"
    else:
        path = Path(tempfile.gettempdir()) / "ci-agentic-fix"
    path.mkdir(parents=True, exist_ok=True)
    return str(path)


def _read_push_checkpoint_from_ctx(*, ctx: RunContext | None, expected_run_id: str = "") -> dict[str, str] | None:
    path = Path(_agentic_output_dir(ctx)) / "ci-agentic-push-checkpoint.latest"
    if not path.is_file():
        return None
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        key, sep, value = line.partition("=")
        if sep and key:
            values[key] = value.strip()
    if expected_run_id:
        checkpoint_run_id = values.get("RUN_ID", "")
        if checkpoint_run_id != expected_run_id:
            return None
    return values


def _parse_kv_output(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text, strip_value=True, skip_empty_key=True)


def _agentic_fix_delegate_timeout_sec() -> float | None:
    """Budget all delegate cycles, passive CI waits, and local verification."""
    verify_slots = len(config.CI_FIXABLE_JOBS)
    per_cycle = (
        config.CI_WAIT_TIMEOUT_SEC
        + config.SUBPROCESS_DEFAULT_TIMEOUT_SEC
        + verify_slots * config.SUBPROCESS_DEFAULT_TIMEOUT_SEC
    )
    return float(config.CI_AGENTIC_FIX_MAX_CYCLES * per_cycle)


def _agentic_fix_result(
    runner: Runner,
    *,
    pr: int,
    run_id: str,
    repo: str,
    plan_file: str | None,
    cwd: str | None,
    base_remote: str,
    base_ref: str,
    ctx: RunContext | None,
) -> FixResult:
    if cwd is None:
        return FixResult(status="waterfall-failed", detail="missing repo_root")
    implement_tmpdir = ctx.tmpdir if ctx is not None and ctx.tmpdir else os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not implement_tmpdir:
        return FixResult(status="waterfall-failed", detail="missing implement_tmpdir")
    argv = [
        sys.executable,
        str(_REPO_ROOT / "python" / "cli.py"),
        "ci",
        "agentic-fix",
        "--pr",
        str(pr),
        "--repo",
        repo,
        "--repo-root",
        cwd,
        "--run-id",
        run_id,
        "--base-remote",
        base_remote,
        "--base-ref",
        base_ref,
        "--output-dir",
        _agentic_output_dir(ctx),
        "--max-cycles",
        str(config.CI_AGENTIC_FIX_MAX_CYCLES),
        "--implement-tmpdir",
        implement_tmpdir,
    ]
    if plan_file:
        argv.extend(["--plan-file", plan_file])
    if ctx is not None and ctx.state_file:
        argv.extend(["--state-file", ctx.state_file])
    if ctx is not None and ctx.no_logs_commit:
        argv.append("--no-logs-commit")
    result = runner.run(argv, cwd=cwd, timeout=_agentic_fix_delegate_timeout_sec())
    if result.returncode == config.EXIT_TIMEOUT:
        checkpoint = _read_push_checkpoint_from_ctx(ctx=ctx, expected_run_id=run_id)
        if checkpoint is not None:
            pending = checkpoint.get("CI_FIX_REBASE_PENDING", "").lower() == "true"
            delta_paths = tuple(
                path for path in checkpoint.get("DELTA_PATHS", "").split(",") if path
            )
            detail = checkpoint.get("DETAIL", "") or "delegate-timeout-after-push"
            if pending:
                return FixResult(
                    status="pushed",
                    winning_tier="claude",
                    delta_paths=delta_paths,
                    detail=detail,
                    ci_fix_rebase_pending=True,
                )
            return FixResult(
                status="pushed",
                winning_tier="claude",
                delta_paths=delta_paths,
                detail=detail,
            )
        return FixResult(
            status="fix-exhausted",
            detail="ci-fix-exhausted: delegate-timeout",
        )
    parsed = _parse_kv_output(result.stdout)
    status = parsed.get("STATUS", "")
    detail = parsed.get("DETAIL", "")
    exhausted_detail_file = parsed.get("EXHAUSTED_DETAIL_FILE", "")
    if status in {"ci-fix-exhausted", "local-unfixable"} and exhausted_detail_file:
        detail_path = Path(exhausted_detail_file)
        if detail_path.is_file():
            detail = detail_path.read_text(encoding="utf-8", errors="replace").strip()
    fix_attempted = parsed.get("FIX_ATTEMPTED", "").lower() == "true"
    delta_paths = tuple(path for path in parsed.get("DELTA_PATHS", "").split(",") if path)
    pending = parsed.get("CI_FIX_REBASE_PENDING", "").lower() == "true"
    if status in {"passed", "pushed"}:
        return FixResult(status="pushed", winning_tier="claude", delta_paths=delta_paths)
    if status == "rebase-required":
        return FixResult(
            status="pushed",
            winning_tier="claude",
            delta_paths=delta_paths,
            detail=detail,
            ci_fix_rebase_pending=True,
        )
    if status == "local-unfixable":
        if fix_attempted:
            exhausted_detail = detail if detail.startswith("ci-fix-exhausted") else f"ci-fix-exhausted: {detail}"
            return FixResult(status="fix-exhausted", detail=exhausted_detail)
        prefixed = detail if detail.startswith("local-unfixable:") else f"local-unfixable: {detail}"
        return FixResult(status="local-unfixable", detail=prefixed)
    if status == "first-fixer-non-health":
        return FixResult(status="first-fixer-non-health", detail=detail)
    if status == "ci-fix-exhausted":
        exhausted_detail = detail if detail.startswith("ci-fix-exhausted") else f"ci-fix-exhausted: {detail}"
        return FixResult(status="fix-exhausted", detail=exhausted_detail)
    if status == "waterfall-failed":
        if detail == "head-changed" and fix_attempted:
            return FixResult(status="fix-exhausted", detail=f"ci-fix-exhausted: {detail}")
        return FixResult(status="waterfall-failed", detail=detail, ci_fix_rebase_pending=pending)
    return FixResult(status="waterfall-failed", detail="malformed agentic-fix output")


def evaluate_failure(
    runner: Runner,
    *,
    pr: int = 0,
    run_id: str,
    repo: str,
    plan_file: str | None,
    transient_retries: int,
    _fix_attempts: int,
    cwd: str | None,
    launch_fn: LaunchFn | None = None,
    sleep_fn: SleepFn = time.sleep,
    base_remote: str = "origin",
    base_ref: str = "main",
    ci_fix_rebase_pending: bool = False,
    ctx: RunContext | None = None,
    clock: ClockFn = time.monotonic,
) -> FixResult:
    """Port of run_evaluate_failure outer loop."""
    if not run_id or not str(run_id).strip():
        return FixResult(status="waterfall-failed", detail="missing run_id")

    upfront_logs = collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
    if upfront_logs.state == "in_progress":
        upfront_logs = _wait_for_ci_ready(
            runner,
            run_id=run_id,
            repo=repo,
            cwd=cwd,
            sleep_fn=sleep_fn,
            clock=clock,
        )
        if upfront_logs.state == "in_progress":
            return FixResult(
                status="ci-still-in-progress",
                detail=(
                    f"CI run {run_id} still in progress after "
                    f"{config.CI_MONITOR_IN_PROGRESS_TIMEOUT}s"
                ),
            )
    upfront_ready_stash: LogCollectResult | None = None
    blind_rerun_attempted = False
    if (
        transient_retries < config.CI_MONITOR_TRANSIENT_RERUN_MAX
        and is_transient_failed_log(upfront_logs)
    ):
        blind_rerun_attempted = True
        rerun = rerun_failed(runner, run_id=run_id, repo=repo, cwd=cwd)
        if rerun.submitted and not rerun.already_running:
            return FixResult(status="no-changes")
        if rerun.submitted and rerun.already_running:
            return FixResult(status="no-changes", rerun_already_running=True)
        if rerun.error:
            _warn_stderr(
                f"evaluate_failure: transient rerun failed: {rerun.error}; continuing to fix loop",
            )
    if upfront_logs.state == "ready" and not blind_rerun_attempted:
        upfront_ready_stash = upfront_logs

    if not ci_fix_rebase_pending:
        if not _on_named_branch(runner, cwd=cwd):
            return FixResult(
                status="waterfall-failed",
                detail="evaluate_failure: detached HEAD",
            )
        return _agentic_fix_result(
            runner,
            pr=pr,
            run_id=run_id,
            repo=repo,
            plan_file=plan_file,
            cwd=cwd,
            base_remote=base_remote,
            base_ref=base_ref,
            ctx=ctx,
        )

    last_classified: ClassifiedJobs | None = None
    last_logs: LogCollectResult | None = None
    for attempt in range(1, config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS + 1):
        if not _on_named_branch(runner, cwd=cwd):
            return FixResult(
                status="waterfall-failed",
                detail="evaluate_failure: detached HEAD",
            )
        if ci_fix_rebase_pending:
            pending_classified = last_classified
            pending_logs = last_logs
            if pending_classified is None:
                jobs_raw, jobs_state = read_failed_jobs(
                    runner,
                    run_id=run_id,
                    repo=repo,
                    cwd=cwd,
                )
                if jobs_state == "ready":
                    pending_classified = classify_failed_jobs(jobs_raw)
            if pending_logs is None:
                pending_logs = upfront_ready_stash or upfront_logs
            pending_fix = run_ci_fix(
                runner,
                run_id=run_id,
                repo=repo,
                classified=pending_classified or ClassifiedJobs(0, (), (), ()),
                logs=pending_logs or LogCollectResult(text="", state="ready"),
                plan_file=plan_file,
                cwd=cwd,
                launch_fn=launch_fn,
                base_remote=base_remote,
                base_ref=base_ref,
                ci_fix_rebase_pending=True,
                ctx=ctx,
            )
            if pending_fix.status == "pushed":
                return pending_fix
            if pending_fix.ci_fix_rebase_pending:
                if attempt < config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS:
                    sleep_fn(_outer_backoff_seconds(attempt))
                    continue
                return pending_fix
            return pending_fix
    return FixResult(status="fix-exhausted", detail=_fix_exhausted_detail(classified=last_classified, logs=last_logs))


def monitor(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    base_remote: str = "origin",
    base_ref: str = "main",
    empty_checks_grace: int = 0,
    empty_checks_startup_deadline_sec: int = 0,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    ci_fix_rebase_pending: bool = False,
    cwd: str | None = None,
    sleep_fn: SleepFn = time.sleep,
    clock: ClockFn = time.monotonic,
) -> MonitorResult:
    """Driver entrypoint for CI monitor loop.

    On a failed-CI decision the loop hands off to the main agent immediately
    (``first-fixer-non-health``) without downloading logs, classifying
    transients, rerunning, or launching the agentic fix sub-process; the
    inline-fix parameters (``plan_file``, ``launch_fn``, ``ctx``,
    ``transient_retries``) were removed with that behavior.
    """
    status, decision = poll_ci(
        runner,
        pr=pr,
        repo=repo,
        base_remote=base_remote,
        base_ref=base_ref,
        empty_checks_grace=empty_checks_grace,
        empty_checks_startup_deadline_sec=empty_checks_startup_deadline_sec,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        sleep_fn=sleep_fn,
        clock=clock,
        cwd=cwd,
    )

    def _base_result(
        *,
        goto: bool,
        step: StepResult,
        rerun_already_running: bool = False,
        transient_rerun_attempted: bool = False,
        pending: bool = ci_fix_rebase_pending,
    ) -> MonitorResult:
        return MonitorResult(
            action=decision.action,
            ci_status=status.status,
            behind_count=status.behind_count,
            failed_run_id=status.failed_run_id,
            goto_rebase=goto,
            iterations=iteration,
            result=step,
            rerun_already_running=rerun_already_running,
            transient_rerun_attempted=transient_rerun_attempted,
            ci_fix_rebase_pending=pending,
        )

    if decision.action in ("merge", "already_merged"):
        return _base_result(
            goto=False,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action == "rebase":
        return _base_result(
            goto=True,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action in ("evaluate_failure", "rebase_then_evaluate"):
        if decision.action == "rebase_then_evaluate":
            return _base_result(
                goto=True,
                step=StepResult(outcome=Outcome.OK),
            )
        # CI reached terminal status with at least one failed check and no rebase
        # is needed. Bail immediately to the main agent instead of downloading
        # failure logs, classifying transient failures, rerunning, or launching
        # the agentic fix sub-process: the main agent re-reads and re-analyzes the
        # CI failure on takeover, so any analysis done here is redundant latency
        # (observed ~30 min in a real run). The main agent uses failed_run_id, or
        # the `pr checks` fallback when it is empty, to read the failure itself.
        return _base_result(
            goto=False,
            step=StepResult(
                outcome=Outcome.NEEDS_USER_INPUT,
                detail="first-fixer-non-health",
            ),
        )

    if decision.action == "bail":
        if decision.bail_reason and retry.is_transient_net_signature(decision.bail_reason):
            return _base_result(
                goto=False,
                step=StepResult(
                    outcome=Outcome.TRANSIENT,
                    detail=decision.bail_reason,
                ),
            )
        if decision.bail_reason == "fix-attempts-exhausted":
            return _base_result(
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail=decision.bail_reason,
                ),
            )
        return _base_result(
            goto=False,
            step=StepResult(
                outcome=Outcome.STALLED,
                detail=decision.bail_reason or "bail",
            ),
        )

    return _base_result(
        goto=False,
        step=StepResult(outcome=Outcome.STALLED, detail=decision.action),
    )
