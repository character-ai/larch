"""Unit tests for ci_monitor.py (stub Runner; no bash)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from pathlib import Path

import pytest

import ci_monitor
import config
import redact
from agents import LaunchFailure, TierAttempt
from gh import FailedJob
from outcomes import Outcome
from proc import CommandResult

REPO_ROOT = Path(__file__).resolve().parents[1]
SCRIPTS_DIR = REPO_ROOT / "scripts"


def _new_response_map() -> dict[tuple[str, ...], CommandResult]:
    return {}


def _new_prefix_responses() -> list[tuple[tuple[str, ...], CommandResult]]:
    return []


def _new_sequential_map() -> dict[tuple[str, ...], list[CommandResult]]:
    return {}


def _new_call_log() -> list[tuple[str, ...]]:
    return []


@dataclass
class RecordingRunner:
    """Stub Runner keyed by argv prefix or exact match."""

    responses: dict[tuple[str, ...], CommandResult] = field(default_factory=_new_response_map)
    prefix_responses: list[tuple[tuple[str, ...], CommandResult]] = field(
        default_factory=_new_prefix_responses,
    )
    sequential: dict[tuple[str, ...], list[CommandResult]] = field(
        default_factory=_new_sequential_map,
    )
    calls: list[tuple[str, ...]] = field(default_factory=_new_call_log)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        self.calls.append(key)
        queued = self.sequential.get(key)
        if queued:
            return queued.pop(0)
        if key in self.responses:
            return self.responses[key]
        for prefix, result in self.prefix_responses:
            if key[: len(prefix)] == prefix:
                return result
        msg = f"unexpected argv: {argv}"
        raise AssertionError(msg)


def _cr(argv: Sequence[str], rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def _status(
    *,
    status: str = "pass",
    behind: int = 0,
    merged: bool = False,
) -> dict[tuple[str, ...], CommandResult]:
    pr_json = json.dumps(
        {
            "number": 1,
            "url": "https://github.com/o/r/pull/1",
            "state": "MERGED" if merged else "OPEN",
            "headRefName": "feature",
        },
    )
    if status == "fail":
        checks = json.dumps(
            [
                {
                    "name": "lint",
                    "state": "FAIL",
                    "bucket": "fail",
                    "link": "https://github.com/o/r/actions/runs/999/job/1",
                },
            ],
        )
    elif status == "pending":
        checks = json.dumps(
            [{"name": "lint", "state": "IN_PROGRESS", "bucket": "pending", "link": ""}],
        )
    elif status == "empty":
        checks = "[]"
    else:
        checks = json.dumps(
            [{"name": "lint", "state": "SUCCESS", "bucket": "pass", "link": ""}],
        )
    return {
        ("gh", "pr", "view", "1", "--repo", "o/r", "--json", "number,url,state,headRefName"): _cr(
            ("gh", "pr", "view"),
            stdout=pr_json,
        ),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
        ): _cr(("gh", "pr", "checks"), stdout=checks),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(
            ("git", "rev-list", "--count"),
            stdout=f"{behind}\n",
        ),
        ("git", "log", "--format=%s", "HEAD..origin/main"): _cr(
            ("git", "log"),
            stdout="",
        ),
    }


@pytest.mark.parametrize(
    ("status", "behind", "iteration", "rebase_count", "fix_attempts", "expected"),
    [
        ("merged", 0, 0, 0, 0, "already_merged"),
        ("pass", 0, 0, 0, 0, "merge"),
        ("pass", 1, 0, 0, 0, "rebase"),
        ("pending", 1, 0, 0, 0, "rebase"),
        ("pending", 0, 0, 0, 0, "wait"),
        ("fail", 1, 0, 0, 0, "rebase_then_evaluate"),
        ("fail", 0, 0, 0, 0, "evaluate_failure"),
        ("error", 0, 0, 0, 0, "bail"),
        ("pass", 0, 50, 0, 0, "merge"),
        ("pending", 0, 50, 0, 0, "bail"),
        ("fail", 0, 0, 0, 10, "bail"),
        ("fail", 0, 0, 20, 0, "bail"),
    ],
)
def test_decide_parity_table(
    status: str,
    behind: int,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    expected: str,
) -> None:
    ci_status = ci_monitor.CiStatus(status=status, behind_count=behind, failed_run_id=None)
    decision = ci_monitor.decide(
        ci_status,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
    )
    assert decision.action == expected


def test_gather_status_merged_short_circuit() -> None:
    runner = RecordingRunner(_status(merged=True))
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "merged"
    assert status.behind_count == 0


def test_gather_status_fail_extracts_run_id() -> None:
    runner = RecordingRunner(_status(status="fail"))
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "fail"
    assert status.failed_run_id == "999"


def test_gather_status_fetch_fail_pending() -> None:
    responses = _status(status="pass")
    responses[("git", "fetch", "origin", "main", "--quiet")] = _cr(
        ("git", "fetch"),
        rc=1,
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "pending"
    assert status.behind_count == 0


def test_gather_status_empty_checks_grace() -> None:
    responses = _status(status="empty")
    runner = RecordingRunner(responses)
    sleeps: list[float] = []

    def sleep_fn(sec: float) -> None:
        sleeps.append(sec)

    status = ci_monitor.gather_status(
        runner,
        pr=1,
        repo="o/r",
        empty_checks_grace=5,
        sleep_fn=sleep_fn,
    )
    assert status.status == "NO_CHECKS"
    assert sleeps == [5.0]


def test_gather_status_squash_merge_race() -> None:
    responses = _status(status="pass", behind=2)
    responses[("git", "log", "--format=%s", "HEAD..origin/main")] = _cr(
        ("git", "log"),
        stdout="Squash feature (#1)\n",
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "merged"
    assert status.behind_count == 0


def test_poll_ci_returns_on_first_non_wait() -> None:
    runner = RecordingRunner(_status(status="pass"))
    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        sleep_fn=lambda _s: None,
    )
    assert status.status == "pass"
    assert decision.action == "merge"


def test_poll_ci_budget_exhaustion_bails() -> None:
    runner = RecordingRunner(_status(status="pending", behind=0))
    _, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=10.0,
        sleep_fn=lambda _s: None,
    )
    assert decision.action == "bail"
    assert "Poll budget" in (decision.bail_reason or "")


def test_poll_ci_three_consecutive_errors_bail() -> None:
    responses = _status(status="pass")
    responses[("gh", "pr", "view", "1", "--repo", "o/r", "--json", "number,url,state,headRefName")] = _cr(
        ("gh", "pr", "view"),
        rc=1,
    )
    runner = RecordingRunner(responses)
    _, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=1000.0,
        sleep_fn=lambda _s: None,
    )
    assert decision.action == "bail"
    assert "3 times consecutively" in (decision.bail_reason or "")


def test_poll_ci_suspend_not_charged() -> None:
    runner = RecordingRunner(_status(status="pending", behind=0))
    clock_values = [0.0, 70.0, 70.0, 140.0, 210.0, 280.0]

    def clock() -> float:
        if clock_values:
            return clock_values.pop(0)
        return 9999.0

    _, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=30.0,
        sleep_fn=lambda _s: None,
        clock=clock,
    )
    assert decision.action == "bail"


def test_classify_failed_jobs_matrix_and_fixable() -> None:
    jobs = (
        FailedJob(name="lint (1)", conclusion="failure"),
        FailedJob(name="gitleaks", conclusion="failure"),
        FailedJob(name="bad name!", conclusion="failure"),
    )
    classified = ci_monitor.classify_failed_jobs(jobs)
    assert classified.count == 3
    assert classified.fixable[0].name == "lint"
    assert classified.fixable[0].shard == "1"
    assert classified.unfixable[0].name == "gitleaks"


def test_collect_failed_logs_redacts_secret() -> None:
    secret = "ghp_" + "A" * 40
    log_body = f"failed step\n{secret}\n"
    runner = RecordingRunner(
        {
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                stdout=log_body,
            ),
        },
    )
    result = ci_monitor.collect_failed_logs(runner, run_id="42", repo="o/r")
    assert result.state == "ready"
    assert secret not in result.text
    assert config.REDACTED_TOKEN in result.text
    assert "last 100 lines" in result.text


def test_collect_failed_logs_in_progress() -> None:
    runner = RecordingRunner(
        {
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                rc=3,
                stderr="is still in progress; logs will be available",
            ),
        },
    )
    result = ci_monitor.collect_failed_logs(runner, run_id="42", repo="o/r")
    assert result.state == "in_progress"
    assert result.text == ""


def test_read_failed_jobs_in_progress() -> None:
    runner = RecordingRunner(
        {
            (
                "gh",
                "run",
                "view",
                "42",
                "--repo",
                "o/r",
                "--json",
                "jobs",
            ): _cr(
                ("gh", "run", "view"),
                rc=1,
                stderr="is still in progress; logs will be available",
            ),
        },
    )
    jobs, state = ci_monitor.read_failed_jobs(runner, run_id="42", repo="o/r")
    assert not jobs
    assert state == "in_progress"


def test_read_failed_jobs_error_empty() -> None:
    runner = RecordingRunner(
        {
            (
                "gh",
                "run",
                "view",
                "42",
                "--repo",
                "o/r",
                "--json",
                "jobs",
            ): _cr(("gh", "run", "view"), rc=1, stderr="network down"),
        },
    )
    jobs, state = ci_monitor.read_failed_jobs(runner, run_id="42", repo="o/r")
    assert not jobs
    assert state == "error"


def test_rerun_failed_submitted_and_already_running() -> None:
    runner = RecordingRunner(
        {
            ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed"): _cr(
                ("gh", "run", "rerun"),
                0,
            ),
        },
    )
    ok = ci_monitor.rerun_failed(runner, run_id="42", repo="o/r")
    assert ok.submitted is True
    assert ok.already_running is False

    runner2 = RecordingRunner(
        {
            ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed"): _cr(
                ("gh", "run", "rerun"),
                1,
                stderr="Workflow already running",
            ),
        },
    )
    running = ci_monitor.rerun_failed(runner2, run_id="42", repo="o/r")
    assert running.submitted is True
    assert running.already_running is True


@pytest.mark.parametrize(
    ("name", "shard", "expected"),
    [
        ("lint", "", ("env", "SKIP=agnix,lint-mermaid-fences,shellcheck", "make", "lint-only")),
        ("python-lint", "", ("make", "py-lint")),
        ("test-harnesses", "2", ("make", "test-harnesses-2")),
        ("unknown", "", None),
    ],
)
def test_per_job_command_table(
    name: str,
    shard: str,
    expected: tuple[str, ...] | None,
) -> None:
    assert ci_monitor.per_job_command(name, shard) == expected


def test_verify_job_locally_rc() -> None:
    runner = RecordingRunner(
        {
            ("make", "py-lint"): _cr(("make", "py-lint"), 0),
        },
    )
    assert ci_monitor.verify_job_locally(runner, "python-lint", "", cwd="/tmp") is True


def _python_toolchain_stubs() -> dict[tuple[str, ...], CommandResult]:
    req_dev = str(REPO_ROOT / "python" / "requirements-dev.txt")
    return {
        ("command", "-v", "ruff"): _cr(("command", "-v", "ruff"), 0),
        ("command", "-v", "pylint"): _cr(("command", "-v", "pylint"), 0),
        ("command", "-v", "pyright"): _cr(("command", "-v", "pyright"), 0),
        ("python3", "-m", "pip", "install", "-q", "-r", req_dev): _cr(
            ("python3", "-m", "pip", "install"),
            0,
        ),
    }


def _baseline_responses(head: str = "abc123") -> dict[tuple[str, ...], CommandResult]:
    out: dict[tuple[str, ...], CommandResult] = {
        ("git", "diff", "--name-only"): _cr(("git", "diff"), stdout=""),
        ("git", "ls-files", "--others", "--exclude-standard"): _cr(("git", "ls-files"), stdout=""),
        ("git", "diff", "--name-only", "--cached"): _cr(("git", "diff"), stdout=""),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout=f"{head}\n"),
    }
    out.update(_python_toolchain_stubs())
    return out


def test_run_ci_fix_pushed_after_winning_tier(tmp_path: Any) -> None:
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(
            tier=tier,
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    baseline_head = "deadbeef" * 5
    new_head = "cafebabe" * 5
    responses = _baseline_responses(baseline_head)
    del responses[("git", "rev-parse", "HEAD")]
    responses[("git", "diff", "--name-only")] = _cr(
        ("git", "diff"),
        stdout="fixed.py\n",
    )
    responses[("git", "add", "--", "fixed.py")] = _cr(("git", "add"), 0)
    commit_script = str(SCRIPTS_DIR / "git-commit.sh")
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (cursor)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), 0)
    responses[("make", "py-lint")] = _cr(("make", "py-lint"), 0)

    runner = RecordingRunner(responses)
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{new_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{new_head}\n"),
    ]

    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    logs = ci_monitor.LogCollectResult(text="log line\n", state="ready")
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=logs,
        plan_file=None,
        start_attempt=0,
        cwd=str(tmp_path),
        launch_fn=launch_fn,
    )
    assert fix.status == "pushed"
    assert launch_calls == ["cursor"]


def test_run_ci_fix_first_fixer_non_health_after_stage(tmp_path: Any) -> None:
    head = "deadbeef" * 5

    def launch_fn(_tier: str) -> TierAttempt:
        return TierAttempt(
            tier="cursor",
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    responses = _baseline_responses(head)
    responses[("make", "py-lint")] = _cr(("make", "py-lint"), 0)
    commit_script = str(SCRIPTS_DIR / "git-commit.sh")
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (cursor)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), 0)

    runner = RecordingRunner(responses)
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    logs = ci_monitor.LogCollectResult(text="", state="ready")
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=logs,
        plan_file=None,
        start_attempt=0,
        cwd=str(tmp_path),
        launch_fn=launch_fn,
    )
    assert fix.status == "first-fixer-non-health"


def test_run_ci_fix_verify_failed_no_push() -> None:
    def launch_fn(_tier: str) -> TierAttempt:
        return TierAttempt(
            tier="cursor",
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    responses = _baseline_responses()
    responses[("make", "py-lint")] = _cr(("make", "py-lint"), 1)
    runner = RecordingRunner(responses)
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=ci_monitor.LogCollectResult(text="x", state="ready"),
        plan_file=None,
        start_attempt=0,
        cwd=None,
        launch_fn=launch_fn,
    )
    assert fix.status == "verify-failed"
    assert fix.failed_verify == ("python-lint",)
    assert not any(call[0] == "git" and call[1] == "push" for call in runner.calls)


def test_run_ci_fix_local_unfixable() -> None:
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="gitleaks", conclusion="failure"),),
    )
    runner = RecordingRunner(_baseline_responses())
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        plan_file=None,
        start_attempt=0,
        cwd=None,
        launch_fn=lambda _t: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
    )
    assert fix.status == "local-unfixable"
    assert "gitleaks" in fix.unfixable


def test_evaluate_failure_transient_rerun_only() -> None:
    runner = RecordingRunner(
        {
            ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed"): _cr(
                ("gh", "run", "rerun"),
                0,
            ),
        },
    )
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=0,
        _fix_attempts=0,
        cwd=None,
    )
    assert fix.status == "no-changes"
    assert len(runner.calls) == 1


def test_evaluate_failure_in_progress_defers_launch() -> None:
    launch_count = 0

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_count
        launch_count += 1
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(
        {
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                rc=3,
                stderr="is still in progress; logs will be available",
            ),
            (
                "gh",
                "run",
                "view",
                "42",
                "--repo",
                "o/r",
                "--json",
                "jobs",
            ): _cr(
                ("gh", "run", "view"),
                rc=1,
                stderr="is still in progress; logs will be available",
            ),
        },
    )
    sleeps: list[float] = []
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=sleeps.append,
    )
    assert launch_count == 0
    assert sleeps
    assert fix.status == "waterfall-failed"


def test_monitor_merge_ok_no_goto() -> None:
    runner = RecordingRunner(_status(status="pass"))
    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        sleep_fn=lambda _s: None,
    )
    assert result.result.outcome == Outcome.OK
    assert result.goto_rebase is False
    assert result.did_fixing is False


def test_monitor_rebase_then_evaluate_no_fix() -> None:
    runner = RecordingRunner(_status(status="fail", behind=1))
    launch_called = False

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_called
        launch_called = True
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        sleep_fn=lambda _s: None,
        launch_fn=launch_fn,
    )
    assert result.action == "rebase_then_evaluate"
    assert result.goto_rebase is True
    assert result.did_fixing is False
    assert launch_called is False


def test_monitor_fix_attempts_exhausted_needs_user_input() -> None:
    runner = RecordingRunner(_status(status="pending"))
    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        fix_attempts=10,
        sleep_fn=lambda _s: None,
    )
    assert result.result.outcome == Outcome.NEEDS_USER_INPUT
    assert result.result.detail == "fix-attempts-exhausted"


def test_redact_in_collect_failed_logs_unit() -> None:
    sample = "token ghp_" + "x" * 40
    redacted = redact.redact(sample)
    assert config.REDACTED_TOKEN in redacted
