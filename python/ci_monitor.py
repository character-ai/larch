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

import agents
import config
import gh
import git
import redact
import retry
from agents import TierAttempt
from gh import FailedJob
from outcomes import Outcome, StepResult
from proc import CommandResult, Runner

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
    _ = sys.stderr.write(message.rstrip("\n") + "\n")
    _ = sys.stderr.flush()


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


def _squash_merge_race(
    runner: Runner,
    *,
    pr: int,
    base_remote: str,
    base_ref: str,
    cwd: str | None,
) -> bool:
    base = f"{base_remote}/{base_ref}"
    subjects = git.log_subjects(runner, f"HEAD..{base}", cwd=cwd)
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
    try:
        pr_info = gh.pr_view(runner, pr, repo=repo, cwd=cwd)
    except Exception:  # pylint: disable=broad-except
        return CiStatus(status="error", behind_count=0, failed_run_id=None, conflicted=False)
    if pr_info.state.upper() == "MERGED":
        return CiStatus(status="merged", behind_count=0, failed_run_id=None, conflicted=False)

    conflicted = _conflicted_from_merge_state(pr_info.merge_state_status)

    fetch = git.fetch(runner, base_remote, base_ref, cwd=cwd)
    if fetch.returncode != 0:
        return CiStatus(status="pending", behind_count=0, failed_run_id=None, conflicted=conflicted)

    checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd)
    checks_json = checks.stdout if checks.returncode == 0 else ""
    status = "pending"
    failed_run_id: str | None = None

    if checks_json and checks_json.strip() not in ("", "null"):
        bucket_status, run_id = _classify_checks_json(checks_json)
        if bucket_status == "empty":
            if empty_checks_grace > 0:
                sleep_fn(float(empty_checks_grace))
                checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd)
                checks_json = checks.stdout if checks.returncode == 0 else ""
                bucket_status, run_id = _classify_checks_json(checks_json)
            if bucket_status == "empty":
                status = "NO_CHECKS" if empty_checks_grace > 0 else "pending"
            else:
                status = bucket_status
                failed_run_id = run_id
        else:
            status = bucket_status
            failed_run_id = run_id
    elif empty_checks_grace > 0:
        sleep_fn(float(empty_checks_grace))
        checks = _gh_pr_checks(runner, pr=pr, repo=repo, cwd=cwd)
        checks_json = checks.stdout if checks.returncode == 0 else ""
        if checks_json and checks_json.strip() not in ("", "null"):
            bucket_status, run_id = _classify_checks_json(checks_json)
            if bucket_status == "empty":
                status = "NO_CHECKS"
            else:
                status = bucket_status
                failed_run_id = run_id
        else:
            status = "NO_CHECKS"
    else:
        status = "pending"

    behind_raw = _behind_count(
        runner,
        base_remote=base_remote,
        base_ref=base_ref,
        cwd=cwd,
    )
    if behind_raw is None:
        return CiStatus(
            status="pending",
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

    while True:
        if checks >= max_polls:
            return (
                CiStatus(status="pending", behind_count=0, failed_run_id=None),
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
        iter_start = clock()
        sleep_fn(poll_interval)
        iter_delta = clock() - iter_start
        if iter_delta > _CI_SUSPEND_THRESHOLD_SEC:
            checks -= 1


def _parse_job_name_shard(raw_name: str) -> tuple[str, str, bool]:
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
        name, shard, malformed = _parse_job_name_shard(job.name)
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
    if result.returncode != 0 and _IN_PROGRESS_MSG in combined:
        return LogCollectResult(text="", state="in_progress")
    if result.returncode != 0:
        return LogCollectResult(text="", state="error")
    lines = combined.splitlines()
    tail = lines[-config.CI_MONITOR_LOG_TAIL_LINES :]
    body = redact.redact("\n".join(tail))
    if body and not body.endswith("\n"):
        body += "\n"
    text = f"{pointer}\n{body}" if body.strip() else pointer + "\n"
    return LogCollectResult(text=redact.redact(text), state="ready")


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
    _ = Path(path).write_text(text, encoding="utf-8")
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
) -> tuple[bool, str | None, tuple[str, ...]]:
    """Stage delta paths, commit, and normal push."""
    if not delta_paths:
        return False, None, ()
    for path in delta_paths:
        _ = runner.run(["git", "add", "--", path], cwd=cwd)
    commit_msg = f"Apply CI fixes ({commit_label})"
    commit_script = str(_SCRIPTS_DIR / "git-commit.sh")
    commit = runner.run(
        [commit_script, "--no-trailer", "-m", commit_msg],
        cwd=cwd,
    )
    if commit.returncode != 0:
        return False, None, delta_paths
    head = git.try_rev_parse(runner, "HEAD", cwd=cwd)
    branch = git.current_branch(runner, cwd=cwd) if head else "HEAD"
    push = git.push(runner, "origin", branch, cwd=cwd)
    pushed = push.returncode == 0
    sha = git.try_rev_parse(runner, "HEAD", cwd=cwd) if pushed else head
    return pushed, sha, delta_paths


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
) -> FixResult:
    """Drive the CI vendor waterfall once."""
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
        pushed, post_head, delta_paths = stage_and_push(
            runner,
            cwd=cwd,
            commit_label=waterfall.winning_tier or "vendor",
            delta_paths=delta,
        )
        if not pushed:
            return FixResult(
                status="waterfall-failed",
                detail="push failed",
                code_fix_attempted_on_ready_log=code_fix_attempted,
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
        return f"{header}\n{tail.rstrip()}\n"
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
    return FixResult(status="waterfall-failed", detail="outer fix attempts exhausted")


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
        )

    if decision.action in ("merge", "already_merged"):
        return _base_result(
            did_fixing=False,
            goto=False,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action in ("rebase", "rebase_then_evaluate"):
        return _base_result(
            did_fixing=False,
            goto=True,
            step=StepResult(outcome=Outcome.OK),
        )

    if decision.action == "evaluate_failure":
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
        )
        if fix.status == "no-changes":
            return _base_result(
                did_fixing=False,
                goto=False,
                step=StepResult(outcome=Outcome.OK),
                rerun_already_running=fix.rerun_already_running,
            )
        if fix.status == "pushed":
            return _base_result(
                did_fixing=True,
                goto=True,
                step=StepResult(outcome=Outcome.OK),
            )
        if fix.status == "head-changed":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(outcome=Outcome.STALLED, detail="head-changed"),
            )
        if fix.status == "first-fixer-non-health":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail="first-fixer-non-health",
                ),
            )
        if fix.status == "fix-exhausted":
            return _base_result(
                did_fixing=True,
                goto=False,
                step=StepResult(
                    outcome=Outcome.NEEDS_USER_INPUT,
                    detail=fix.detail or "ci-fix-exhausted",
                ),
            )
        detail = fix.detail or fix.status
        if fix.failed_verify:
            detail = f"{fix.status}: {', '.join(fix.failed_verify)}"
        if fix.unfixable:
            detail = f"{fix.status}: {', '.join(fix.unfixable)}"
        return _base_result(
            did_fixing=True,
            goto=False,
            step=StepResult(outcome=Outcome.STALLED, detail=detail),
        )

    if decision.action == "bail":
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
