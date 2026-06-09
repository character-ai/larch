"""CI monitor loop: poll, classify, collect logs, fixer waterfall, GOTO-Rebase signal."""

from __future__ import annotations

import json
import math
import os
import re
import tempfile
import time
from collections.abc import Callable
from contextlib import suppress
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import agents
import config
import gh
import git
import logging_util
import rebase
import redact
import retry
import run_logs
from agents import TierAttempt
from errors import ShipError
from gh import FailedJob
from outcomes import Outcome, StepResult
from proc import CommandResult, Runner
from run_context import RunContext

_IN_PROGRESS_MSG = "is still in progress; logs will be available"
_CI_SUSPEND_THRESHOLD_SEC = 60.0
_RUN_ID_RE = re.compile(r"runs/(\d+)")
_MATRIX_SHARD_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s+\((\d+)\)$")
_MATRIX_ANY_RE = re.compile(r"^([A-Za-z][A-Za-z0-9_-]*)\s+\(([^)]*)\)$")
_JOB_NAME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_-]*$")
_REPO_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS_DIR = _REPO_ROOT / "scripts"
_LAUNCHER_EXIT_RE = re.compile(r"^LAUNCHER_EXIT=(\d+)", re.MULTILINE)

SleepFn = Callable[[float], None]
ClockFn = Callable[[], float]
LaunchFn = Callable[[str], TierAttempt]


@dataclass(frozen=True)
class CiStatus:
    status: str
    behind_count: int
    failed_run_id: str | None
    conflicted: bool = False


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
    did_fixing: bool
    goto_rebase: bool
    iterations: int
    result: StepResult
    rerun_already_running: bool = False
    transient_rerun_attempted: bool = False
    ci_fix_rebase_pending: bool = False


def _conflicted_from_merge_state(merge_state: str | None) -> bool:
    """Mirror ci-status.sh CONFLICTED derivation (conservative for UNKNOWN/empty)."""
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
    """Pure port of ci-decide.sh decision matrix."""
    if status.status == "merged":
        return Decision(action="already_merged")
    if status.status == "error":
        return Decision(
            action="bail",
            bail_reason="ci-status.sh returned error — check script arguments",
        )
    behind = status.behind_count > 0
    if status.status == "pass" and (not behind or not status.conflicted):
        return Decision(action="merge")
    if iteration >= config.CI_MONITOR_MAX_ITERATIONS:
        return Decision(
            action="bail",
            bail_reason="Timeout: 50 iterations (~25 minutes) without successful merge",
        )
    if rebase_count >= config.CI_MONITOR_MAX_REBASES:
        return Decision(
            action="bail",
            bail_reason="Too many rebases (20) without converging — main branch too active",
        )
    if fix_attempts >= config.CI_MONITOR_MAX_FIX_ATTEMPTS:
        return Decision(action="bail", bail_reason="fix-attempts-exhausted")
    if status.status == "pending":
        return Decision(action="rebase" if behind else "wait")
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
) -> CommandResult:
    return runner.run(
        [
            "gh",
            "pr",
            "checks",
            str(pr),
            "--repo",
            repo,
            "--json",
            "name,state,bucket,link",
        ],
        cwd=cwd,
    )


def _warn_stderr(message: str) -> None:
    logging_util.BreadcrumbWriter().emit(message)


def _behind_count(
    runner: Runner,
    *,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> int | None:
    base = f"{base_remote}/{base_ref}"
    result = runner.run(
        ["git", "rev-list", "--count", f"HEAD..{base}"],
        cwd=cwd,
    )
    if result.returncode != 0:
        _warn_stderr(
            "gather_status: git rev-list --count failed; treating branch as pending",
        )
        return None
    text = result.stdout.strip() or "0"
    try:
        return int(text)
    except ValueError:
        _warn_stderr(
            "gather_status: git rev-list --count returned non-integer; treating as pending",
        )
        return None


def behind_count(
    runner: Runner,
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
    fetch: bool = True,
    cwd: str | None = None,
) -> int:
    """Public ci-behind-count parity: validate labels, fail open to 0."""
    if git.validate_base_remote_ref(base_remote, base_ref) is not None:
        return 0
    if fetch:
        fetched = git.fetch(runner, base_remote, base_ref, cwd=cwd)
        if fetched.returncode != 0:
            return 0
    value = _behind_count(
        runner,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    )
    return value if value is not None else 0


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
    out: list[dict[str, object]] = []
    for item in raw_list:
        if isinstance(item, dict):
            out.append(cast("dict[str, object]", item))  # noqa: PERF401
    return out


def _checks_json_is_array(checks_json: str) -> bool:
    if not checks_json or checks_json.strip() in ("", "null"):
        return False
    try:
        parsed = json.loads(checks_json)
    except json.JSONDecodeError:
        return False
    return isinstance(parsed, list)


def _classify_checks_json(checks_json: str) -> tuple[str, str | None]:
    try:
        parsed = json.loads(checks_json or "[]")
    except json.JSONDecodeError:
        return "pending", None
    rows = _parse_check_rows(parsed)
    if not rows:
        return "empty", None
    failed = [row for row in rows if row.get("bucket") == "fail"]
    pending = [row for row in rows if row.get("bucket") == "pending"]
    if failed:
        link = str(failed[0].get("link", ""))
        return "fail", _extract_run_id(link)
    if pending:
        return "pending", None
    return "pass", None


def _classify_checks_text(text: str) -> tuple[str, str | None]:
    if not text.strip():
        return "empty", None
    if re.search(r"\bfail", text, flags=re.IGNORECASE):
        failed_line = next(
            (line for line in text.splitlines() if re.search(r"\bfail", line, flags=re.IGNORECASE)),
            "",
        )
        link_match = re.search(r"https://\S+", failed_line)
        run_id = _extract_run_id(link_match.group(0)) if link_match else None
        return "fail", run_id
    if re.search(
        r"\b(pending|in_progress|queued)",
        text,
        flags=re.IGNORECASE,
    ):
        return "pending", None
    return "pass", None


def _read_pr_checks_text(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    cwd: str | None,
) -> str:
    result = gh.pr_checks_text_read(runner, pr, repo=repo, cwd=cwd)
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
) -> tuple[str, str | None]:
    """Classify PR checks with JSON-first and text fallback (ci-status.sh parity)."""
    checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd)
    checks_json = checks.stdout if checks.returncode == 0 else ""

    if _checks_json_is_array(checks_json):
        bucket_status, run_id = _classify_checks_json(checks_json)
        if bucket_status == "empty" and empty_checks_grace > 0:
            sleep_fn(float(empty_checks_grace))
            checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd)
            checks_json = checks.stdout if checks.returncode == 0 else ""
            if _checks_json_is_array(checks_json):
                bucket_status, run_id = _classify_checks_json(checks_json)
        if bucket_status == "empty":
            text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd)
            if text.strip():
                return _classify_checks_text(text)
            return ("NO_CHECKS", None) if empty_checks_grace > 0 else ("pending", None)
        return bucket_status, run_id

    text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd)
    if not text.strip() and empty_checks_grace > 0:
        sleep_fn(float(empty_checks_grace))
        text = _read_pr_checks_text(runner, pr=pr, repo=repo, cwd=cwd)
    if text.strip():
        return _classify_checks_text(text)
    if empty_checks_grace > 0:
        return "NO_CHECKS", None
    return "pending", None


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
) -> CiStatus:
    """Port of ci-status.sh."""
    conflicted = True
    try:
        pr_info = gh.pr_view(runner, pr, repo=repo, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        pr_info = None
    if pr_info is not None:
        if pr_info.state.upper() == "MERGED":
            return CiStatus(status="merged", behind_count=0, failed_run_id=None, conflicted=False)
        conflicted = _conflicted_from_merge_state(pr_info.merge_state_status)

    fetch = git.fetch(runner, base_remote, base_ref, cwd=cwd)
    if fetch.returncode != 0:
        return CiStatus(status="pending", behind_count=0, failed_run_id=None, conflicted=conflicted)

    status, failed_run_id = _resolve_checks_status(
        runner,
        pr=pr,
        repo=repo,
        empty_checks_grace=empty_checks_grace,
        sleep_fn=sleep_fn,
        cwd=cwd,
    )

    behind_raw = _behind_count(
        runner,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    )
    if behind_raw is None:
        return CiStatus(
            status=status,
            behind_count=0,
            failed_run_id=failed_run_id,
            conflicted=conflicted,
        )
    behind = behind_raw
    if behind > 0 and _squash_merge_race(
        runner,
        pr=pr,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    ):
        return CiStatus(status="merged", behind_count=0, failed_run_id=None, conflicted=False)
    return CiStatus(
        status=status,
        behind_count=behind,
        failed_run_id=failed_run_id,
        conflicted=conflicted,
    )


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
    timeout: float = config.CI_WAIT_TIMEOUT_SEC,
    sleep_fn: SleepFn = time.sleep,
    clock: ClockFn = time.monotonic,
    cwd: str | None = None,
) -> tuple[CiStatus, Decision]:
    """Port of ci-wait.sh poll loop."""
    max_polls = max(1, math.ceil(timeout / config.CI_WAIT_POLL_INTERVAL_SEC))
    checks = 0
    ci_failures = 0
    poll_interval = float(config.CI_WAIT_POLL_INTERVAL_SEC)
    started_at = clock()
    last_status = CiStatus(status="pending", behind_count=0, failed_run_id=None)

    while True:
        if checks >= max_polls:
            return (
                last_status,
                Decision(
                    action="bail",
                    bail_reason=f"Poll budget ({max_polls} polls / {int(timeout)}s) exhausted",
                ),
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
        )
        last_status = status

        if not status.status or status.status == "error":
            ci_failures += 1
            if ci_failures >= config.CI_MONITOR_STATUS_FAILURE_BAIL:
                return (
                    CiStatus(status="error", behind_count=0, failed_run_id=None),
                    Decision(
                        action="bail",
                        bail_reason="ci-status.sh returned no valid output 3 times consecutively",
                    ),
                )
            status = CiStatus(
                status="pending",
                behind_count=status.behind_count,
                failed_run_id=status.failed_run_id,
            )
        else:
            ci_failures = 0

        if status.status == "NO_CHECKS":
            return (
                status,
                Decision(
                    action="bail",
                    bail_reason=f"No CI checks observed after {empty_checks_grace}s grace",
                ),
            )

        decision = decide(
            status,
            iteration=iteration,
            rebase_count=rebase_count,
            fix_attempts=fix_attempts,
        )
        if decision.action != "wait":
            return status, decision

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
            checks -= 1


def _parse_job_name_shard(raw_name: str) -> tuple[str, str, bool]:
    raw_name = logging_util.sanitize_diagnostic_line(raw_name)
    if not raw_name:
        return "", "", True
    match = _MATRIX_SHARD_RE.match(raw_name)
    if match:
        return match.group(1), match.group(2), False
    match = _MATRIX_ANY_RE.match(raw_name)
    if match:
        return match.group(1), "", False
    if _JOB_NAME_RE.match(raw_name):
        return raw_name, "", False
    return raw_name, "", True


def classify_failed_jobs(jobs: tuple[FailedJob, ...]) -> ClassifiedJobs:
    """Port of ci-failed-jobs.sh classification."""
    parsed: list[JobClass] = []
    fixable: list[JobClass] = []
    unfixable: list[JobClass] = []
    for job in jobs:
        sanitized = logging_util.sanitize_diagnostic_line(job.name)
        if not sanitized:
            continue
        name, shard, malformed = _parse_job_name_shard(sanitized)
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
    """Port of gh-run-logs.sh."""
    pointer = (
        f"--- CI log (run {run_id}, repo {repo}) — last "
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


def rerun_failed(
    runner: Runner,
    *,
    run_id: str,
    repo: str,
    cwd: str | None = None,
) -> RerunResult:
    """Port of ci-rerun-failed.sh."""
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


def per_job_command(name: str, shard: str) -> tuple[str, ...] | None:
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
    if name == "smoke-dialectic":
        return ("make", "smoke-dialectic")
    if name == "agent-sync":
        return ("make", "agent-sync")
    if name == "python-lint":
        return ("make", "py-lint")
    if name == "python-tests":
        return ("make", "py-test")
    return None


def prepare_python_toolchain(runner: Runner, name: str, *, cwd: str | None = None) -> bool:
    """Port of _prepare_python_job_toolchain."""
    if name == "python-lint":
        req = _REPO_ROOT / "python" / "requirements-dev.txt"
        if req.is_file():
            _ = runner.run(
                ["python3", "-m", "pip", "install", "-q", "-r", str(req)],
                cwd=cwd,
            )
        for tool in ("ruff", "pylint", "pyright"):
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
    runner: Runner,
    name: str,
    shard: str,
    *,
    cwd: str | None = None,
) -> bool:
    argv = per_job_command(name, shard)
    if argv is None:
        return False
    result = runner.run(list(argv), cwd=cwd)
    return result.returncode == 0


def _job_token(name: str, shard: str) -> str:
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


def _capture_baseline(
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


def _is_submodule_gitlink(runner: Runner, path: str, *, cwd: str | None) -> bool:
    result = runner.run(["git", "ls-files", "--stage", "--", path], cwd=cwd)
    if result.returncode != 0:
        return False
    return any(line.startswith("160000 ") for line in result.stdout.splitlines())


def _rollback_to_baseline(
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
        if _path_unsafe_for_rollback(path) or _is_submodule_gitlink(runner, path, cwd=cwd):
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
        if _path_unsafe_for_rollback(path) or _is_submodule_gitlink(runner, path, cwd=cwd):
            continue
        _ = runner.run(["git", "restore", "--staged", "--", path], cwd=cwd)
        if path not in baseline_tracked_set and path not in baseline_untracked_set:
            _ = runner.run(["rm", "-f", "--", path], cwd=cwd)


def _delta_paths(
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


def _parse_launcher_exit(text: str) -> int:
    match = _LAUNCHER_EXIT_RE.search(text)
    if match:
        return int(match.group(1))
    return 0


def _available_tiers() -> tuple[str, ...]:
    tiers: list[str] = []
    for tier in config.FIXER_TIER_ORDER:
        if tier == "claude":
            script = _SCRIPTS_DIR / "launch-claude-ci.sh"
            if not script.is_file() or not os.access(script, os.X_OK):
                continue
        tiers.append(tier)
    return tuple(tiers) if tiers else config.FIXER_TIER_ORDER


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


def _make_default_launch_fn(
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

    def launch_fn(tier: str) -> TierAttempt:
        tier_out = str(Path(prefix) / f"ci-fix-{tier}.out")
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
        launcher_exit = _parse_launcher_exit(combined)
        failure = agents.classify_launch_failure(
            launcher_exit,
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
    classified: ClassifiedJobs | None = None,
    ctx: RunContext | None = None,
) -> tuple[bool, str | None, tuple[str, ...], bool, bool]:
    """Stage delta paths, commit, then push; force-push only after a rebase."""
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
                    _ = git.rebase(runner, "--abort", cwd=cwd)
                    return False, head, delta_paths, False, False
    if did_rebase or ci_fix_rebase_pending:
        if ci_fix_rebase_pending and not (classified and classified.fixable):
            _warn_stderr("ship-pr: pending CI-fix rebase lacks local verification targets; preserving pending retry")
            return False, head, delta_paths, did_rebase, True
        if (did_rebase or ci_fix_rebase_pending) and classified and classified.fixable:
            failed_verify = [
                _job_token(job.name, job.shard)
                for job in classified.fixable
                if not verify_job_locally(runner, job.name, job.shard, cwd=cwd)
            ]
            if failed_verify:
                return False, head, delta_paths, did_rebase, False
        if ctx is not None:
            with suppress(OSError, ShipError):
                skip = run_logs.flush_logs_pre(runner, ctx.with_(state_file=None), cwd=cwd)
                if skip.skipped and skip.reason == run_logs.REFRESH_SKIP_RECOVERY_FAILED:
                    _warn_stderr("ship-pr: run-log refresh skipped before force-push: manifest recovery failed")
                    return False, head, delta_paths, did_rebase, True
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
    start_attempt: int,
    cwd: str | None,
    launch_fn: LaunchFn | None = None,
    output_dir: str | None = None,
    base_remote: str = "origin",
    base_ref: str = "main",
    ci_fix_rebase_pending: bool = False,
    ctx: RunContext | None = None,
) -> FixResult:
    """Drive the CI vendor waterfall once."""
    if ci_fix_rebase_pending:
        pushed, post_head, delta_paths, did_rebase, pending = stage_and_push(
            runner,
            cwd=cwd,
            commit_label="pending-retry",
            delta_paths=(),
            base_remote=base_remote,
            base_ref=base_ref,
            ci_fix_rebase_pending=True,
            classified=classified,
            ctx=ctx,
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
    baseline_tracked, baseline_untracked, baseline_staged, baseline_head = _capture_baseline(
        runner,
        cwd=cwd,
    )
    failure_log_paths: list[str] = []
    base_launch = launch_fn or _make_default_launch_fn(
        runner,
        run_id=run_id,
        repo=repo,
        plan_file=plan_file,
        logs=logs,
        output_dir=output_dir,
        cwd=cwd,
        failure_log_paths=failure_log_paths,
    )

    def _rollback() -> None:
        _rollback_to_baseline(
            runner,
            baseline_tracked=baseline_tracked,
            baseline_untracked=baseline_untracked,
            baseline_staged=baseline_staged,
            cwd=cwd,
        )

    def _tier_launch(tier: str) -> TierAttempt:
        attempt = base_launch(tier)
        if attempt.launcher_exit != 0 or attempt.wrapper_rc != 0:
            _rollback()
        return attempt

    try:
        unfixable = [_job_token(job.name, job.shard) for job in classified.unfixable]
        if not classified.fixable and unfixable:
            return FixResult(status="local-unfixable", unfixable=tuple(unfixable))

        code_fix_attempted = False

        tiers = _available_tiers()
        if not tiers:
            return FixResult(status="waterfall-failed", detail="no launcher tiers available")
        first_tier = tiers[start_attempt % len(tiers)]
        waterfall = agents.run_waterfall(
            tiers,
            _tier_launch,
            first_tier=first_tier,
        )
        if waterfall.short_circuited:
            _rollback()
            return FixResult(
                status="first-fixer-non-health",
                detail="first-fixer-non-health",
            )
        if waterfall.winning_tier is None:
            _rollback()
            return FixResult(
                status="waterfall-failed",
                detail="all tiers failed",
            )

        if classified.fixable:
            code_fix_attempted = True
        for job in classified.fixable:
            argv = per_job_command(job.name, job.shard)
            if argv is None or not prepare_python_toolchain(runner, job.name, cwd=cwd):
                unfixable.append(_job_token(job.name, job.shard))
        if unfixable:
            _rollback()
            return FixResult(
                status="local-unfixable",
                unfixable=tuple(unfixable),
                code_fix_attempted_on_ready_log=code_fix_attempted,
            )

        current_head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
        if current_head != baseline_head:
            _rollback()
            return FixResult(
                status="head-changed",
                code_fix_attempted_on_ready_log=code_fix_attempted,
            )

        failed_verify = [
            _job_token(job.name, job.shard)
            for job in classified.fixable
            if not verify_job_locally(runner, job.name, job.shard, cwd=cwd)
        ]
        if failed_verify:
            _rollback()
            return FixResult(
                status="verify-failed",
                failed_verify=tuple(failed_verify),
                code_fix_attempted_on_ready_log=code_fix_attempted,
            )

        delta = _delta_paths(
            runner,
            baseline_tracked=baseline_tracked,
            baseline_untracked=baseline_untracked,
            cwd=cwd,
        )
        pushed, post_head, delta_paths, did_rebase, pending = stage_and_push(
            runner,
            cwd=cwd,
            commit_label=waterfall.winning_tier or "vendor",
            delta_paths=delta,
            base_remote=base_remote,
            base_ref=base_ref,
            ci_fix_rebase_pending=ci_fix_rebase_pending,
            classified=classified,
            ctx=ctx,
        )
        if not pushed:
            return FixResult(
                status="waterfall-failed",
                detail="push failed",
                code_fix_attempted_on_ready_log=code_fix_attempted,
                did_rebase=did_rebase,
                ci_fix_rebase_pending=pending,
            )
        if post_head == baseline_head:
            return FixResult(
                status="first-fixer-non-health",
                winning_tier=waterfall.winning_tier,
                detail="first-fixer-non-health",
            )
        return FixResult(
            status="pushed",
            winning_tier=waterfall.winning_tier,
            delta_paths=delta_paths,
            code_fix_attempted_on_ready_log=code_fix_attempted,
            did_rebase=did_rebase,
            ci_fix_rebase_pending=False,
        )
    finally:
        for path in failure_log_paths:
            Path(path).unlink(missing_ok=True)


def _fix_exhausted_detail(
    classified: ClassifiedJobs | None,
    logs: LogCollectResult | None,
) -> str:
    """Compose the diagnostic detail surfaced when the CI-fix loop exhausts.

    Carries the stable ``ci-fix-exhausted`` reason token, the failing job
    name(s), and the already-redacted CI log tail so Step 18a stall recovery
    can route the stall to an inline fix (``RESUME_HINT=step8-shippr``) instead
    of terminal ``unrecoverable`` handling. The job names come from the closed
    CI-job enum and the log tail is redacted upstream in ``collect_failed_logs``.
    """
    jobs = ""
    if classified is not None:
        jobs = ", ".join(_job_token(job.name, job.shard) for job in classified.jobs)
    header = f"ci-fix-exhausted: {jobs}" if jobs else "ci-fix-exhausted"
    tail = logs.text if logs is not None and logs.state == "ready" else ""
    if tail.strip():
        return f"{header}\n{redact.redact(tail).rstrip()}\n"
    return header


def evaluate_failure(
    runner: Runner,
    *,
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
) -> FixResult:
    """Port of run_evaluate_failure outer loop."""
    if not run_id or not str(run_id).strip():
        return FixResult(status="waterfall-failed", detail="missing run_id")

    upfront_logs = collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
    upfront_ready_stash: LogCollectResult | None = None
    blind_rerun_attempted = False
    if (
        transient_retries < config.CI_MONITOR_TRANSIENT_RERUN_MAX
        and upfront_logs.state == "ready"
        and retry.is_transient_net_signature(upfront_logs.text)
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

    last_verify: tuple[str, ...] = ()
    last_classified: ClassifiedJobs | None = None
    last_logs: LogCollectResult | None = None
    code_fix_attempted_on_ready_log = False
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
                start_attempt=0,
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
        if attempt == 1 and upfront_ready_stash is not None:
            logs = upfront_ready_stash
        else:
            logs = collect_failed_logs(runner, run_id=run_id, repo=repo, cwd=cwd)
        if logs.state != "ready":
            if attempt < config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS:
                sleep_fn(_outer_backoff_seconds(attempt))
            continue
        jobs_raw, jobs_state = read_failed_jobs(
            runner,
            run_id=run_id,
            repo=repo,
            cwd=cwd,
        )
        if jobs_state != "ready":
            if attempt < config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS:
                sleep_fn(_outer_backoff_seconds(attempt))
            continue

        classified = classify_failed_jobs(jobs_raw)
        last_classified = classified
        last_logs = logs
        fix = run_ci_fix(
            runner,
            run_id=run_id,
            repo=repo,
            classified=classified,
            logs=logs,
            plan_file=plan_file,
            start_attempt=attempt - 1,
            cwd=cwd,
            launch_fn=launch_fn,
            base_remote=base_remote,
            base_ref=base_ref,
            ci_fix_rebase_pending=ci_fix_rebase_pending,
            ctx=ctx,
        )
        if fix.code_fix_attempted_on_ready_log:
            code_fix_attempted_on_ready_log = True
        if fix.status == "local-unfixable":
            if code_fix_attempted_on_ready_log:
                return FixResult(
                    status="fix-exhausted",
                    detail=_fix_exhausted_detail(classified, logs),
                )
            return fix
        if fix.status == "head-changed":
            if code_fix_attempted_on_ready_log:
                return FixResult(
                    status="fix-exhausted",
                    detail=_fix_exhausted_detail(classified, logs),
                )
            return fix
        if fix.status == "pushed":
            return fix
        if fix.status == "first-fixer-non-health":
            return fix
        if fix.status == "verify-failed":
            last_verify = fix.failed_verify
            if attempt < config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS:
                sleep_fn(_outer_backoff_seconds(attempt))
            continue
        if fix.status == "waterfall-failed":
            if attempt < config.CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS:
                sleep_fn(_outer_backoff_seconds(attempt))
            continue
        return fix

    if code_fix_attempted_on_ready_log:
        return FixResult(
            status="fix-exhausted",
            detail=_fix_exhausted_detail(last_classified, last_logs),
        )
    if last_verify:
        jobs = ", ".join(last_verify)
        return FixResult(
            status="waterfall-failed",
            failed_verify=last_verify,
            detail=f"verify-failed after outer cap: {jobs}",
        )
    return FixResult(status="fix-exhausted", detail=_fix_exhausted_detail(last_classified, last_logs))


def monitor(
    runner: Runner,
    *,
    pr: int,
    repo: str,
    base_remote: str = "origin",
    base_ref: str = "main",
    empty_checks_grace: int = 0,
    iteration: int = 0,
    rebase_count: int = 0,
    fix_attempts: int = 0,
    transient_retries: int = 0,
    plan_file: str | None = None,
    ci_fix_rebase_pending: bool = False,
    ctx: RunContext | None = None,
    cwd: str | None = None,
    launch_fn: LaunchFn | None = None,
    sleep_fn: SleepFn = time.sleep,
    clock: ClockFn = time.monotonic,
) -> MonitorResult:
    """Driver entrypoint for CI monitor loop."""
    status, decision = poll_ci(
        runner,
        pr=pr,
        repo=repo,
        base_remote=base_remote,
        base_ref=base_ref,
        empty_checks_grace=empty_checks_grace,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
        sleep_fn=sleep_fn,
        clock=clock,
        cwd=cwd,
    )

    def _base_result(
        *,
        did_fixing: bool,
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
            did_fixing=did_fixing,
            goto_rebase=goto,
            iterations=iteration,
            result=step,
            rerun_already_running=rerun_already_running,
            transient_rerun_attempted=transient_rerun_attempted,
            ci_fix_rebase_pending=pending,
        )

    if decision.action in ("merge", "already_merged"):
        return _base_result(
            did_fixing=False,
            goto=False,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action == "rebase":
        return _base_result(
            did_fixing=False,
            goto=True,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action in ("evaluate_failure", "rebase_then_evaluate"):
        if decision.action == "rebase_then_evaluate":
            return _base_result(
                did_fixing=False,
                goto=True,
                step=StepResult(outcome=Outcome.OK),
            )
        if not status.failed_run_id:
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(
                    outcome=Outcome.STALLED,
                    detail="missing failed_run_id",
                ),
            )
        fix = evaluate_failure(
            runner,
            run_id=status.failed_run_id,
            repo=repo,
            plan_file=plan_file,
            transient_retries=transient_retries,
            _fix_attempts=fix_attempts,
            cwd=cwd,
            launch_fn=launch_fn,
            sleep_fn=sleep_fn,
            base_remote=base_remote,
            base_ref=base_ref,
            ci_fix_rebase_pending=ci_fix_rebase_pending,
            ctx=ctx,
        )
        if fix.status == "no-changes":
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(outcome=Outcome.OK),
                rerun_already_running=fix.rerun_already_running,
                transient_rerun_attempted=True,
                pending=fix.ci_fix_rebase_pending,
            )
        if fix.status == "pushed":
            return _base_result(
                did_fixing=True,
                goto=status.behind_count > 0,
                step=StepResult(outcome=Outcome.OK),
                pending=fix.ci_fix_rebase_pending,
            )
        if fix.status == "head-changed":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(outcome=Outcome.STALLED, detail="head-changed"),
                pending=fix.ci_fix_rebase_pending,
            )
        if fix.status == "first-fixer-non-health":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail="first-fixer-non-health",
                ),
                pending=fix.ci_fix_rebase_pending,
            )
        if fix.status == "fix-exhausted":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail=fix.detail or "ci-fix-exhausted",
                ),
                pending=fix.ci_fix_rebase_pending,
            )
        detail = fix.detail or fix.status
        if fix.failed_verify:
            detail = f"{fix.status}: {', '.join(fix.failed_verify)}"
        if fix.unfixable:
            detail = f"{fix.status}: {', '.join(fix.unfixable)}"
        if fix.status == "local-unfixable":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(outcome=Outcome.NEEDS_USER_INPUT, detail=detail),
                pending=fix.ci_fix_rebase_pending,
            )
        if fix.status == "waterfall-failed" and fix.ci_fix_rebase_pending:
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(outcome=Outcome.OK),
                pending=True,
            )
        return _base_result(
            did_fixing=True,
            goto=False,
            step=StepResult(outcome=Outcome.STALLED, detail=detail),
            pending=fix.ci_fix_rebase_pending,
        )

    if decision.action == "bail":
        if decision.bail_reason and retry.is_transient_net_signature(decision.bail_reason):
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(
                    outcome=Outcome.TRANSIENT,
                    detail=decision.bail_reason,
                ),
            )
        if decision.bail_reason == "fix-attempts-exhausted":
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail=decision.bail_reason,
                ),
            )
        return _base_result(
            did_fixing=False,
            goto=False,
            step=StepResult(
                outcome=Outcome.STALLED,
                detail=decision.bail_reason or "bail",
            ),
        )

    return _base_result(
        did_fixing=False,
        goto=False,
        step=StepResult(outcome=Outcome.STALLED, detail=decision.action),
    )
