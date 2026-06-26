"""Unit tests for design_log_ship.py."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

import pytest

from larch.core import config
import design_log_ship
from larch.core.proc import CommandResult


def _cr(argv: Sequence[str], rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def _pr(state: str = "OPEN") -> str:
    return json.dumps(
        {
            "number": 1,
            "url": "https://github.com/o/r/pull/1",
            "state": state,
            "headRefName": "feature",
            "mergedAt": None,
            "mergeStateStatus": "CLEAN",
        },
    )


def _checks(status: str = "pass", run_id: str = "999") -> str:
    if status == "pass":
        rows: list[dict[str, str]] = [{"name": "ci", "state": "SUCCESS", "bucket": "pass", "link": ""}]
    elif status == "pending":
        rows = [{"name": "ci", "state": "IN_PROGRESS", "bucket": "pending", "link": ""}]
    elif status == "empty":
        rows = []
    elif status == "unknown":
        rows = [{"name": "ci", "state": "CANCELLED", "bucket": "cancelled", "link": ""}]
    else:
        rows = [
            {
                "name": "ci",
                "state": "FAILURE",
                "bucket": "fail",
                "link": f"https://github.com/o/r/actions/runs/{run_id}/job/1",
            },
        ]
    return json.dumps(rows)


PR_VIEW = (
    "gh",
    "pr",
    "view",
    "1",
    "--repo",
    "o/r",
    "--json",
    "number,url,state,headRefName,mergedAt,mergeStateStatus",
)
CHECKS = ("gh", "pr", "checks", "1", "--repo", "o/r", "--json", "name,state,bucket,link", "--required")
MERGE = ("gh", "pr", "merge", "1", "--repo", "o/r", "--squash", "--admin", "--delete-branch")
RUN_VIEW = ("gh", "run", "view", "999", "--repo", "o/r", "--log-failed")
RERUN = ("gh", "run", "rerun", "999", "--repo", "o/r", "--failed")


def _empty_sequential() -> dict[tuple[str, ...], list[CommandResult]]:
    return {}


def _empty_responses() -> dict[tuple[str, ...], CommandResult]:
    return {}


def _empty_calls() -> list[tuple[tuple[str, ...], str | None]]:
    return []


@dataclass
class RecordingRunner:
    sequential: dict[tuple[str, ...], list[CommandResult]] = field(default_factory=_empty_sequential)
    responses: dict[tuple[str, ...], CommandResult] = field(default_factory=_empty_responses)
    calls: list[tuple[tuple[str, ...], str | None]] = field(default_factory=_empty_calls)

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        self.calls.append((key, cwd))
        queued = self.sequential.get(key)
        if queued:
            return queued.pop(0)
        if key in self.responses:
            return self.responses[key]
        msg = f"unexpected argv: {argv!r} cwd={cwd!r}"
        raise AssertionError(msg)


def _runner(*, checks: list[str], pr_states: list[str] | None = None, merge: list[CommandResult] | None = None) -> RecordingRunner:
    states = pr_states or ["OPEN"] * 20
    return RecordingRunner(
        sequential={
            PR_VIEW: [_cr(PR_VIEW, stdout=_pr(state)) for state in states],
            CHECKS: [_cr(CHECKS, stdout=value) for value in checks],
            MERGE: merge or [_cr(MERGE)],
        },
    )


def _sleeps() -> tuple[list[float], Any]:
    values: list[float] = []

    def sleep_fn(seconds: float) -> None:
        values.append(seconds)

    return values, sleep_fn


def test_green_required_checks_guard_then_merge_succeeds() -> None:
    runner = _runner(checks=[_checks("pass"), _checks("pass")])
    result = design_log_ship.run_design_log_ci_merge(
        runner,
        pr=1,
        repo="o/r",
        cwd="/tmp/wt",
        merge_cwd="/repo",
        sleep_fn=lambda _s: None,
    )
    assert result.ok is True
    assert (MERGE, "/repo") in runner.calls
    assert all(call[0][0] != "git" for call in runner.calls)


def test_already_merged_before_checks_skips_merge() -> None:
    runner = _runner(checks=[], pr_states=["MERGED"])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is True
    assert result.already_merged is True
    assert all(call[0] != MERGE for call in runner.calls)


def test_guard_observes_already_merged_skips_merge() -> None:
    runner = _runner(checks=[_checks("pass")], pr_states=["OPEN", "MERGED"])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is True
    assert result.already_merged is True
    assert all(call[0] != MERGE for call in runner.calls)


def test_does_not_call_full_ci_monitor_or_git(monkeypatch: pytest.MonkeyPatch) -> None:
    def fail_poll_ci(*_args: object, **_kwargs: object) -> None:
        pytest.fail("poll_ci called")

    def fail_gather_status(*_args: object, **_kwargs: object) -> None:
        pytest.fail("gather_status called")

    monkeypatch.setattr("ci_monitor.poll_ci", fail_poll_ci)
    monkeypatch.setattr("ci_monitor.gather_status", fail_gather_status)
    runner = _runner(checks=[_checks("pass"), _checks("pass")])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is True
    assert not any(call[0][0] == "git" for call in runner.calls)


@pytest.mark.parametrize("bad_status", ["unknown"])
def test_required_non_pass_buckets_fail_closed(bad_status: str) -> None:
    runner = _runner(checks=[_checks(bad_status)])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is False
    assert all(call[0] != MERGE for call in runner.calls)


def test_failed_required_check_transient_logs_reruns_then_merges() -> None:
    runner = _runner(checks=[_checks("fail"), _checks("pass"), _checks("pass")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, stdout="Could not resolve host: api.github.com")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(
        runner,
        pr=1,
        repo="o/r",
        cwd="/tmp/wt",
        merge_cwd="/repo",
        sleep_fn=lambda _s: None,
    )
    assert result.ok is True
    assert (RERUN, "/tmp/wt") in runner.calls
    assert (MERGE, "/repo") in runner.calls


def test_failed_required_check_no_signature_does_not_rerun() -> None:
    runner = _runner(checks=[_checks("fail")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, stdout="assertion failed")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is False
    assert all(call[0] != RERUN for call in runner.calls)


def test_failed_logs_wait_until_ready_before_rerun(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 3)
    runner = _runner(checks=[_checks("fail"), _checks("fail"), _checks("pass"), _checks("pass")])
    runner.sequential[RUN_VIEW] = [
        _cr(RUN_VIEW, rc=1, stderr="is still in progress; logs will be available"),
        _cr(RUN_VIEW, stdout="Could not resolve host: api.github.com"),
    ]
    runner.responses[RERUN] = _cr(RERUN)
    sleeps, sleep_fn = _sleeps()
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=sleep_fn)
    assert result.ok is True
    assert sleeps[:2] == [float(config.CI_WAIT_POLL_INTERVAL_SEC), float(config.CI_WAIT_POLL_INTERVAL_SEC)]


def test_failed_logs_wait_budget_resets_for_distinct_run_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 1)
    runner = _runner(
        checks=[
            _checks("fail", "999"),
            _checks("fail", "1000"),
            _checks("fail", "1000"),
            _checks("pass"),
            _checks("pass"),
        ],
    )
    run_view_999 = ("gh", "run", "view", "999", "--repo", "o/r", "--log-failed")
    run_view_1000 = ("gh", "run", "view", "1000", "--repo", "o/r", "--log-failed")
    rerun_1000 = ("gh", "run", "rerun", "1000", "--repo", "o/r", "--failed")
    runner.responses[run_view_999] = _cr(run_view_999, rc=1, stderr="is still in progress; logs will be available")
    runner.sequential[run_view_1000] = [
        _cr(run_view_1000, rc=1, stderr="is still in progress; logs will be available"),
        _cr(run_view_1000, stdout="Could not resolve host: api.github.com"),
    ]
    runner.responses[rerun_1000] = _cr(rerun_1000)
    sleeps, sleep_fn = _sleeps()
    result = design_log_ship.run_design_log_ci_merge(
        runner,
        pr=1,
        repo="o/r",
        cwd="/tmp/wt",
        merge_cwd="/repo",
        sleep_fn=sleep_fn,
    )
    assert result.ok is True
    assert sleeps[:2] == [float(config.CI_WAIT_POLL_INTERVAL_SEC), float(config.CI_WAIT_POLL_INTERVAL_SEC)]
    assert (rerun_1000, "/tmp/wt") in runner.calls


def test_failed_logs_never_ready_does_not_rerun(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 1)
    runner = _runner(checks=[_checks("fail"), _checks("fail")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, rc=1, stderr="still unavailable")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is False
    assert all(call[0] != RERUN for call in runner.calls)


def test_failed_check_without_run_id_fails() -> None:
    rows = json.dumps([{"name": "ci", "state": "FAILURE", "bucket": "fail", "link": ""}])
    runner = _runner(checks=[rows])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is False
    assert all(call[0] != RERUN for call in runner.calls)


def test_stale_failure_after_rerun_settles_then_merges(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 3)
    runner = _runner(checks=[_checks("fail"), _checks("fail"), _checks("pending"), _checks("pass"), _checks("pass")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, stdout="Could not resolve host: api.github.com")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is True
    assert [call[0] for call in runner.calls].count(RERUN) == 1


def test_stale_failure_through_settle_budget_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 1)
    runner = _runner(checks=[_checks("fail"), _checks("fail"), _checks("fail")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, stdout="Could not resolve host: api.github.com")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is False
    assert [call[0] for call in runner.calls].count(RERUN) == 1


def test_later_distinct_failure_after_one_rerun_fails() -> None:
    runner = _runner(checks=[_checks("fail", "999"), _checks("fail", "1000")])
    runner.responses[RUN_VIEW] = _cr(RUN_VIEW, stdout="Could not resolve host: api.github.com")
    runner.responses[RERUN] = _cr(RERUN)
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is False
    assert [call[0] for call in runner.calls].count(RERUN) == 1


def test_merge_transient_failure_then_success() -> None:
    runner = _runner(
        checks=[_checks("pass"), _checks("pass")],
        merge=[
            _cr(MERGE, rc=1, stderr="Could not resolve host: api.github.com"),
            _cr(MERGE),
        ],
    )
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is True
    assert [call[0] for call in runner.calls].count(MERGE) == 2


def test_merge_deterministic_failure_returns_false() -> None:
    runner = _runner(checks=[_checks("pass"), _checks("pass")], merge=[_cr(MERGE, rc=1, stderr="GraphQL: forbidden")])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo")
    assert result.ok is False


def test_pending_checks_sleep_then_merge() -> None:
    runner = _runner(checks=[_checks("pending"), _checks("pass"), _checks("pass")])
    sleeps, sleep_fn = _sleeps()
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=sleep_fn)
    assert result.ok is True
    assert sleeps == [float(config.CI_WAIT_POLL_INTERVAL_SEC)]


def test_pending_checks_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(design_log_ship, "_ci_wait_poll_budget", lambda: 1)
    runner = _runner(checks=[_checks("pending"), _checks("pending")])
    result = design_log_ship.run_design_log_ci_merge(runner, pr=1, repo="o/r", cwd="/tmp/wt", merge_cwd="/repo", sleep_fn=lambda _s: None)
    assert result.ok is False
    assert all(call[0] != MERGE for call in runner.calls)


def test_main_valid_explicit_repo_does_not_resolve(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = _runner(checks=[_checks("pass"), _checks("pass")])
    monkeypatch.setattr(design_log_ship, "proc", runner)

    def fail_resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        pytest.fail("resolve_repo called")

    monkeypatch.setattr("larch.git.gh.resolve_repo", fail_resolve_repo)
    rc = design_log_ship.main(["--pr-number", "1", "--repo", "o/r", "--cwd", "/tmp/wt", "--merge-cwd", "/repo"])
    assert rc == 0
    assert "PUBLISH_OK=true" in capsys.readouterr().out


def test_main_rejects_invalid_explicit_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = _runner(checks=[])
    monkeypatch.setattr(design_log_ship, "proc", runner)

    def fail_resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        pytest.fail("resolve_repo called")

    monkeypatch.setattr("larch.git.gh.resolve_repo", fail_resolve_repo)
    rc = design_log_ship.main(["--pr-number", "1", "--repo", "../bad"])
    assert rc == 2
    assert not runner.calls


def test_main_resolves_repo_when_omitted(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = _runner(checks=[_checks("pass"), _checks("pass")])
    monkeypatch.setattr(design_log_ship, "proc", runner)
    def resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        return "o/r"

    monkeypatch.setattr("larch.git.gh.resolve_repo", resolve_repo)
    rc = design_log_ship.main(["--pr-number", "1", "--cwd", "/tmp/wt", "--merge-cwd", "/repo"])
    assert rc == 0
    assert "PUBLISH_OK=true" in capsys.readouterr().out


# --- design-log-sweep reconciliation -----------------------------------------

PR_LIST = ("gh", "pr", "list", "--repo", "o/r", "--state", "open", "--json", "number,title,headRefName", "--limit", "200")


def _pr_view_for(n: int) -> tuple[str, ...]:
    return ("gh", "pr", "view", str(n), "--repo", "o/r", "--json", "number,url,state,headRefName,mergedAt,mergeStateStatus")


def _checks_for(n: int) -> tuple[str, ...]:
    return ("gh", "pr", "checks", str(n), "--repo", "o/r", "--json", "name,state,bucket,link", "--required")


def _merge_for(n: int) -> tuple[str, ...]:
    return ("gh", "pr", "merge", str(n), "--repo", "o/r", "--squash", "--admin", "--delete-branch")


def _list_json(prs: list[tuple[int, str]]) -> str:
    return json.dumps([{"number": n, "title": t, "headRefName": f"larch-logs/design-{n}"} for n, t in prs])


def test_sweep_merges_green_and_skips_pending() -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A"), (11, "chore(larch-logs): design run B")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("OPEN")),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
            _merge_for(10): _cr(_merge_for(10)),
            _pr_view_for(11): _cr(_pr_view_for(11), stdout=_pr("OPEN")),
            _checks_for(11): _cr(_checks_for(11), stdout=_checks("pending")),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert {it.pr: it.outcome for it in items} == {10: "merged", 11: "skipped-not-green"}
    assert (_merge_for(10), None) in runner.calls
    assert all(call[0] != _merge_for(11) for call in runner.calls)


def test_sweep_filters_non_design_log_titles() -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A"), (20, "feat: unrelated")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("MERGED")),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert [it.pr for it in items] == [10]
    assert all(call[0] != _pr_view_for(20) for call in runner.calls)


def test_sweep_excludes_spoofed_title_on_foreign_branch() -> None:
    rows = json.dumps(
        [
            {"number": 10, "title": "chore(larch-logs): design run A", "headRefName": "larch-logs/design-A"},
            {"number": 30, "title": "chore(larch-logs): sneaky", "headRefName": "attacker/pwn"},
        ],
    )
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=rows),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("MERGED")),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert [it.pr for it in items] == [10]
    assert all(call[0] != _pr_view_for(30) for call in runner.calls)


def test_sweep_skips_already_merged() -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("MERGED")),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert [(it.pr, it.outcome) for it in items] == [(10, "already-merged")]
    assert all(call[0] != _checks_for(10) for call in runner.calls)
    assert all(call[0] != _merge_for(10) for call in runner.calls)


def test_sweep_dry_run_does_not_merge() -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("OPEN")),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", dry_run=True, sleep_fn=lambda _s: None)
    assert [(it.pr, it.outcome) for it in items] == [(10, "would-merge")]
    assert all(call[0] != _merge_for(10) for call in runner.calls)


def test_sweep_reports_merge_failed() -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("OPEN")),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
            _merge_for(10): _cr(_merge_for(10), rc=1, stderr="GraphQL: forbidden"),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert [(it.pr, it.outcome) for it in items] == [(10, "merge-failed")]


def test_sweep_merge_failure_rechecks_concurrent_merge() -> None:
    runner = RecordingRunner(
        sequential={
            _pr_view_for(10): [
                _cr(_pr_view_for(10), stdout=_pr("OPEN")),
                _cr(_pr_view_for(10), stdout=_pr("MERGED")),
            ],
        },
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
            _merge_for(10): _cr(_merge_for(10), rc=1, stderr="GraphQL: Pull request is already merged"),
        },
    )
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert [(it.pr, it.outcome) for it in items] == [(10, "already-merged")]


def test_sweep_empty_when_no_design_log_prs() -> None:
    runner = RecordingRunner(responses={PR_LIST: _cr(PR_LIST, stdout=_list_json([(20, "feat: unrelated")]))})
    items = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)
    assert not items


def test_sweep_list_failure_raises() -> None:
    runner = RecordingRunner(responses={PR_LIST: _cr(PR_LIST, rc=1, stderr="gh: rate limited")})
    with pytest.raises(design_log_ship.DesignLogSweepError):
        _ = design_log_ship.run_design_log_sweep(runner, repo="o/r", sleep_fn=lambda _s: None)


def test_sweep_main_explicit_repo_emits_summary(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("OPEN")),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
            _merge_for(10): _cr(_merge_for(10)),
        },
    )
    monkeypatch.setattr(design_log_ship, "proc", runner)

    def fail_resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        pytest.fail("resolve_repo called")

    monkeypatch.setattr("larch.git.gh.resolve_repo", fail_resolve_repo)
    rc = design_log_ship.sweep_main(["--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "SWEEP_TOTAL=1" in out
    assert "SWEEP_MERGED=1" in out
    assert "SWEEP_FAILED=0" in out


def test_sweep_main_rejects_invalid_repo(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(design_log_ship, "proc", runner)

    def fail_resolve_repo(_runner: object, *, cwd: str | None = None) -> str:
        _ = cwd
        pytest.fail("resolve_repo called")

    monkeypatch.setattr("larch.git.gh.resolve_repo", fail_resolve_repo)
    rc = design_log_ship.sweep_main(["--repo", "../bad"])
    assert rc == 2
    assert not runner.calls


def test_sweep_main_merge_failed_returns_one(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses={
            PR_LIST: _cr(PR_LIST, stdout=_list_json([(10, "chore(larch-logs): design run A")])),
            _pr_view_for(10): _cr(_pr_view_for(10), stdout=_pr("OPEN")),
            _checks_for(10): _cr(_checks_for(10), stdout=_checks("pass")),
            _merge_for(10): _cr(_merge_for(10), rc=1, stderr="GraphQL: forbidden"),
        },
    )
    monkeypatch.setattr(design_log_ship, "proc", runner)
    rc = design_log_ship.sweep_main(["--repo", "o/r"])
    out = capsys.readouterr().out
    assert rc == 1
    assert "SWEEP_FAILED=1" in out
