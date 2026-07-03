# pyright: reportPrivateUsage=false
"""Unit tests for ci_monitor.py (stub Runner; no bash)."""

from __future__ import annotations

import json
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, cast

from pathlib import Path

import pytest

from larch.implement import ci_monitor
from larch.core import config
from larch.core import redact
from larch.agents.agents import LaunchFailure, TierAttempt
from larch.git.gh import FailedJob
from larch.outcomes import Outcome
from larch.core.proc import CommandResult
from larch.core.run_context import RunContext
from larch.report import run_log_flush
from larch.report import run_logs
from test_support import make_run_context

REPO_ROOT = Path(__file__).resolve().parents[3]


def _new_response_map() -> dict[tuple[str, ...], CommandResult]:
    return {}


def _new_prefix_responses() -> list[tuple[tuple[str, ...], CommandResult]]:
    return []


def _new_sequential_map() -> dict[tuple[str, ...], list[CommandResult]]:
    return {}


def _new_call_log() -> list[tuple[str, ...]]:
    return []


@dataclass
# Keep this keyed runner local; use test_support.py for simple queue runners.
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
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
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
        if key[:3] == ("git", "commit", "--file"):
            return _cr(key, 0)
        msg = f"unexpected argv: {argv}"
        raise AssertionError(msg)


def _cr(argv: Sequence[str], rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def _seed_warning_flush_inputs(tmpdir: Path, *, warning: str) -> None:
    _ = (tmpdir / ".execution-issues-step7a-reached").write_text("", encoding="utf-8")
    _ = (tmpdir / "execution-issues.md").write_text(
        f"### Warnings\n- {warning}\n",
        encoding="utf-8",
    )


def test_available_tiers_tracks_config_order() -> None:
    assert ci_monitor._available_tiers() == config.FIXER_TIER_ORDER  # pylint: disable=protected-access


@pytest.mark.parametrize("tier", config.FIXER_TIER_ORDER)
def test_default_launch_fn_uses_python_agent_launcher(
    tier: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    runner = RecordingRunner()
    runner.prefix_responses.append(
        ((sys.executable,), _cr((sys.executable,), stdout="LAUNCHER_EXIT=0\n")),
    )
    logs = ci_monitor.LogCollectResult(text="", state="ready")
    launch_fn = ci_monitor._make_default_launch_fn(
        runner,
        run_id="run-1",
        repo="o/r",
        plan_file=None,
        logs=logs,
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    attempt = launch_fn(tier)
    assert attempt.launcher_exit == 0
    argv = runner.calls[-1]
    assert argv[2] == "agent"
    assert argv[3] == f"launch-{tier}-ci"
    assert str(tmp_path / f"ci-fix-{tier}.out") in argv


def test_default_launch_fn_reads_launcher_done_sidecar_when_fd3_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    class DoneRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
            output = Path(argv[argv.index("--output") + 1])
            _ = output.write_text("tool prose\n", encoding="utf-8")
            _ = output.with_suffix(output.suffix + ".done").write_text("1\n", encoding="utf-8")
            self.calls.append(tuple(argv))
            return _cr(argv, 0, stdout="", stderr="")

    runner = DoneRunner()
    logs = ci_monitor.LogCollectResult(text="", state="ready")
    launch_fn = ci_monitor._make_default_launch_fn(
        runner,
        run_id="run-1",
        repo="o/r",
        plan_file=None,
        logs=logs,
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    attempt = launch_fn("codex")
    assert attempt.wrapper_rc == 0
    assert attempt.launcher_exit == 1


def test_default_launch_fn_prefers_done_sentinel_over_stdout_launcher_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))

    class DoneRunner(RecordingRunner):
        def run(self, argv: Sequence[str], **_kwargs: object) -> CommandResult:
            output = Path(argv[argv.index("--output") + 1])
            _ = output.write_text("tool prose\n", encoding="utf-8")
            _ = output.with_suffix(output.suffix + ".done").write_text("1\n", encoding="utf-8")
            self.calls.append(tuple(argv))
            return _cr(argv, 0, stdout="LAUNCHER_EXIT=0\n", stderr="")

    runner = DoneRunner()
    logs = ci_monitor.LogCollectResult(text="", state="ready")
    launch_fn = ci_monitor._make_default_launch_fn(
        runner,
        run_id="run-1",
        repo="o/r",
        plan_file=None,
        logs=logs,
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    attempt = launch_fn("codex")
    assert attempt.launcher_exit == 1


def test_default_launch_fn_missing_metadata_uses_wrapper_rc(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    runner = RecordingRunner()
    runner.prefix_responses.append(((sys.executable,), _cr((sys.executable,), rc=7)))
    logs = ci_monitor.LogCollectResult(text="", state="ready")
    launch_fn = ci_monitor._make_default_launch_fn(
        runner,
        run_id="run-1",
        repo="o/r",
        plan_file=None,
        logs=logs,
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    attempt = launch_fn("claude")
    assert attempt.wrapper_rc == 7
    assert attempt.launcher_exit == 7


def _status(
    *,
    status: str = "pass",
    behind: int = 0,
    merged: bool = False,
    merge_state: str = "CLEAN",
) -> dict[tuple[str, ...], CommandResult]:
    pr_json = json.dumps(
        {
            "number": 1,
            "url": "https://github.com/o/r/pull/1",
            "state": "MERGED" if merged else "OPEN",
            "headRefName": "feature",
            "mergeStateStatus": merge_state,
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
        ("gh", "pr", "view", "1", "--repo", "o/r", "--json", "number,url,state,headRefName,mergedAt,mergeStateStatus"): _cr(
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
        ("gh", "pr", "checks", "1", "--repo", "o/r"): _cr(
            ("gh", "pr", "checks", "text"),
            stdout="",
        ),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(
            ("git", "rev-list", "--count"),
            stdout=f"{behind}\n",
        ),
        ("git", "log", "--format=%s", "HEAD..origin/main"): _cr(
            ("git", "log"),
            stdout="",
        ),
    }


def test_default_launch_fn_ingests_external_token_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(ci_monitor, "_implement_tmpdir", lambda: str(tmp_path))

    def fake_build_launch_argv(tier: str, **_kwargs: object) -> list[str]:
        return ["launch", tier]

    monkeypatch.setattr(ci_monitor.agents, "build_launch_argv", fake_build_launch_argv)
    ingest_calls: list[dict[str, object]] = []

    def fake_ingest(_runner: RecordingRunner, **kwargs: object) -> bool:
        ingest_calls.append(kwargs)
        return True

    monkeypatch.setattr(ci_monitor.agents, "ingest_launcher_token_sidecar", fake_ingest)
    runner.responses[("launch", "codex")] = _cr(
        ("launch", "codex"),
        stdout=f"LAUNCHER_EXIT=0\nTOKEN_RECORD={tmp_path / 'codex.token-record'}\n",
    )
    launch_fn = ci_monitor._make_default_launch_fn(  # pyright: ignore[reportPrivateUsage]
        runner,
        run_id="run",
        repo="owner/repo",
        plan_file=None,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    attempt = launch_fn("codex")
    assert attempt.launcher_exit == 0
    assert len(ingest_calls) == 1
    assert ingest_calls[0]["tmpdir"] == str(tmp_path)
    assert ingest_calls[0]["implement_tmpdir"] == str(tmp_path)
    assert ingest_calls[0]["cwd"] == str(tmp_path)
    assert ingest_calls[0]["allow_output_fallback"] is True
    assert isinstance(ingest_calls[0]["seen"], set)


@pytest.mark.parametrize(("tier", "expected_fallback"), [("codex", True), ("cursor", True), ("claude", False)])
def test_default_launch_fn_gates_output_fallback_by_tier(
    tier: str,
    expected_fallback: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(ci_monitor, "_implement_tmpdir", lambda: str(tmp_path))

    def fake_build_launch_argv(given_tier: str, **_kwargs: object) -> list[str]:
        return ["launch", given_tier]

    monkeypatch.setattr(ci_monitor.agents, "build_launch_argv", fake_build_launch_argv)
    ingest_calls: list[dict[str, object]] = []

    def fake_ingest(_runner: RecordingRunner, **kwargs: object) -> bool:
        ingest_calls.append(kwargs)
        return False

    monkeypatch.setattr(ci_monitor.agents, "ingest_launcher_token_sidecar", fake_ingest)
    runner.responses[("launch", tier)] = _cr(("launch", tier), stdout="LAUNCHER_EXIT=0\n")
    launch_fn = ci_monitor._make_default_launch_fn(  # pyright: ignore[reportPrivateUsage]
        runner,
        run_id="run",
        repo="owner/repo",
        plan_file=None,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )

    _ = launch_fn(tier)

    assert ingest_calls[0]["allow_output_fallback"] is expected_fallback


def test_default_launch_fn_clears_fallback_sidecar_before_codex_launch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(ci_monitor, "_implement_tmpdir", lambda: str(tmp_path))

    def fake_build_launch_argv(tier: str, **_kwargs: object) -> list[str]:
        return ["launch", tier, "--output", str(tmp_path / f"ci-fix-{tier}.out")]

    monkeypatch.setattr(ci_monitor.agents, "build_launch_argv", fake_build_launch_argv)

    def fake_ingest(_runner: RecordingRunner, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(ci_monitor.agents, "ingest_launcher_token_sidecar", fake_ingest)

    class FreshnessRunner(RecordingRunner):
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> CommandResult:
            output = Path(argv[argv.index("--output") + 1])
            fallback = Path(f"{output}.token-record")
            assert not fallback.exists()
            _ = fallback.write_text("TOOL=codex\nTOTAL=1\n", encoding="utf-8")
            return super().run(
                argv,
                timeout=timeout,
                cwd=cwd,
                env=env,
                check=check,
                stdout=stdout,
                stderr=stderr,
            )

    runner = FreshnessRunner()
    output = tmp_path / "ci-fix-codex.out"
    _ = Path(f"{output}.token-record").write_text("stale\n", encoding="utf-8")
    runner.responses[("launch", "codex", "--output", str(output))] = _cr(
        ("launch", "codex"),
        stdout="LAUNCHER_EXIT=0\n",
    )
    launch_fn = ci_monitor._make_default_launch_fn(  # pyright: ignore[reportPrivateUsage]
        runner,
        run_id="run",
        repo="owner/repo",
        plan_file=None,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )

    attempt = launch_fn("codex")

    assert attempt.launcher_exit == 0


def test_default_launch_fn_dedups_repeated_external_token_sidecar(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner()
    token_record = tmp_path / "codex.token-record"
    monkeypatch.setattr(ci_monitor, "_implement_tmpdir", lambda: str(tmp_path))

    def fake_build_launch_argv(tier: str, **_kwargs: object) -> list[str]:
        return ["launch", tier]

    monkeypatch.setattr(ci_monitor.agents, "build_launch_argv", fake_build_launch_argv)
    seen_ids: list[int] = []
    ingested: list[str] = []

    def fake_ingest(_runner: RecordingRunner, **kwargs: object) -> bool:
        seen_obj = kwargs["seen"]
        assert isinstance(seen_obj, set)
        seen = cast("set[str]", seen_obj)
        seen_ids.append(id(seen))
        path = str(token_record)
        if path in seen:
            return False
        seen.add(path)
        ingested.append(path)
        return True

    monkeypatch.setattr(ci_monitor.agents, "ingest_launcher_token_sidecar", fake_ingest)
    runner.responses[("launch", "codex")] = _cr(
        ("launch", "codex"),
        stdout=f"LAUNCHER_EXIT=1\nTOKEN_RECORD={token_record}\n",
    )
    launch_fn = ci_monitor._make_default_launch_fn(  # pyright: ignore[reportPrivateUsage]
        runner,
        run_id="run",
        repo="owner/repo",
        plan_file=None,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        output_dir=str(tmp_path),
        cwd=str(tmp_path),
        failure_log_paths=[],
    )
    _ = launch_fn("codex")
    _ = launch_fn("codex")
    assert ingested == [str(token_record)]
    assert len(set(seen_ids)) == 1


@pytest.mark.parametrize(
    ("status", "behind", "conflicted", "iteration", "rebase_count", "fix_attempts", "expected"),
    [
        ("merged", 0, False, 0, 0, 0, "already_merged"),
        ("pass", 0, False, 0, 0, 0, "merge"),
        ("pass", 1, False, 0, 0, 0, "merge"),
        ("pass", 1, True, 0, 0, 0, "rebase"),
        ("pending", 1, False, 0, 0, 0, "wait"),
        ("pending", 0, False, 0, 0, 0, "wait"),
        ("fail", 1, False, 0, 0, 0, "rebase_then_evaluate"),
        ("fail", 0, False, 0, 0, 0, "evaluate_failure"),
        ("error", 0, False, 0, 0, 0, "bail"),
        ("pass", 0, False, 50, 0, 0, "merge"),
        ("pending", 0, False, 50, 0, 0, "bail"),
        ("fail", 0, False, 0, 0, 10, "bail"),
        ("fail", 0, False, 0, 20, 0, "bail"),
    ],
)
def test_decide_parity_table(
    status: str,
    behind: int,
    conflicted: bool,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    expected: str,
) -> None:
    ci_status = ci_monitor.CiStatus(
        status=status,
        behind_count=behind,
        failed_run_id=None,
        conflicted=conflicted,
    )
    decision = ci_monitor.decide(
        ci_status,
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
    )
    assert decision.action == expected


def test_decide_pending_behind_waits_for_inflight_ci() -> None:
    """A pending run on a behind-but-unconflicted branch waits, never rebases.

    Rebasing a healthy in-flight run force-pushes a new head that must
    re-register checks, which previously produced a false no-ci-checks-observed
    stall (issue #5217). The branch is squash-mergeable while behind, so the
    monitor waits for CI to finish on the current head.
    """
    decision = ci_monitor.decide(
        ci_monitor.CiStatus(status="pending", behind_count=3, failed_run_id=None),
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
    )
    assert decision.action == "wait"


@pytest.mark.parametrize(
    ("status", "iteration", "rebase_count", "fix_attempts", "expected_reason"),
    [
        ("error", 0, 0, 0, config.CI_DECIDE_BAIL_STATUS_ERROR),
        ("pending", config.CI_MONITOR_MAX_ITERATIONS, 0, 0, config.CI_DECIDE_BAIL_TIMEOUT),
        ("pending", 0, config.CI_MONITOR_MAX_REBASES, 0, config.CI_DECIDE_BAIL_TOO_MANY_REBASES),
        ("fail", 0, 0, config.CI_MONITOR_MAX_FIX_ATTEMPTS, config.CI_DECIDE_BAIL_FIX_ATTEMPTS_EXHAUSTED),
    ],
)
def test_decide_bail_reasons_match_ci_decide_tokens(
    status: str,
    iteration: int,
    rebase_count: int,
    fix_attempts: int,
    expected_reason: str,
) -> None:
    decision = ci_monitor.decide(
        ci_monitor.CiStatus(status=status, behind_count=0, failed_run_id=None),
        iteration=iteration,
        rebase_count=rebase_count,
        fix_attempts=fix_attempts,
    )
    assert decision.action == "bail"
    assert decision.bail_reason == expected_reason


def test_gather_status_merged_short_circuit() -> None:
    runner = RecordingRunner(_status(merged=True))
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "merged"
    assert status.behind_count == 0


@pytest.mark.parametrize(
    ("merge_state", "expected_conflicted"),
    [
        ("DIRTY", True),
        ("UNKNOWN", True),
        ("BEHIND", False),
        ("CLEAN", False),
    ],
)
def test_gather_status_conflicted_from_merge_state(
    merge_state: str,
    expected_conflicted: bool,
) -> None:
    runner = RecordingRunner(_status(status="pass", merge_state=merge_state))
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.conflicted is expected_conflicted


def test_gather_status_fail_extracts_run_id() -> None:
    runner = RecordingRunner(_status(status="fail"))
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "fail"
    assert status.failed_run_id == "999"
    assert status.checks_observed is True
    assert status.checks_empty is False


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
    assert status.checks_observed is False
    assert status.checks_empty is False


def test_gather_status_pr_view_failure_still_probes_checks() -> None:
    responses = _status(status="pass")
    responses[
        (
            "gh",
            "pr",
            "view",
            "1",
            "--repo",
            "o/r",
            "--json",
            "number,url,state,headRefName,mergedAt,mergeStateStatus",
        )
    ] = _cr(("gh", "pr", "view"), rc=1)
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "pass"
    assert status.conflicted is True


def test_gather_status_behind_probe_fail_preserves_checks_status() -> None:
    responses = _status(status="pass")
    responses[("git", "rev-list", "--count", "HEAD..origin/main")] = _cr(
        ("git", "rev-list", "--count"),
        rc=1,
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "pass"
    assert status.behind_count == 0
    assert status.checks_observed is True
    assert status.checks_empty is False


def test_gather_status_behind_probe_fail_preserves_empty_rollup_observation() -> None:
    responses = _status(status="empty")
    responses[("git", "rev-list", "--count", "HEAD..origin/main")] = _cr(
        ("git", "rev-list", "--count"),
        rc=1,
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "pending"
    assert status.behind_count == 0
    assert status.checks_observed is True
    assert status.checks_empty is True


def test_gather_status_empty_checks_without_grace_records_empty_observation() -> None:
    runner = RecordingRunner(_status(status="empty"))

    status = ci_monitor.gather_status(runner, pr=1, repo="o/r", empty_checks_grace=0)

    assert status.status == "pending"
    assert status.checks_empty is True
    assert status.checks_observed is True


@pytest.mark.parametrize("check_status", ["pass", "pending", "fail"])
def test_gather_status_non_empty_checks_record_observed_not_empty(check_status: str) -> None:
    runner = RecordingRunner(_status(status=check_status))

    status = ci_monitor.gather_status(runner, pr=1, repo="o/r", empty_checks_grace=0)

    assert status.status == check_status
    assert status.checks_empty is False
    assert status.checks_observed is True


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
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert sleeps == [5.0]


def test_checks_rollup_empty_zero_row_json() -> None:
    runner = RecordingRunner(_status(status="empty"))

    assert ci_monitor._checks_rollup_empty(  # pylint: disable=protected-access
        runner,
        pr=1,
        repo="o/r",
        cwd=None,
    )
    assert (
        "gh",
        "pr",
        "checks",
        "1",
        "--repo",
        "o/r",
    ) in runner.calls


def test_checks_rollup_empty_pending_json_is_not_empty() -> None:
    runner = RecordingRunner(_status(status="pending"))

    assert not ci_monitor._checks_rollup_empty(  # pylint: disable=protected-access
        runner,
        pr=1,
        repo="o/r",
        cwd=None,
    )
    assert (
        "gh",
        "pr",
        "checks",
        "1",
        "--repo",
        "o/r",
    ) not in runner.calls


def test_checks_rollup_empty_uses_empty_text_fallback_after_empty_json() -> None:
    responses = _status(status="empty")
    responses[("gh", "pr", "checks", "1", "--repo", "o/r")] = _cr(
        ("gh", "pr", "checks", "text"),
        stdout="  \n",
    )
    runner = RecordingRunner(responses)

    assert ci_monitor._checks_rollup_empty(  # pylint: disable=protected-access
        runner,
        pr=1,
        repo="o/r",
        cwd=None,
    )


def test_resolve_checks_observation_derives_empty_rollup_without_rollup_probe(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail_rollup_probe(*_args: object, **_kwargs: object) -> bool:
        raise AssertionError("observation must not re-fetch rollup emptiness")

    monkeypatch.setattr(ci_monitor, "_checks_rollup_empty", fail_rollup_probe)
    runner = RecordingRunner(_status(status="empty"))

    observation = ci_monitor._resolve_checks_observation(  # pyright: ignore[reportPrivateUsage]
        runner,
        pr=1,
        repo="o/r",
        empty_checks_grace=0,
        sleep_fn=lambda _s: None,
        cwd=None,
    )

    assert observation.status == "pending"
    assert observation.rollup_empty is True
    assert runner.calls.count(
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
        )
    ) == 1
    assert runner.calls.count(("gh", "pr", "checks", "1", "--repo", "o/r")) == 1


def test_resolve_checks_observation_uses_same_text_fallback_for_non_empty_rollup() -> None:
    responses = _status(status="empty")
    responses[("gh", "pr", "checks", "1", "--repo", "o/r")] = _cr(
        ("gh", "pr", "checks", "text"),
        stdout="lint\tpass\thttps://github.com/o/r/actions/runs/42\n",
    )
    runner = RecordingRunner(responses)

    observation = ci_monitor._resolve_checks_observation(  # pyright: ignore[reportPrivateUsage]
        runner,
        pr=1,
        repo="o/r",
        empty_checks_grace=0,
        sleep_fn=lambda _s: None,
        cwd=None,
    )

    assert observation.status == "pass"
    assert observation.failed_run_id is None
    assert observation.rollup_empty is False
    assert observation.observed is True


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
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED


def test_poll_ci_startup_deadline_empty_rollup_bails_no_blocking_sleep() -> None:
    runner = RecordingRunner(_status(status="empty"))
    json_key = (
        "gh",
        "pr",
        "checks",
        "1",
        "--repo",
        "o/r",
        "--json",
        "name,state,bucket,link",
    )
    text_key = ("gh", "pr", "checks", "1", "--repo", "o/r")
    now = {"value": 0.0}
    sleeps: list[float] = []

    def clock() -> float:
        return now["value"]

    def sleep_fn(sec: float) -> None:
        sleeps.append(sec)
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=20,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=sleep_fn,
        clock=clock,
    )

    assert status.status == "NO_CHECKS"
    assert status.behind_count == 0
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    assert sleeps == [
        float(config.CI_WAIT_POLL_INTERVAL_SEC),
        float(config.CI_WAIT_POLL_INTERVAL_SEC),
    ]
    assert runner.calls.count(json_key) == 3
    assert runner.calls.count(text_key) == 3


def test_poll_ci_startup_deadline_clears_when_checks_appear() -> None:
    responses = _status(status="empty")
    json_key = (
        "gh",
        "pr",
        "checks",
        "1",
        "--repo",
        "o/r",
        "--json",
        "name,state,bucket,link",
    )
    empty = _cr(("gh", "pr", "checks"), stdout="[]")
    pending = _cr(
        ("gh", "pr", "checks"),
        stdout=json.dumps(
            [{"name": "lint", "state": "IN_PROGRESS", "bucket": "pending", "link": ""}],
        ),
    )
    runner = RecordingRunner(responses)
    runner.sequential[json_key] = [empty, empty, pending, empty, empty]
    now = {"value": 0.0}
    sleeps: list[float] = []

    def clock() -> float:
        return now["value"]

    def sleep_fn(sec: float) -> None:
        sleeps.append(sec)
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=20,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=50.0,
        sleep_fn=sleep_fn,
        clock=clock,
    )

    assert status.status == "pending"
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED
    assert sleeps == [10.0, 10.0, 10.0, 10.0, 10.0]
    assert runner.calls.count(json_key) == 5
    assert runner.calls.count(("gh", "pr", "checks", "1", "--repo", "o/r")) == 4


def test_poll_ci_startup_deadline_ignores_pending_in_flight_checks() -> None:
    runner = RecordingRunner(_status(status="pending"))
    now = {"value": 0.0}
    sleeps: list[float] = []

    def clock() -> float:
        return now["value"]

    def sleep_fn(sec: float) -> None:
        sleeps.append(sec)
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=10,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=20.0,
        sleep_fn=sleep_fn,
        clock=clock,
    )

    assert status.status == "pending"
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED
    assert sleeps == [10.0, 10.0]


def test_poll_ci_startup_deadline_does_not_run_before_non_wait_decision() -> None:
    runner = RecordingRunner(_status(status="pending", behind=1))

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=10,
        iteration=0,
        # rebase_count at the cap forces a decisive non-wait "bail"; pending now
        # always waits even when behind (issue #5217), so the cap is how this test
        # still exercises the "decide returned non-wait" short-circuit.
        rebase_count=config.CI_MONITOR_MAX_REBASES,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=lambda _s: None,
    )

    assert status.status == "pending"
    assert status.checks_empty is False
    assert status.checks_observed is True
    assert decision.action == "bail"
    assert ("gh", "pr", "checks", "1", "--repo", "o/r") not in runner.calls


def test_poll_ci_startup_deadline_expiry_returns_before_next_sleep(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(_status(status="empty"))
    now = {"value": 0.0}
    sleeps: list[float] = []

    def clock() -> float:
        return now["value"]

    def sleep_fn(sec: float) -> None:
        sleeps.append(sec)
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=10,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=sleep_fn,
        clock=clock,
    )
    captured = capsys.readouterr()

    assert status.status == "NO_CHECKS"
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    assert sleeps == [10.0]
    assert "poll 1/" in captured.err
    assert "poll 2/" not in captured.err


def test_poll_ci_startup_deadline_expiry_copies_live_snapshot_fields(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live = ci_monitor.CiStatus(
        status="pending",
        behind_count=4,
        failed_run_id="77",
        conflicted=True,
        pr_view_ok=False,
        checks_empty=True,
        checks_observed=True,
    )

    def fake_gather_status(*_args: object, **_kwargs: object) -> ci_monitor.CiStatus:
        return live

    def always_wait(
        _status: ci_monitor.CiStatus,
        **_kwargs: object,
    ) -> ci_monitor.Decision:
        return ci_monitor.Decision(action="wait")

    now = {"value": 0.0}

    def sleep_fn(sec: float) -> None:
        now["value"] += sec

    monkeypatch.setattr(ci_monitor, "gather_status", fake_gather_status)
    monkeypatch.setattr(ci_monitor, "decide", always_wait)

    status, decision = ci_monitor.poll_ci(
        RecordingRunner(),
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=10,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=sleep_fn,
        clock=lambda: now["value"],
    )

    assert status == ci_monitor.CiStatus(
        status="NO_CHECKS",
        behind_count=4,
        failed_run_id="77",
        conflicted=True,
        pr_view_ok=False,
        checks_empty=True,
        checks_observed=True,
    )
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED


def test_poll_ci_startup_deadline_accumulates_when_behind_probe_fails() -> None:
    responses = _status(status="empty")
    responses[("git", "rev-list", "--count", "HEAD..origin/main")] = _cr(
        ("git", "rev-list", "--count"),
        rc=1,
    )
    runner = RecordingRunner(responses)
    now = {"value": 0.0}

    def sleep_fn(sec: float) -> None:
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=10,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=sleep_fn,
        clock=lambda: now["value"],
    )

    assert status.status == "NO_CHECKS"
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED


def test_poll_ci_fetch_failure_does_not_clear_startup_deadline_accounting() -> None:
    responses = _status(status="empty")
    fetch_key = ("git", "fetch", "origin", "main", "--quiet")
    responses[fetch_key] = _cr(("git", "fetch"), 0)
    runner = RecordingRunner(responses)
    runner.sequential[fetch_key] = [
        _cr(("git", "fetch"), 0),
        _cr(("git", "fetch"), 1),
        _cr(("git", "fetch"), 0),
    ]
    now = {"value": 0.0}

    def sleep_fn(sec: float) -> None:
        now["value"] += sec

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=20,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=100.0,
        sleep_fn=sleep_fn,
        clock=lambda: now["value"],
    )

    assert status.status == "NO_CHECKS"
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED
    assert runner.calls.count(fetch_key) == 3
    assert runner.calls.count(
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
        )
    ) == 2


def test_poll_ci_startup_deadline_zero_preserves_empty_pending_timeout() -> None:
    runner = RecordingRunner(_status(status="empty"))

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        empty_checks_startup_deadline_sec=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=10.0,
        sleep_fn=lambda _s: None,
    )

    assert status.status == "pending"
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED


def test_poll_ci_repeated_status_errors_use_stale_token(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_gather_status(*_args: object, **_kwargs: object) -> ci_monitor.CiStatus:
        return ci_monitor.CiStatus(status="error", behind_count=0, failed_run_id=None)

    monkeypatch.setattr(ci_monitor, "gather_status", fake_gather_status)
    _, decision = ci_monitor.poll_ci(
        RecordingRunner(),
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=60.0,
        sleep_fn=lambda _s: None,
    )
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_STATUS_STALE


def test_poll_ci_error_normalization_preserves_checks_observation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_gather_status(*_args: object, **_kwargs: object) -> ci_monitor.CiStatus:
        return ci_monitor.CiStatus(
            status="",
            behind_count=0,
            failed_run_id="55",
            conflicted=True,
            pr_view_ok=False,
            checks_empty=True,
            checks_observed=True,
        )

    monkeypatch.setattr(ci_monitor, "gather_status", fake_gather_status)

    status, decision = ci_monitor.poll_ci(
        RecordingRunner(),
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

    assert status.status == "pending"
    assert status.failed_run_id == "55"
    assert status.conflicted is True
    assert status.pr_view_ok is False
    assert status.checks_empty is True
    assert status.checks_observed is True
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED


def test_poll_ci_emits_poll_breadcrumb_to_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(_status(status="pending", behind=0))
    clock_values = iter((1.0, 8.0, 8.0))
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
        clock=lambda: next(clock_values, 8.0),
    )
    captured = capsys.readouterr()
    assert decision.action == "bail"
    assert captured.out == ""
    assert "ci_monitor: poll 1/" in captured.err
    assert "after 7s" in captured.err
    assert "sleeping" in captured.err


def test_poll_ci_pr_view_fail_open_triggers_rebase_when_behind() -> None:
    responses = _status(status="pass", behind=1)
    responses[("gh", "pr", "view", "1", "--repo", "o/r", "--json", "number,url,state,headRefName,mergedAt,mergeStateStatus")] = _cr(
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
    assert decision.action == "rebase"


def test_poll_ci_retry_preserves_conflicted_state(monkeypatch: pytest.MonkeyPatch) -> None:
    status_calls = {"n": 0}

    def fake_gather_status(*_args: object, **_kwargs: object) -> ci_monitor.CiStatus:
        status_calls["n"] += 1
        if status_calls["n"] == 1:
            return ci_monitor.CiStatus(
                status="",
                behind_count=2,
                failed_run_id=None,
                conflicted=True,
                pr_view_ok=False,
            )
        return ci_monitor.CiStatus(
            status="pass",
            behind_count=2,
            failed_run_id=None,
            conflicted=True,
            pr_view_ok=True,
        )

    monkeypatch.setattr(ci_monitor, "gather_status", fake_gather_status)
    _, decision = ci_monitor.poll_ci(
        RecordingRunner({}),
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
    assert decision.action == "rebase"


def test_monitor_evaluate_failure_bails_to_first_fixer(monkeypatch: pytest.MonkeyPatch) -> None:
    """Failed CI with no rebase needed → immediate first-fixer-non-health bail.

    The main agent re-reads and fixes the CI failure on takeover, so monitor()
    must hand off immediately without calling evaluate_failure (no log download,
    transient classification, rerun, or agentic fix).
    """

    def fake_poll_ci(*_args: object, **_kwargs: object) -> tuple[ci_monitor.CiStatus, ci_monitor.Decision]:
        return (
            ci_monitor.CiStatus("fail", 0, "42"),
            ci_monitor.Decision("evaluate_failure"),
        )

    def boom_evaluate_failure(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        raise AssertionError("monitor must not call evaluate_failure on the immediate-bail path")

    monkeypatch.setattr(ci_monitor, "poll_ci", fake_poll_ci)
    monkeypatch.setattr(ci_monitor, "evaluate_failure", boom_evaluate_failure)

    result = ci_monitor.monitor(RecordingRunner(), pr=1, repo="o/r")

    assert result.result.outcome is Outcome.NEEDS_USER_INPUT
    assert result.result.detail == "first-fixer-non-health"
    assert result.goto_rebase is False
    assert result.failed_run_id == "42"


def test_monitor_transient_bail_maps_to_transient(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_poll_ci(*_args: object, **_kwargs: object) -> tuple[ci_monitor.CiStatus, ci_monitor.Decision]:
        return (
            ci_monitor.CiStatus("pending", 0, None),
            ci_monitor.Decision("bail", "HTTP 502 Bad Gateway"),
        )

    monkeypatch.setattr(
        ci_monitor,
        "poll_ci",
        fake_poll_ci,
    )

    result = ci_monitor.monitor(RecordingRunner(), pr=1, repo="o/r")

    assert result.result.outcome is Outcome.TRANSIENT
    assert result.result.detail == "HTTP 502 Bad Gateway"


def test_monitor_already_merged_short_circuit_ok() -> None:
    runner = RecordingRunner(_status(merged=True))

    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        sleep_fn=lambda _s: None,
    )

    assert result.action == "already_merged"
    assert result.ci_status == "merged"
    assert result.result.outcome is Outcome.OK
    assert result.goto_rebase is False


def test_monitor_pr_view_probe_fail_open_rebases_when_behind() -> None:
    responses = _status(status="pass", behind=1)
    responses[
        (
            "gh",
            "pr",
            "view",
            "1",
            "--repo",
            "o/r",
            "--json",
            "number,url,state,headRefName,mergedAt,mergeStateStatus",
        )
    ] = _cr(("gh", "pr", "view"), rc=1)
    runner = RecordingRunner(responses)

    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        sleep_fn=lambda _s: None,
    )

    assert result.action == "rebase"
    assert result.goto_rebase is True
    assert result.ci_status == "pass"


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
        FailedJob(name="python-pyright", conclusion="failure"),
        FailedJob(name="gitleaks", conclusion="failure"),
        FailedJob(name="bad name!", conclusion="failure"),
    )
    classified = ci_monitor.classify_failed_jobs(jobs)
    assert classified.count == 4
    assert classified.fixable[0].name == "lint"
    assert classified.fixable[0].shard == "1"
    assert classified.fixable[1].name == "python-pyright"
    assert classified.unfixable[0].name == "gitleaks"


def test_classify_failed_jobs_excludes_aggregator_gates() -> None:
    # Gate jobs (e.g. test-harnesses-gate) mirror their matrix and have no local
    # fix; they are excluded from the count and from both buckets so a redundant
    # gate failure does not force local-unfixable.
    jobs = (
        FailedJob(name="test-harnesses-gate", conclusion="failure"),
        FailedJob(name="lint", conclusion="failure"),
        FailedJob(name="python-tests-gate", conclusion="failure"),
    )
    classified = ci_monitor.classify_failed_jobs(jobs)
    assert classified.count == 1
    assert [j.name for j in classified.fixable] == ["lint"]
    assert not classified.unfixable


def test_collect_failed_logs_redacts_tail() -> None:
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
    assert "is still in progress" in result.text


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
        ("python-lint", "", ("make", "py-lint-main")),
        ("python-pyright", "", ("make", "py-typecheck")),
        ("test-harnesses", "2", ("make", "test-harnesses-2")),
        ("unknown", "", None),
    ],
)
def test_per_job_command_table(
    name: str,
    shard: str,
    expected: tuple[str, ...] | None,
) -> None:
    assert ci_monitor.per_job_command(name=name, shard=shard) == expected


def test_verify_job_locally_rc() -> None:
    runner = RecordingRunner(
        {
            ("make", "py-lint-main"): _cr(("make", "py-lint-main"), 0),
            ("make", "py-typecheck"): _cr(("make", "py-typecheck"), 0),
        },
    )
    assert ci_monitor.verify_job_locally(runner=runner, name="python-lint", shard="", cwd="/tmp") is True
    assert ci_monitor.verify_job_locally(runner=runner, name="python-pyright", shard="", cwd="/tmp") is True


def _python_toolchain_stubs(name: str = "python-lint") -> dict[tuple[str, ...], CommandResult]:
    req_dev = str(REPO_ROOT / "python" / "requirements-dev.txt")
    tools_by_name = {
        "python-lint": ("ruff", "pylint"),
        "python-pyright": ("pyright",),
        "python-lint-duplicate-code": ("pylint",),
    }
    responses: dict[tuple[str, ...], CommandResult] = {
        ("python3", "-m", "pip", "install", "-q", "-r", req_dev): _cr(
            ("python3", "-m", "pip", "install"),
            0,
        ),
    }
    for tool in tools_by_name[name]:
        responses[("command", "-v", tool)] = _cr(("command", "-v", tool), 0)
    return responses


@pytest.mark.parametrize(
    ("name", "expected_tools"),
    [
        ("python-lint", ("ruff", "pylint")),
        ("python-pyright", ("pyright",)),
        ("python-lint-duplicate-code", ("pylint",)),
    ],
)
def test_prepare_python_toolchain_split_tools(
    name: str,
    expected_tools: tuple[str, ...],
) -> None:
    runner = RecordingRunner(_python_toolchain_stubs(name))
    assert ci_monitor.prepare_python_toolchain(runner=runner, name=name, cwd="/tmp") is True
    tool_calls = tuple(call[-1] for call in runner.calls if call[:2] == ("command", "-v"))
    assert tool_calls == expected_tools


def _baseline_responses(head: str = "abc123") -> dict[tuple[str, ...], CommandResult]:
    out: dict[tuple[str, ...], CommandResult] = {
        ("git", "diff", "--name-only"): _cr(("git", "diff"), stdout=""),
        ("git", "ls-files", "--others", "--exclude-standard"): _cr(("git", "ls-files"), stdout=""),
        ("git", "diff", "--name-only", "--cached"): _cr(("git", "diff"), stdout=""),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout=f"{head}\n"),
        ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(("git", "rev-list"), stdout="0\n"),
    }
    out.update(_python_toolchain_stubs())
    return out


def test_run_ci_fix_non_pending_winning_tier_fails_closed(tmp_path: Any) -> None:
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
    responses[("git", "add", "--", "fixed.py")] = _cr(("git", "add"), 0)
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), 0)
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), 0)

    runner = RecordingRunner(responses)
    # baseline captured before vendor runs (empty); vendor adds fixed.py; delta sees it
    runner.sequential[("git", "diff", "--name-only")] = [
        _cr(("git", "diff"), stdout=""),           # _capture_baseline tracked
        _cr(("git", "diff"), stdout="fixed.py\n"), # _delta_paths tracked_now
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
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

        cwd=str(tmp_path),
        launch_fn=launch_fn,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"
    assert not launch_calls


def test_stage_and_push_defer_rebase_uses_typed_rebase_push(tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): _cr(("git", "add"), 0),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): _cr((commit_script,), 0),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(("git", "rev-list"), stdout="1\n"),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "merge-base", "--is-ancestor", "origin/main", "HEAD"): _cr(("git", "merge-base"), rc=1),
        ("git", "rebase", "origin/main"): _cr(("git", "rebase"), 0),
        ("make", "py-lint-main"): _cr(("make", "py-lint-main"), 0),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): _cr(
            ("git", "ls-remote"),
            stdout="remote\trefs/heads/feature\n",
        ),
        ("git", "fetch", "origin", "feature", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "status", "--porcelain", "--untracked-files=all"): _cr(("git", "status"), stdout=""),
        (
            "git",
            "push",
            "--force-with-lease=refs/heads/feature:remote",
            "origin",
        ): _cr(("git", "push"), 0),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    runner = RecordingRunner(responses)
    pushed, _head, _delta, did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="codex",
        delta_paths=("fixed.py",),
        context=ci_monitor.StagePushContext(classified=classified),
    )
    assert pushed is True
    assert did_rebase is True
    assert pending is False
    assert ("git", "rebase", "origin/main") in runner.calls


def test_stage_and_push_warning_refreshes_before_normal_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): _cr(("git", "add"), 0),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): _cr((commit_script,), 0),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(("git", "rev-list"), stdout="0\n"),
    }
    order: list[str] = []

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_logs.RefreshSkip:
        order.append("flush")
        return ci_monitor.run_logs.RefreshSkip(skipped=False, reason="")

    def fake_push(*_args: object, **_kwargs: object) -> CommandResult:
        order.append("push")
        return _cr(("git", "push"), 0)

    def callback() -> bool:
        order.append("callback")
        return True

    monkeypatch.setattr(ci_monitor.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ci_monitor.git, "push", fake_push)
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="claude",
        delta_paths=("fixed.py",),
        context=ci_monitor.StagePushContext(
            run_context=make_run_context(tmpdir=str(tmp_path), run_id="run-abc"),
            pre_push_log_refresh=callback,
        ),
    )

    assert pushed is True
    assert pending is False
    assert order == ["callback", "flush", "push"]


def test_stage_and_push_warning_refresh_skip_blocks_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): _cr(("git", "add"), 0),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): _cr((commit_script,), 0),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(("git", "rev-list"), stdout="0\n"),
    }
    order: list[str] = []

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_logs.RefreshSkip:
        order.append("flush")
        return ci_monitor.run_logs.RefreshSkip(skipped=True, reason=ci_monitor.config.REFRESH_SKIP_VOLATILE_ONLY)

    def fake_push(*_args: object, **_kwargs: object) -> CommandResult:
        order.append("push")
        return _cr(("git", "push"), 0)

    def callback() -> bool:
        order.append("callback")
        return True

    monkeypatch.setattr(ci_monitor.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ci_monitor.git, "push", fake_push)
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="claude",
        delta_paths=("fixed.py",),
        context=ci_monitor.StagePushContext(
            run_context=make_run_context(tmpdir=str(tmp_path), run_id="run-abc"),
            pre_push_log_refresh=callback,
        ),
    )

    assert pushed is False
    assert pending is False
    assert order == ["callback", "flush"]


def test_stage_and_push_warning_refresh_commits_before_ci_fix_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): _cr(
            ("git", "ls-remote"),
            stdout="abc123\trefs/heads/feature\n",
        ),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    ctx = make_run_context(tmpdir=str(tmp_path), run_id="run-abc")
    _ = run_logs.init_run(ctx)
    _seed_warning_flush_inputs(tmp_path, warning="architectural-guidelines warning")

    def noop(*_args: object, **_kwargs: object) -> None:
        return None

    def fake_commit(
        *_args: object,
        **_kwargs: object,
    ) -> CommandResult:
        return _cr(("git", "commit"))

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(run_log_flush, "_commit_run", fake_commit)
    monkeypatch.setattr(run_log_flush, "_write_final_report", noop)
    monkeypatch.setattr(run_log_flush, "capture_session_transcript", noop)
    monkeypatch.setattr(run_log_flush, "_render_ledger_reports", noop)
    monkeypatch.setattr(run_log_flush, "_render_token_timing_batches", noop)
    monkeypatch.setattr(run_log_flush, "_refresh_difficulty_record", noop)
    monkeypatch.setattr(run_log_flush, "_stage_vendor_failure_diagnostics", noop)
    monkeypatch.setattr(run_log_flush, "_stage_ship_route_handoff", noop)
    monkeypatch.setattr(run_log_flush, "_reconcile_stalled_summary_backstop", noop)

    def callback() -> bool:
        return True

    def fake_force_push_recovery(*_args: object, **_kwargs: object) -> ci_monitor.git.ForcePushResult:
        run_dir = tmp_path / "larch-logs" / "implement" / "run-abc"
        batch = run_dir / "execution-issues.ndjson"
        assert batch.is_file()
        assert "architectural-guidelines warning" in batch.read_text(encoding="utf-8")
        assert (tmp_path / ".execution-issues-flushed.sha").is_file()
        return ci_monitor.git.ForcePushResult(pushed=True, status="ok")

    monkeypatch.setattr(ci_monitor.git, "force_push_recovery", fake_force_push_recovery)
    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)

    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(
            classified=classified,
            run_context=ctx,
            pre_push_log_refresh=callback,
        ),
    )

    assert pushed is True
    assert pending is False


def test_stage_and_push_warning_refresh_no_logs_commit_allows_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): _cr(
            ("git", "ls-remote"),
            stdout="abc123\trefs/heads/feature\n",
        ),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_logs.RefreshSkip:
        return ci_monitor.run_logs.RefreshSkip(skipped=True, reason=ci_monitor.config.REFRESH_SKIP_NO_LOGS_COMMIT)

    def fake_force_push_recovery(*_args: object, **_kwargs: object) -> ci_monitor.git.ForcePushResult:
        return ci_monitor.git.ForcePushResult(pushed=True, status="ok")

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(ci_monitor.run_logs, "flush_logs_pre", fake_flush)
    monkeypatch.setattr(ci_monitor.git, "force_push_recovery", fake_force_push_recovery)
    monkeypatch.setattr(ci_monitor, "verify_job_locally", fake_verify_job_locally)
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(
            classified=classified,
            run_context=make_run_context(tmpdir=str(tmp_path), run_id="run-abc", no_logs_commit=True),
            pre_push_log_refresh=lambda: True,
        ),
    )

    assert pushed is True
    assert pending is False


def test_pending_retry_verifies_before_force_push(tmp_path: Any) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("make", "py-lint-main"): _cr(("make", "py-lint-main"), 1),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(classified=classified),
    )
    assert pushed is False
    assert pending is False
    assert not any("force-with-lease" in " ".join(call) for call in runner.calls)


def test_pending_retry_verifies_pyright_before_force_push(tmp_path: Any) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("make", "py-typecheck"): _cr(("make", "py-typecheck"), 1),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
    )
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(classified=classified),
    )
    assert pushed is False
    assert pending is False
    assert ("make", "py-typecheck") in runner.calls
    assert not any("force-with-lease" in " ".join(call) for call in runner.calls)


def test_pending_retry_missing_remote_oid_preserves_pending(tmp_path: Any) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("git", "fetch", "origin", "feature", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "rev-parse", "origin/feature"): _cr(("git", "rev-parse"), rc=1),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): _cr(("git", "ls-remote"), rc=2),
    }
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(classified=ci_monitor.ClassifiedJobs(0, (), (), ())),
    )
    assert pushed is False
    assert pending is True


def test_pending_retry_missing_local_remote_ref_uses_ls_remote_lease(tmp_path: Any) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("make", "py-lint-main"): _cr(("make", "py-lint-main"), 0),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): _cr(
            ("git", "ls-remote"),
            stdout="remoteoid\trefs/heads/feature\n",
        ),
        ("git", "fetch", "origin", "feature", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "status", "--porcelain", "--untracked-files=all"): _cr(("git", "status"), stdout=""),
        ("git", "push", "--force-with-lease=refs/heads/feature:remoteoid", "origin"): _cr(("git", "push"), 0),
    }
    runner = RecordingRunner(responses)
    pushed, _head, _delta, _did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="pending-retry",
        delta_paths=(),
        ci_fix_rebase_pending=True,
        context=ci_monitor.StagePushContext(
            classified=ci_monitor.classify_failed_jobs(
                (FailedJob(name="python-lint", conclusion="failure"),),
            ),
        ),
    )
    assert pushed is True
    assert pending is False
    assert ("git", "push", "--force-with-lease=refs/heads/feature:remoteoid", "origin") in runner.calls


def test_evaluate_failure_pending_reload_failed_jobs_before_force_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr(config, "CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS", 1)
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    responses = {
        ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
            ("gh", "run", "view"),
            stdout="FAIL\n",
        ),
        ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
        ("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs"): _cr(
            ("gh", "run", "view"),
            stdout=jobs_json,
        ),
        ("git", "rev-parse", "HEAD"): _cr(("git", "rev-parse"), stdout="head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feature\n"),
        ("make", "py-lint-main"): _cr(("make", "py-lint-main"), rc=1),
    }
    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=str(tmp_path),
        sleep_fn=lambda _s: None,
        ci_fix_rebase_pending=True,
    )
    assert fix.ci_fix_rebase_pending is False
    assert ("make", "py-lint-main") in runner.calls
    assert not any("force-with-lease" in " ".join(call) for call in runner.calls)



def test_run_ci_fix_pending_retry_pins_guidelines_before_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = make_run_context(tmpdir=str(tmp_path), run_id="run-abc")
    calls: list[object] = []

    def fake_try_rev_parse(*_args: object, **_kwargs: object) -> str:
        calls.append("resolve-head")
        return "current-head"

    def fake_pin_or_invalidate(**kwargs: object) -> bool:
        calls.append(("pin", kwargs))
        return False

    def fail_raw_invalidate(*_args: object, **_kwargs: object) -> bool:
        raise AssertionError("pending retry should use pin-before-invalidate helper")

    def fake_stage_and_push(
        *_args: object,
        context: ci_monitor.StagePushContext | None = None,
        delta_paths: tuple[str, ...] = (),
        base_remote: str = "",
        base_ref: str = "",
        ci_fix_rebase_pending: bool = False,
        **_kwargs: object,
    ) -> tuple[bool, str, tuple[str, ...], bool, bool]:
        assert context is not None
        assert context.run_context is ctx
        assert context.pre_push_log_refresh is not None
        assert delta_paths == ()
        assert base_remote == "upstream"
        assert base_ref == "trunk"
        assert ci_fix_rebase_pending is True
        calls.append("before-callback")
        warning_logged = context.pre_push_log_refresh()
        calls.append(("callback-return", warning_logged))
        return True, "current-head", (), False, False

    monkeypatch.setattr(ci_monitor.git, "try_rev_parse", fake_try_rev_parse)
    monkeypatch.setattr(ci_monitor.ship_guidelines, "_pin_or_invalidate_guidelines_note", fake_pin_or_invalidate)
    monkeypatch.setattr(ci_monitor.ship_guidelines, "_invalidate_guidelines_note", fail_raw_invalidate)
    monkeypatch.setattr(ci_monitor, "stage_and_push", fake_stage_and_push)

    fix = ci_monitor.run_ci_fix(
        RecordingRunner(),
        run_id="42",
        repo="o/r",
        classified=ci_monitor.ClassifiedJobs(0, (), (), ()),
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        plan_file=None,
        cwd=str(tmp_path),
        base_remote="upstream",
        base_ref="trunk",
        ci_fix_rebase_pending=True,
        ctx=ctx,
    )

    assert fix.status == "pushed"
    assert calls == [
        "before-callback",
        "resolve-head",
        (
            "pin",
            {
                "implement_tmpdir": str(tmp_path),
                "head_sha": "current-head",
                "base_ref": "upstream/trunk",
                "repo_root": str(tmp_path),
            },
        ),
        ("callback-return", False),
    ]

def test_run_ci_fix_non_pending_after_stage_fails_closed(tmp_path: Any) -> None:
    head = "deadbeef" * 5

    def launch_fn(_tier: str) -> TierAttempt:
        return TierAttempt(
            tier="codex",
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    responses = _baseline_responses(head)
    responses[("git", "add", "--", "fixed.py")] = _cr(("git", "add"), 0)
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), 0)
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), 0)

    runner = RecordingRunner(responses)
    # empty baseline, vendor adds fixed.py; HEAD stays same after push → first-fixer-non-health
    runner.sequential[("git", "diff", "--name-only")] = [
        _cr(("git", "diff"), stdout=""),           # _capture_baseline tracked
        _cr(("git", "diff"), stdout="fixed.py\n"), # _delta_paths tracked_now
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{head}\n"),
    ]
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

        cwd=str(tmp_path),
        launch_fn=launch_fn,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"


def test_run_ci_fix_non_pending_verify_case_fails_closed() -> None:
    def launch_fn(_tier: str) -> TierAttempt:
        return TierAttempt(
            tier="cursor",
            wrapper_rc=0,
            launcher_exit=0,
            failure=LaunchFailure("none", ""),
        )

    responses = _baseline_responses()
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), 1)
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

        cwd=None,
        launch_fn=launch_fn,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"
    assert not any(call[0] == "git" and call[1] == "push" for call in runner.calls)


def test_run_ci_fix_non_pending_unfixable_fails_closed() -> None:
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

        cwd=None,
        launch_fn=lambda _t: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"


def test_evaluate_failure_transient_rerun_only() -> None:
    runner = RecordingRunner(
        {
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                stdout="fatal: unable to access https://github.com/o/r/\n",
            ),
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
    assert ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed") in runner.calls


def test_evaluate_failure_in_progress_defers_launch() -> None:
    launch_count = 0

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_count
        launch_count += 1
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(
        {
            ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
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
    # Fake clock: starts at 0, advances past the in-progress timeout on first sleep
    # so the wait loop exits after one poll without blocking for a real hour.
    clock_val = [0.0]

    def fake_clock() -> float:
        return clock_val[0]

    def fake_sleep(s: float) -> None:
        sleeps.append(s)
        clock_val[0] += ci_monitor.config.CI_MONITOR_IN_PROGRESS_TIMEOUT + 1

    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=fake_sleep,
        clock=fake_clock,
    )
    assert launch_count == 0
    # The wait loop should have slept exactly once at the poll interval before timing out.
    assert sleeps == [float(ci_monitor.config.CI_MONITOR_IN_PROGRESS_POLL_INTERVAL)]
    assert fix.status == "ci-still-in-progress"
    assert fix.detail is not None
    assert "still in progress after" in fix.detail


def test_wait_for_ci_ready_polls_until_ready() -> None:
    """_wait_for_ci_ready polls every 15s and returns once the run exits in_progress."""
    in_progress = _cr(
        ("gh", "run", "view"),
        rc=3,
        stderr="is still in progress; logs will be available",
    )
    ready_log = _cr(("gh", "run", "view"), stdout="FAIL AssertionError\n")
    runner = RecordingRunner({})
    # sleep → poll sequence: one in_progress, then ready on the second poll
    runner.sequential[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = [
        in_progress,
        ready_log,
    ]
    sleeps: list[float] = []
    clock_val = [0.0]

    def fake_clock() -> float:
        return clock_val[0]

    def fake_sleep(s: float) -> None:
        sleeps.append(s)
        clock_val[0] += s

    result = ci_monitor._wait_for_ci_ready(  # pyright: ignore[reportPrivateUsage]
        runner,
        run_id="42",
        repo="o/r",
        sleep_fn=fake_sleep,
        clock=fake_clock,
    )
    # Two sleeps: one before the in_progress poll, one before the ready poll.
    assert sleeps == [
        float(ci_monitor.config.CI_MONITOR_IN_PROGRESS_POLL_INTERVAL),
        float(ci_monitor.config.CI_MONITOR_IN_PROGRESS_POLL_INTERVAL),
    ]
    assert result.state == "ready"


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_deterministic_no_rerun() -> None:
    runner = RecordingRunner(
        {
            ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                stdout="FAIL AssertionError: expected True\n",
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
                stderr="failed",
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
        launch_fn=lambda _t: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        sleep_fn=lambda _s: None,
    )
    assert not any(c[:3] == ("gh", "run", "rerun") for c in runner.calls)
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_exhausted_routes_needs_user_input() -> None:
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), rc=1)
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")
    assert "python-lint" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_per_job_exhausted_routes_needs_user_input() -> None:
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), rc=1)
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_calls
    assert ("make", "py-lint-main") in runner.calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")
    assert "python-lint" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_upfront_ready_stash_when_transient_cap_exhausted() -> None:
    jobs_json = json.dumps({"jobs": []})
    log_responses = [
        _cr(("gh", "run", "view"), stdout="FAIL test\n"),
        _cr(("gh", "run", "view"), stdout="FAIL test\n"),
        _cr(("gh", "run", "view"), stdout="FAIL test\n"),
    ]
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    runner = RecordingRunner(responses)
    runner.sequential[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = log_responses
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=config.CI_MONITOR_TRANSIENT_RERUN_MAX,
        _fix_attempts=0,
        cwd=None,
        launch_fn=lambda _t: TierAttempt("cursor", 0, 1, LaunchFailure("none", "")),
        sleep_fn=lambda _s: None,
    )
    log_calls = [
        c
        for c in runner.calls
        if c[:3] == ("gh", "run", "view") and "--log-failed" in c
    ]
    assert len(log_calls) == 3
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_fixable_jobs_launcher_exhausted_stalls() -> None:
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier, 0, 1, LaunchFailure("none", ""))

    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_vendor_only_push_failed_stalls(tmp_path: Any) -> None:
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    baseline_head = "deadbeef" * 5
    jobs_json = json.dumps({"jobs": []})
    responses = _baseline_responses(baseline_head)
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    responses[("git", "add", "--", "fixed.py")] = _cr(("git", "add"), 0)
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), rc=1)

    runner = RecordingRunner(responses)
    runner.sequential[("git", "diff", "--name-only")] = [
        _cr(("git", "diff"), stdout=""),
        _cr(("git", "diff"), stdout="fixed.py\n"),
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
    ]

    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=str(tmp_path),
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_push_failed_routes_fix_exhausted(tmp_path: Any) -> None:
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier, 0, 0, LaunchFailure("none", ""))

    baseline_head = "deadbeef" * 5
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    responses = _baseline_responses(baseline_head)
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), 0)
    responses[("git", "add", "--", "fixed.py")] = _cr(("git", "add"), 0)
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = _cr(
        (commit_script,),
        0,
    )
    responses[("git", "symbolic-ref", "--short", "HEAD")] = _cr(
        ("git", "symbolic-ref"),
        stdout="feature\n",
    )
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), rc=1)

    runner = RecordingRunner(responses)
    runner.sequential[("git", "diff", "--name-only")] = [
        _cr(("git", "diff"), stdout=""),
        _cr(("git", "diff"), stdout="fixed.py\n"),
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
    ]

    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=str(tmp_path),
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")
    assert "python-lint" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_exhausted_surfaces_job_and_log_tail() -> None:
    """fix-exhausted detail carries the failing job name and redacted log tail."""
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})
    log_tail = "ruff check failed on foo.py:42\nE501 line too long in bar.py\n"
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout=log_tail,
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), rc=1)

    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=lambda _t: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        sleep_fn=lambda _s: None,
    )
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    # Stable reason token stays the prefix so a BAIL_REASON bridge survives.
    assert fix.detail.startswith("ci-fix-exhausted")
    # Failing job name is surfaced so the main agent knows what broke.
    assert "python-lint" in fix.detail
    # Redacted CI log tail (with its run pointer) is surfaced, not just the token.
    assert "ruff check failed on foo.py:42" in fix.detail
    assert "E501 line too long in bar.py" in fix.detail
    assert "CI log (run 42" in fix.detail
    assert "\n" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_launcher_exhausted_stalls() -> None:
    jobs_json = json.dumps({"jobs": []})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = _cr(
        ("gh", "run", "view"),
        stdout="FAIL test\n",
    )
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = _cr(
        ("gh", "run", "view"),
        stdout=jobs_json,
    )
    runner = RecordingRunner(responses)
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=lambda _t: TierAttempt("cursor", 0, 1, LaunchFailure("none", "")),
        sleep_fn=lambda _s: None,
    )
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_jobs_in_progress_defers_vendor() -> None:
    launch_count = 0

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_count
        launch_count += 1
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(
        {
            ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                stdout="FAIL test\n",
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
                rc=3,
                stderr="is still in progress; logs will be available",
            ),
        },
    )
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_count == 0
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_error_logs_defers_fix() -> None:
    launch_count = 0

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_count
        launch_count += 1
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner(
        {
            ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): _cr(
                ("gh", "run", "view"),
                rc=1,
                stderr="logs unavailable",
            ),
        },
    )
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=None,
        launch_fn=launch_fn,
        sleep_fn=lambda _s: None,
    )
    assert launch_count == 0
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")
    assert not any(c[:4] == ("gh", "run", "view", "42") and "--json" in c for c in runner.calls)


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


def test_monitor_rebase_then_evaluate_no_fix() -> None:
    responses = _status(status="fail", behind=1)
    runner = RecordingRunner(responses)

    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        sleep_fn=lambda _s: None,
    )
    assert result.action == "rebase_then_evaluate"
    assert result.goto_rebase is True
    # Behind + failed CI rebases first; it must not download logs or rerun.
    assert not any(c[:3] == ("gh", "run", "view") for c in runner.calls)
    assert not any(c[:3] == ("gh", "run", "rerun") for c in runner.calls)


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


# FINDING_14: poll_ci NO_CHECKS bail
def test_poll_ci_no_checks_bail() -> None:
    """Empty checks with grace → NO_CHECKS bail from poll_ci."""
    responses = _status(status="empty")
    runner = RecordingRunner(responses)
    status, decision = ci_monitor.poll_ci(
        runner,
        pr=1,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=5,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        sleep_fn=lambda _s: None,
    )
    assert decision.action == "bail"
    assert status.status == "NO_CHECKS"
    assert decision.bail_reason == config.CI_WAIT_BAIL_NO_CHECKS_OBSERVED


# FINDING_15: run_ci_fix head-changed
def test_run_ci_fix_non_pending_head_changed_fails_closed() -> None:
    """Non-pending callers fail closed before legacy head-change handling."""
    baseline_head = "aaaa" * 10
    new_head = "bbbb" * 10

    def launch_fn(tier: str) -> TierAttempt:
        return TierAttempt(tier=tier, wrapper_rc=0, launcher_exit=0, failure=LaunchFailure("none", ""))

    responses = _baseline_responses()
    responses[("make", "py-lint-main")] = _cr(("make", "py-lint-main"), 0)
    runner = RecordingRunner(responses)
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{new_head}\n"),
    ]
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        plan_file=None,

        cwd=None,
        launch_fn=launch_fn,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"
    assert not any(c[0] == "git" and c[1] == "push" for c in runner.calls)


# FINDING_16: waterfall short-circuit (pre-verify) → first-fixer-non-health, no stage
def test_run_ci_fix_non_pending_short_circuit_fails_closed() -> None:
    """Non-pending callers fail closed before legacy waterfall launch."""
    call_log: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        call_log.append(tier)
        return TierAttempt(
            tier=tier, wrapper_rc=0, launcher_exit=1, failure=LaunchFailure("other", "unknown")
        )

    responses = _baseline_responses()
    runner = RecordingRunner(responses)
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-lint", conclusion="failure"),),
    )
    fix = ci_monitor.run_ci_fix(
        runner,
        run_id="99",
        repo="o/r",
        classified=classified,
        logs=ci_monitor.LogCollectResult(text="", state="ready"),
        plan_file=None,

        cwd=None,
        launch_fn=launch_fn,
    )
    assert fix.status == "waterfall-failed"
    assert fix.detail == "run_ci_fix: non-pending calls not supported"
    assert not call_log
    assert not any(c[0] == "git" and c[1] == "add" for c in runner.calls)
    assert not any(c[0] == "git" and c[1] == "push" for c in runner.calls)


# FINDING_11: evaluate_failure verify-failed retry
@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_verify_failed_then_pushed(tmp_path: Any) -> None:
    """verify-failed on outer 1, pushed on outer 2; assert launch count and fresh log fetches."""
    launch_calls: list[str] = []

    def launch_fn(tier: str) -> TierAttempt:
        launch_calls.append(tier)
        return TierAttempt(tier=tier, wrapper_rc=0, launcher_exit=0, failure=LaunchFailure("none", ""))

    baseline_head = "abcd" * 10
    new_head = "efgh" * 10
    jobs_json = json.dumps({"jobs": [{"name": "python-lint", "conclusion": "failure"}]})

    commit_script = "cli.py git commit"
    responses: dict[tuple[str, ...], CommandResult] = {
        ("git", "symbolic-ref", "--quiet", "HEAD"): _cr(("git", "symbolic-ref"), 0),
        ("gh", "run", "view", "77", "--repo", "o/r", "--log-failed"): _cr(
            ("gh", "run", "view"), stdout="log"
        ),
        ("gh", "run", "view", "77", "--repo", "o/r", "--json", "jobs"): _cr(
            ("gh", "run", "view"), stdout=jobs_json
        ),
        ("git", "ls-files", "--others", "--exclude-standard"): _cr(("git", "ls-files"), stdout=""),
        ("git", "diff", "--name-only", "--cached"): _cr(("git", "diff"), stdout=""),
        ("git", "add", "--", "fixed.py"): _cr(("git", "add"), 0),
        ("git", "symbolic-ref", "--short", "HEAD"): _cr(("git", "symbolic-ref"), stdout="feat\n"),
        ("git", "fetch", "origin", "main", "--quiet"): _cr(("git", "fetch"), 0),
        ("git", "rev-list", "--count", "HEAD..origin/main"): _cr(("git", "rev-list"), stdout="0\n"),
        ("git", "push", "origin", "feat"): _cr(("git", "push"), 0),
        # both attempts use codex (always first tier, #3994)
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): _cr((commit_script,), 0),
    }
    responses.update(_python_toolchain_stubs())

    runner = RecordingRunner(responses)
    # git diff --name-only: a1 baseline, a1 rollback-tracked, a2 baseline, a2 delta
    runner.sequential[("git", "diff", "--name-only")] = [
        _cr(("git", "diff"), stdout=""),
        _cr(("git", "diff"), stdout=""),
        _cr(("git", "diff"), stdout=""),
        _cr(("git", "diff"), stdout="fixed.py\n"),
    ]
    # git rev-parse HEAD: a1 baseline, a1 head-check, a2 baseline, a2 head-check, a2 post-commit, a2 post-push
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{baseline_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{new_head}\n"),
        _cr(("git", "rev-parse", "HEAD"), stdout=f"{new_head}\n"),
    ]
    # make py-lint-main: fail on attempt 1, pass on attempt 2
    runner.sequential[("make", "py-lint-main")] = [
        _cr(("make", "py-lint-main"), rc=1),
        _cr(("make", "py-lint-main"), rc=0),
    ]

    sleeps: list[float] = []
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="77",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd=str(tmp_path),
        launch_fn=launch_fn,
        sleep_fn=sleeps.append,
    )

    assert fix.status == "pushed"
    assert len(launch_calls) == 2
    log_calls = [
        c for c in runner.calls
        if c == ("gh", "run", "view", "77", "--repo", "o/r", "--log-failed")
    ]
    assert len(log_calls) == 2
    assert sleeps


# FINDING_12: monitor driver mapping tests
def test_monitor_timeout_bail_stalled() -> None:
    """Iteration cap reached → bail → STALLED."""
    runner = RecordingRunner(_status(status="pending"))
    result = ci_monitor.monitor(
        runner,
        pr=1,
        repo="o/r",
        iteration=config.CI_MONITOR_MAX_ITERATIONS,
        sleep_fn=lambda _s: None,
    )
    assert result.result.outcome == Outcome.STALLED
    assert result.result.detail == "ci-timeout"


def test_checks_status_required_true_is_checks_only_and_uses_required_json() -> None:
    responses = {
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
            "--required",
        ): _cr(("gh", "pr", "checks"), stdout=json.dumps([{"name": "ci", "bucket": "pass"}])),
    }
    runner = RecordingRunner(responses)
    status, run_id = ci_monitor.checks_status(runner, pr=1, repo="o/r", required=True)
    assert status == "pass"
    assert run_id is None
    assert runner.calls == [
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
            "--required",
        ),
    ]


def test_gather_status_required_true_passes_required_to_json_checks() -> None:
    responses = _status(status="pass")
    responses[
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
            "--required",
        )
    ] = _cr(("gh", "pr", "checks"), stdout=json.dumps([{"name": "ci", "bucket": "pass"}]))
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r", required=True)
    assert status.status == "pass"
    assert (
        "gh",
        "pr",
        "checks",
        "1",
        "--repo",
        "o/r",
        "--json",
        "name,state,bucket,link",
        "--required",
    ) in runner.calls


def test_poll_ci_required_true_forwards_required_to_gather() -> None:
    responses = _status(status="pass")
    responses[
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
            "--required",
        )
    ] = _cr(("gh", "pr", "checks"), stdout=json.dumps([{"name": "ci", "bucket": "pass"}]))
    runner = RecordingRunner(responses)
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
        required=True,
    )
    assert status.status == "pass"
    assert decision.action == "merge"
    assert any(call[-1] == "--required" for call in runner.calls if call[:3] == ("gh", "pr", "checks"))


def test_required_text_fallback_invokes_gh_required_not_public_helper() -> None:
    responses = {
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
            "--required",
        ): _cr(("gh", "pr", "checks"), rc=1),
        ("gh", "pr", "checks", "1", "--repo", "o/r", "--required"): _cr(
            ("gh", "pr", "checks"),
            stdout="all required checks passed",
        ),
    }
    runner = RecordingRunner(responses)
    status, _ = ci_monitor.checks_status(runner, pr=1, repo="o/r", required=True)
    assert status == "pass"
    assert ("gh", "pr", "checks", "1", "--repo", "o/r", "--required") in runner.calls
    assert ("gh", "pr", "checks", "1", "--repo", "o/r") not in runner.calls


def test_required_json_classifier_pass_only_when_every_row_passes() -> None:
    rows = json.dumps([{"bucket": "pass"}, {"bucket": "pass"}])
    assert ci_monitor._classify_checks_json(rows, required=True) == ("pass", None)  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("bucket", ["cancelled", "skipping", "unknown", "", None])
def test_required_json_classifier_fails_closed_for_non_pass_buckets(bucket: object) -> None:
    row: dict[str, object] = {"name": "ci", "link": "https://github.com/o/r/actions/runs/77"}
    if bucket is not None:
        row["bucket"] = bucket
    assert ci_monitor._classify_checks_json(json.dumps([row]), required=True) == ("fail", "77")  # pyright: ignore[reportPrivateUsage]


def test_required_text_fallback_ambiguous_output_is_not_pass() -> None:
    assert ci_monitor._classify_checks_text("check status unavailable", required=True)[0] == "fail"  # pyright: ignore[reportPrivateUsage]


@pytest.mark.parametrize("bucket", ["cancelled", "skipping", "neutral", "unknown"])
def test_default_optional_json_classifier_remains_lenient_for_non_blocking_buckets(bucket: str) -> None:
    assert ci_monitor._classify_checks_json(json.dumps([{"bucket": bucket}])) == ("pass", None)  # pyright: ignore[reportPrivateUsage]


def test_agentic_fix_delegate_timeout_includes_verify_budget(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "CI_AGENTIC_FIX_MAX_CYCLES", 3)
    monkeypatch.setattr(config, "CI_WAIT_TIMEOUT_SEC", 100)
    monkeypatch.setattr(config, "SUBPROCESS_DEFAULT_TIMEOUT_SEC", 10)

    verify_slots = len(config.CI_FIXABLE_JOBS)
    per_cycle = 100 + 10 + verify_slots * 10
    assert ci_monitor._agentic_fix_delegate_timeout_sec() == 3 * per_cycle  # pyright: ignore[reportPrivateUsage]


def _agentic_timeout_ctx(tmp_path: Path, run_id: str = "42") -> RunContext:
    return make_run_context(
        issue="",
        run_id=run_id,
        tmpdir=str(tmp_path),
        merge=False,
        manifest_path="",
        tool_label="claude",
        pr_number=1,
    )


def test_agentic_fix_timeout_ignores_stale_push_checkpoint(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "ci-agentic-fix"
    checkpoint_dir.mkdir()
    _ = (checkpoint_dir / "ci-agentic-push-checkpoint.latest").write_text(
        "RUN_ID=old-run\n"
        "DELTA_PATHS=fixed.py\n"
        "CI_FIX_REBASE_PENDING=false\n"
        "DETAIL=delegate-timeout-after-push\n",
        encoding="utf-8",
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> CommandResult:
            return _cr(("cli",), rc=config.EXIT_TIMEOUT)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=_agentic_timeout_ctx(tmp_path),
    )

    assert fix.status == "fix-exhausted"
    assert fix.detail == "ci-fix-exhausted: delegate-timeout"


def test_agentic_fix_timeout_trusts_matching_push_checkpoint(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "ci-agentic-fix"
    checkpoint_dir.mkdir()
    _ = (checkpoint_dir / "ci-agentic-push-checkpoint.latest").write_text(
        "RUN_ID=42\n"
        "DELTA_PATHS=fixed.py,other.py\n"
        "CI_FIX_REBASE_PENDING=true\n"
        "DETAIL=delegate-timeout-after-push\n",
        encoding="utf-8",
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> CommandResult:
            return _cr(("cli",), rc=config.EXIT_TIMEOUT)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=_agentic_timeout_ctx(tmp_path),
    )

    assert fix.status == "pushed"
    assert fix.delta_paths == ("fixed.py", "other.py")
    assert fix.ci_fix_rebase_pending is True


def test_agentic_fix_timeout_treats_missing_checkpoint_run_id_as_stale(tmp_path: Path) -> None:
    checkpoint_dir = tmp_path / "ci-agentic-fix"
    checkpoint_dir.mkdir()
    _ = (checkpoint_dir / "ci-agentic-push-checkpoint.latest").write_text(
        "DELTA_PATHS=fixed.py\n"
        "CI_FIX_REBASE_PENDING=false\n",
        encoding="utf-8",
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> CommandResult:
            return _cr(("cli",), rc=config.EXIT_TIMEOUT)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=_agentic_timeout_ctx(tmp_path),
    )

    assert fix.status == "fix-exhausted"


def test_agentic_fix_result_fix_attempted_local_unfixable_promotes_exhausted(tmp_path: Path) -> None:
    detail_file = tmp_path / "exhausted.detail"
    _ = detail_file.write_text(
        "local-unfixable: gitleaks\nFAIL gitleaks\n",
        encoding="utf-8",
    )
    kv = (
        "STATUS=local-unfixable\n"
        "DETAIL=gitleaks\n"
        f"EXHAUSTED_DETAIL_FILE={detail_file}\n"
        "FIX_ATTEMPTED=true\n"
        "DELTA_PATHS=\n"
        "CI_FIX_REBASE_PENDING=false\n"
    )

    class _Runner:
        def run(self, *_args: object, **_kwargs: object) -> CommandResult:
            return _cr(("cli",), stdout=kv)

    fix = ci_monitor._agentic_fix_result(  # pyright: ignore[reportPrivateUsage]
        _Runner(),
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        cwd="/tmp/repo",
        base_remote="origin",
        base_ref="main",
        ctx=RunContext(
            branch="feat",
            issue="",
            repo="o/r",
            run_id="42",
            tmpdir="/tmp/implement",
            merge=False,
            draft=False,
            forked=False,
            manifest_path="",
            tool_label="claude",
            no_admin_fallback=False,
            repo_unavailable=False,
            pr_number=1,
        ),
    )
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert "FAIL gitleaks" in fix.detail


def test_evaluate_failure_pending_push_only_skips_agentic_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agentic_calls = {"n": 0}

    def fake_agentic(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        agentic_calls["n"] += 1
        return ci_monitor.FixResult(status="pushed", winning_tier="claude")

    def fake_run_ci_fix(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        return ci_monitor.FixResult(status="pushed", winning_tier="claude")

    def fake_collect_failed_logs(*_args: object, **_kwargs: object) -> ci_monitor.LogCollectResult:
        return ci_monitor.LogCollectResult(text="", state="ready")

    def fake_read_failed_jobs(*_args: object, **_kwargs: object) -> tuple[list[FailedJob], str]:
        return [], "ready"

    monkeypatch.setattr(ci_monitor, "_agentic_fix_result", fake_agentic)
    monkeypatch.setattr(ci_monitor, "run_ci_fix", fake_run_ci_fix)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)
    monkeypatch.setattr(ci_monitor, "read_failed_jobs", fake_read_failed_jobs)

    runner = RecordingRunner(_baseline_responses())
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=1,
        _fix_attempts=0,
        cwd="/tmp/repo",
        launch_fn=lambda _t: TierAttempt("cursor", 0, 0, LaunchFailure("none", "")),
        ci_fix_rebase_pending=True,
    )
    assert agentic_calls["n"] == 0
    assert fix.status == "pushed"


def test_evaluate_failure_normal_path_uses_agentic_delegate_only(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    agentic_calls = {"n": 0}
    waterfall_calls = {"n": 0}

    def fake_agentic(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        agentic_calls["n"] += 1
        return ci_monitor.FixResult(status="pushed", winning_tier="claude")

    def fake_run_ci_fix(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        waterfall_calls["n"] += 1
        return ci_monitor.FixResult(status="waterfall-failed", detail="should-not-run")

    def fake_collect_failed_logs(
        *_args: object,
        **_kwargs: object,
    ) -> ci_monitor.LogCollectResult:
        return ci_monitor.LogCollectResult(text="", state="ready")

    monkeypatch.setattr(ci_monitor, "_agentic_fix_result", fake_agentic)
    monkeypatch.setattr(ci_monitor, "run_ci_fix", fake_run_ci_fix)
    monkeypatch.setattr(ci_monitor, "collect_failed_logs", fake_collect_failed_logs)

    runner = RecordingRunner(_baseline_responses())
    fix = ci_monitor.evaluate_failure(
        runner,
        pr=1,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=0,
        _fix_attempts=0,
        cwd="/tmp/repo",
        ctx=RunContext(
            branch="feat",
            issue="",
            repo="o/r",
            run_id="42",
            tmpdir="/tmp/implement",
            merge=False,
            draft=False,
            forked=False,
            manifest_path="",
            tool_label="claude",
            no_admin_fallback=False,
            repo_unavailable=False,
            pr_number=1,
        ),
    )
    assert agentic_calls["n"] == 1
    assert waterfall_calls["n"] == 0
    assert fix.status == "pushed"


_PR_VIEW_KEY = (
    "gh",
    "pr",
    "view",
    "1",
    "--repo",
    "o/r",
    "--json",
    "number,url,state,headRefName,mergedAt,mergeStateStatus",
)
_PR_CHECKS_JSON_KEY = (
    "gh",
    "pr",
    "checks",
    "1",
    "--repo",
    "o/r",
    "--json",
    "name,state,bucket,link",
)


def test_gather_status_pr_view_timeout_returns_error() -> None:
    # A hung gh pr view (EXIT_TIMEOUT) must surface as a status failure, not be
    # swallowed into a checks-derived status, so poll_ci can count it (#5066).
    responses = _status(status="pass")
    responses[_PR_VIEW_KEY] = _cr(("gh", "pr", "view"), rc=config.EXIT_TIMEOUT)
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "error"
    assert status.pr_view_ok is False


def test_poll_ci_pr_view_timeout_bails_status_stale() -> None:
    responses = _status(status="pass")
    responses[_PR_VIEW_KEY] = _cr(("gh", "pr", "view"), rc=config.EXIT_TIMEOUT)
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
        timeout=60.0,
        sleep_fn=lambda _s: None,
        clock=lambda: 0.0,
    )
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_STATUS_STALE


def test_gather_status_pr_checks_timeout_returns_error() -> None:
    responses = _status(status="pass")
    responses[_PR_CHECKS_JSON_KEY] = _cr(("gh", "pr", "checks"), rc=config.EXIT_TIMEOUT)
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "error"
    assert status.checks_observed is False


def test_poll_ci_pr_checks_timeout_bails_status_stale() -> None:
    responses = _status(status="pass")
    responses[_PR_CHECKS_JSON_KEY] = _cr(("gh", "pr", "checks"), rc=config.EXIT_TIMEOUT)
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
        timeout=60.0,
        sleep_fn=lambda _s: None,
        clock=lambda: 0.0,
    )
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_STATUS_STALE


def test_gather_status_fetch_timeout_returns_error() -> None:
    responses = _status(status="pass")
    responses[("git", "fetch", "origin", "main", "--quiet")] = _cr(
        ("git", "fetch"),
        rc=config.EXIT_TIMEOUT,
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "error"
    assert status.checks_observed is False


def test_gather_status_behind_count_timeout_preserves_checks_observation() -> None:
    responses = _status(status="pass")
    responses[("git", "rev-list", "--count", "HEAD..origin/main")] = _cr(
        ("git", "rev-list", "--count"),
        rc=config.EXIT_TIMEOUT,
    )
    runner = RecordingRunner(responses)
    status = ci_monitor.gather_status(runner, pr=1, repo="o/r")
    assert status.status == "pending"
    assert status.checks_observed is True
    assert status.behind_count == 0


def test_poll_ci_emits_query_heartbeat_and_transition_breadcrumbs(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(_status(status="pass"))
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
        sleep_fn=lambda _s: None,
    )
    captured = capsys.readouterr()
    assert decision.action == "merge"
    assert captured.out == ""
    assert "CI status query #1 in progress" in captured.err
    assert "-> merge" in captured.err


def test_poll_ci_suspend_gap_emits_breadcrumb(
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(_status(status="pending", behind=0))
    now = {"value": 0.0}
    sleep_calls = {"n": 0}

    def clock() -> float:
        return now["value"]

    def sleep_fn(_sec: float) -> None:
        sleep_calls["n"] += 1
        # Simulate a host-suspend real-time gap on the first poll only so the loop
        # still terminates on poll-budget exhaustion afterward.
        now["value"] += 200.0 if sleep_calls["n"] == 1 else 10.0

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
        sleep_fn=sleep_fn,
        clock=clock,
    )
    captured = capsys.readouterr()
    assert decision.action == "bail"
    assert decision.bail_reason == config.CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED
    assert "host suspend" in captured.err
