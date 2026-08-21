# pyright: reportPrivateUsage=false
"""Unit tests for ci_monitor.py (stub Runner; no bash)."""

from __future__ import annotations

import json
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
from test_support import make_run_context, ok

REPO_ROOT = Path(__file__).resolve().parents[3]
_RUST_GIT = str(ci_monitor.larch_entrypoint(ci_monitor._REPO_ROOT))
_RUST_REBASE = (
    _RUST_GIT,
    "push",
    "rebase",
    "--no-push",
    "--keep-on-conflict",
    "--base-remote",
    "origin",
    "--base-ref",
    "main",
)
_RUST_REBASE_ABORT = (_RUST_GIT, "git", "rebase-abort")


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
        lookup = key
        if key[:3] == (_RUST_GIT, "git", "stage"):
            lookup = ("git", "add", "--", *key[3:])
        elif key[:3] == (_RUST_GIT, "git", "commit"):
            lookup = ("cli.py git commit", *key[3:])
        queued = self.sequential.get(lookup)
        if queued:
            return queued.pop(0)
        if lookup in self.responses:
            return self.responses[lookup]
        for prefix, result in self.prefix_responses:
            if key[: len(prefix)] == prefix:
                return result
        if key[:3] == ("git", "commit", "--file"):
            return ok(key)
        msg = f"unexpected argv: {argv}"
        raise AssertionError(msg)


def _cr(argv: Sequence[str], rc: int = 0, stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(tuple(argv), rc, stdout, stderr, 0.01)


def test_poll_ci_consumes_rust_wait_wire_through_verified_entrypoint() -> None:
    runner = RecordingRunner(
        prefix_responses=[
            (
                (_RUST_GIT, "ci", "wait"),
                _cr(
                    (_RUST_GIT, "ci", "wait"),
                    stdout=(
                        "ACTION=evaluate_failure\n"
                        "CI_STATUS=fail\n"
                        "BEHIND_COUNT=2\n"
                        "CONFLICTED=false\n"
                        "FAILED_RUN_ID=123\n"
                        "BAIL_REASON=\n"
                        "ITERATION=4\n"
                        "ELAPSED=8\n"
                    ),
                ),
            ),
        ],
    )

    status, decision = ci_monitor.poll_ci(
        runner,
        pr=7,
        repo="o/r",
        base_remote="upstream",
        base_ref="main",
        empty_checks_grace=12,
        empty_checks_startup_deadline_sec=30,
        iteration=4,
        rebase_count=1,
        fix_attempts=2,
        timeout=60,
    )

    assert status == ci_monitor.CiStatus("fail", 2, "123", conflicted=False)
    assert decision == ci_monitor.Decision("evaluate_failure")
    argv = runner.calls[0]
    assert argv[:3] == (_RUST_GIT, "ci", "wait")
    assert argv[argv.index("--base-remote") + 1] == "upstream"
    assert argv[argv.index("--empty-checks-startup-deadline") + 1] == "30"


def test_poll_ci_fails_closed_on_invalid_rust_wait_wire() -> None:
    runner = RecordingRunner(
        prefix_responses=[
            (
                (_RUST_GIT, "ci", "wait"),
                _cr(
                    (_RUST_GIT, "ci", "wait"),
                    stdout=(
                        "ACTION=merge\n"
                        "CI_STATUS=pass\n"
                        "BEHIND_COUNT=0\n"
                        "CONFLICTED=false\n"
                        "FAILED_RUN_ID=\n"
                        "ITERATION=0\n"
                        "ELAPSED=1\n"
                    ),
                ),
            ),
        ],
    )
    status, decision = ci_monitor.poll_ci(
        runner,
        pr=7,
        repo="o/r",
        base_remote="origin",
        base_ref="main",
        empty_checks_grace=0,
        iteration=0,
        rebase_count=0,
        fix_attempts=0,
        timeout=1,
    )
    assert status.status == "error"
    assert decision == ci_monitor.Decision("bail", config.CI_WAIT_BAIL_UNEXPECTED_EXIT)


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
        ((_RUST_GIT, "agent"), ok((_RUST_GIT, "agent"), "LAUNCHER_EXIT=0\n")),
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
    assert argv[0] == _RUST_GIT
    assert argv[1] == "agent"
    assert argv[2] == f"launch-{tier}-ci"
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
            return ok(argv)

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
            return ok(argv, "LAUNCHER_EXIT=0\n")

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
    runner.prefix_responses.append(((_RUST_GIT, "agent"), _cr((_RUST_GIT, "agent"), rc=7)))
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
        ("gh", "pr", "view", "1", "--repo", "o/r", "--json", "number,url,state,headRefName,mergedAt,mergeStateStatus"): ok(("gh", "pr", "view"), pr_json),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        (
            "gh",
            "pr",
            "checks",
            "1",
            "--repo",
            "o/r",
            "--json",
            "name,state,bucket,link",
        ): ok(("gh", "pr", "checks"), checks),
        ("gh", "pr", "checks", "1", "--repo", "o/r"): ok(("gh", "pr", "checks", "text")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list", "--count"), f"{behind}\n"),
        ("git", "log", "--format=%s", "HEAD..origin/main"): ok(("git", "log")),
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
    runner.responses[("launch", "codex")] = ok(("launch", "codex"), f"LAUNCHER_EXIT=0\nTOKEN_RECORD={tmp_path / 'codex.token-record'}\n")
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
    runner.responses[("launch", tier)] = ok(("launch", tier), "LAUNCHER_EXIT=0\n")
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
    runner.responses[("launch", "codex", "--output", str(output))] = ok(("launch", "codex"), "LAUNCHER_EXIT=0\n")
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
    runner.responses[("launch", "codex")] = ok(("launch", "codex"), f"LAUNCHER_EXIT=1\nTOKEN_RECORD={token_record}\n")
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
    responses[("gh", "pr", "checks", "1", "--repo", "o/r")] = ok(("gh", "pr", "checks", "text"), "  \n")
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
    responses[("gh", "pr", "checks", "1", "--repo", "o/r")] = ok(("gh", "pr", "checks", "text"), "lint\tpass\thttps://github.com/o/r/actions/runs/42\n")
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


@pytest.mark.parametrize(
    ("status", "decision", "goto_rebase", "outcome", "detail"),
    [
        ("merged", ci_monitor.Decision("already_merged"), False, Outcome.OK, ""),
        ("pass", ci_monitor.Decision("merge"), False, Outcome.OK, ""),
        ("pass", ci_monitor.Decision("rebase"), True, Outcome.OK, ""),
        ("fail", ci_monitor.Decision("rebase_then_evaluate"), True, Outcome.OK, ""),
        (
            "fail",
            ci_monitor.Decision("bail", "fix-attempts-exhausted"),
            False,
            Outcome.NEEDS_USER_INPUT,
            "fix-attempts-exhausted",
        ),
        ("pending", ci_monitor.Decision("bail", "ci-timeout"), False, Outcome.STALLED, "ci-timeout"),
    ],
)
def test_monitor_preserves_rust_wait_state_handoff(
    monkeypatch: pytest.MonkeyPatch,
    status: str,
    decision: ci_monitor.Decision,
    goto_rebase: bool,
    outcome: Outcome,
    detail: str,
) -> None:
    observed = ci_monitor.CiStatus(status, 2, "42", conflicted=True)

    def fake_poll_ci(*_args: object, **_kwargs: object) -> tuple[ci_monitor.CiStatus, ci_monitor.Decision]:
        return observed, decision

    monkeypatch.setattr(ci_monitor, "poll_ci", fake_poll_ci)
    result = ci_monitor.monitor(
        RecordingRunner(),
        pr=1,
        repo="o/r",
        iteration=4,
        ci_fix_rebase_pending=True,
    )

    assert result.action == decision.action
    assert result.ci_status == status
    assert result.behind_count == 2
    assert result.failed_run_id == "42"
    assert result.goto_rebase is goto_rebase
    assert result.iterations == 4
    assert result.result.outcome is outcome
    assert result.result.detail == detail
    assert result.ci_fix_rebase_pending is True


def test_wait_for_pr_merge_observes_open_then_merged(
    capsys: pytest.CaptureFixture[str],
) -> None:
    key = (
        "gh",
        "pr",
        "view",
        "1",
        "--repo",
        "o/r",
        "--json",
        "number,url,state,headRefName,mergedAt,mergeStateStatus",
    )
    runner = RecordingRunner(
        sequential={
            key: [
                _cr(
                    key,
                    stdout=(
                        '{"number":1,"url":"u","state":"OPEN",'
                        '"headRefName":"feat","mergedAt":null}'
                    ),
                ),
                _cr(
                    key,
                    stdout=(
                        '{"number":1,"url":"u","state":"MERGED",'
                        '"headRefName":"feat","mergedAt":"2026-08-10T00:00:00Z"}'
                    ),
                ),
            ],
        },
    )
    sleeps: list[float] = []

    merged = ci_monitor.wait_for_pr_merge(
        runner,
        pr=1,
        repo="o/r",
        timeout=2,
        poll_interval=1,
        sleep_fn=sleeps.append,
    )

    assert merged.state == "MERGED"
    assert sleeps == [1]
    assert "queued PR #1 is still open; waiting 1s for merge" in capsys.readouterr().err


def test_wait_for_pr_merge_times_out_without_claiming_completion() -> None:
    key = (
        "gh",
        "pr",
        "view",
        "1",
        "--repo",
        "o/r",
        "--json",
        "number,url,state,headRefName,mergedAt,mergeStateStatus",
    )
    runner = RecordingRunner(
        responses={
            key: _cr(
                key,
                stdout=(
                    '{"number":1,"url":"u","state":"OPEN",'
                    '"headRefName":"feat","mergedAt":null}'
                ),
            ),
        },
    )

    with pytest.raises(ci_monitor.ShipError, match="did not merge"):
        _ = ci_monitor.wait_for_pr_merge(
            runner,
            pr=1,
            repo="o/r",
            timeout=1,
            poll_interval=1,
            sleep_fn=lambda _delay: None,
        )


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
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): ok(("gh", "run", "view"), log_body),
        },
    )
    result = ci_monitor.collect_failed_logs(runner, run_id="42", repo="o/r")
    assert result.state == "ready"
    assert secret not in result.text
    assert config.REDACTED_TOKEN in result.text
    assert "--- CI log (run 42, repo o/r): last 100 lines shown." in result.text


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
            ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed"): ok(("gh", "run", "rerun")),
        },
    )
    submitted = ci_monitor.rerun_failed(runner, run_id="42", repo="o/r")
    assert submitted.submitted is True
    assert submitted.already_running is False

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
        ("lint", "", ("env", "SKIP=agnix,shellcheck", "make", "lint-only")),
        (
            "lint-local",
            "",
            (
                "env",
                "SKIP=agnix,shellcheck,gitleaks,pyright,markdownlint,jsonlint,"
                "agent-lint,actionlint,cargo-fmt,cargo-clippy,larch-lint,"
                "check-topology-rule-paths,lint-retired-scripts",
                "make",
                "lint-only",
            ),
        ),
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


def test_lint_local_replay_uses_ci_skip_contract() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yaml").read_text(encoding="utf-8")
    lint_local = workflow.split("\n  lint-local:", 1)[1].split("\n  shellcheck:", 1)[0]
    skip = lint_local.split("SKIP: ", 1)[1].split("\n", 1)[0]

    assert ci_monitor.per_job_command(name="lint-local", shard="") == (
        "env",
        f"SKIP={skip}",
        "make",
        "lint-only",
    )


def test_verify_job_locally_rc() -> None:
    runner = RecordingRunner(
        {
            ("make", "py-typecheck"): ok(("make", "py-typecheck")),
        },
    )
    assert ci_monitor.verify_job_locally(runner=runner, name="python-pyright", shard="", cwd="/tmp") is True


def _python_toolchain_stubs(name: str = "python-pyright") -> dict[tuple[str, ...], CommandResult]:
    req_dev = str(REPO_ROOT / "python" / "requirements-dev.txt")
    tools_by_name = {
        "python-pyright": ("pyright",),
    }
    responses: dict[tuple[str, ...], CommandResult] = {
        ("python3", "-m", "pip", "install", "-q", "-r", req_dev): ok(("python3", "-m", "pip", "install")),
    }
    for tool in tools_by_name[name]:
        responses[("command", "-v", tool)] = ok(("command", "-v", tool))
    return responses


@pytest.mark.parametrize(
    ("name", "expected_tools"),
    [
        ("python-pyright", ("pyright",)),
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
        ("git", "diff", "--name-only"): ok(("git", "diff")),
        ("git", "ls-files", "--others", "--exclude-standard"): ok(("git", "ls-files")),
        ("git", "diff", "--name-only", "--cached"): ok(("git", "diff")),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), f"{head}\n"),
        ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "0\n"),
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
    responses[("git", "add", "--", "fixed.py")] = ok(("git", "add"))
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = ok((commit_script,))
    responses[("git", "symbolic-ref", "--short", "HEAD")] = ok(("git", "symbolic-ref"), "feature\n")
    responses[("git", "push", "origin", "feature")] = ok(("git", "push"))
    responses[("make", "py-typecheck")] = ok(("make", "py-typecheck"))

    runner = RecordingRunner(responses)
    # baseline captured before vendor runs (empty); vendor adds fixed.py; delta sees it
    runner.sequential[("git", "diff", "--name-only")] = [
        ok(("git", "diff")),           # _capture_baseline tracked
        ok(("git", "diff"), "fixed.py\n"), # _delta_paths tracked_now
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{new_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{new_head}\n"),
    ]

    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
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


def test_stage_and_push_defer_rebase_uses_verified_rust_entrypoint(tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (codex)"): ok((commit_script,)),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "1\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        _RUST_REBASE: ok(_RUST_REBASE),
        ("make", "py-typecheck"): ok(("make", "py-typecheck")),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): ok(("git", "ls-remote"), "remote\trefs/heads/feature\n"),
        ("git", "fetch", "origin", "feature", "--quiet"): ok(("git", "fetch")),
        ("git", "status", "--porcelain", "--untracked-files=all"): ok(("git", "status")),
        (
            "git",
            "push",
            "--force-with-lease=refs/heads/feature:remote",
            "origin",
            "HEAD:refs/heads/feature",
        ): ok(("git", "push")),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
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
    assert _RUST_REBASE in runner.calls
    assert not any(call[:2] == ("git", "rebase") for call in runner.calls)


def test_stage_and_push_defer_rebase_preserves_rust_conflict_for_retry(tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (codex)"): ok((commit_script,)),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "1\n"),
        _RUST_REBASE: _cr(_RUST_REBASE, rc=1, stdout="CONFLICT_FILES=fixed.py\n"),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
    )
    runner = RecordingRunner(responses)

    pushed, _head, _delta, did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="codex",
        delta_paths=("fixed.py",),
        context=ci_monitor.StagePushContext(classified=classified),
    )

    assert pushed is False
    assert did_rebase is False
    assert pending is True
    assert _RUST_REBASE in runner.calls
    assert _RUST_REBASE_ABORT not in runner.calls


def test_stage_and_push_defer_rebase_aborts_rust_failure(tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (codex)"): ok((commit_script,)),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "1\n"),
        _RUST_REBASE: _cr(_RUST_REBASE, rc=3, stdout="REBASE_ERROR=git fetch origin main failed (network/auth issue)\n"),
        _RUST_REBASE_ABORT: ok(_RUST_REBASE_ABORT),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
    )
    runner = RecordingRunner(responses)

    pushed, _head, _delta, did_rebase, pending = ci_monitor.stage_and_push(
        runner,
        cwd=str(tmp_path),
        commit_label="codex",
        delta_paths=("fixed.py",),
        context=ci_monitor.StagePushContext(classified=classified),
    )

    assert pushed is False
    assert did_rebase is False
    assert pending is False
    assert _RUST_REBASE in runner.calls
    assert _RUST_REBASE_ABORT in runner.calls
    assert not any(call[:2] == ("git", "rebase") for call in runner.calls)


def test_stage_and_push_warning_refreshes_before_normal_push(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): ok((commit_script,)),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "0\n"),
    }
    order: list[str] = []

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_log_manifest.RefreshSkip:
        order.append("flush")
        return ci_monitor.run_log_manifest.RefreshSkip(skipped=False, reason="")

    def fake_push(*_args: object, **_kwargs: object) -> CommandResult:
        order.append("push")
        return ok(("git", "push"))

    def callback() -> bool:
        order.append("callback")
        return True

    monkeypatch.setattr(ci_monitor.run_log_flush, "refresh_logs_checkpoint", fake_flush)
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


def test_stage_and_push_warning_refresh_skip_blocks_push(monkeypatch: pytest.MonkeyPatch, tmp_path: Any) -> None:
    commit_script = "cli.py git commit"
    responses = {
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): ok((commit_script,)),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "0\n"),
    }
    order: list[str] = []

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_log_manifest.RefreshSkip:
        order.append("flush")
        return ci_monitor.run_log_manifest.RefreshSkip(skipped=True, reason=ci_monitor.config.REFRESH_SKIP_VOLATILE_ONLY)

    def fake_push(*_args: object, **_kwargs: object) -> CommandResult:
        order.append("push")
        return ok(("git", "push"))

    def callback() -> bool:
        order.append("callback")
        return True

    monkeypatch.setattr(ci_monitor.run_log_flush, "refresh_logs_checkpoint", fake_flush)
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


def test_stage_and_push_warning_refresh_no_logs_commit_allows_push(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Any
) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): ok(("git", "ls-remote"), "abc123\trefs/heads/feature\n"),
    }
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
    )

    def fake_flush(*_args: object, **_kwargs: object) -> ci_monitor.run_log_manifest.RefreshSkip:
        return ci_monitor.run_log_manifest.RefreshSkip(skipped=True, reason=ci_monitor.config.REFRESH_SKIP_NO_LOGS_COMMIT)

    def fake_force_push_recovery(*_args: object, **_kwargs: object) -> ci_monitor.git.ForcePushResult:
        return ci_monitor.git.ForcePushResult(pushed=True, status="ok")

    def fake_verify_job_locally(*_args: object, **_kwargs: object) -> bool:
        return True

    monkeypatch.setattr(ci_monitor.run_log_flush, "refresh_logs_checkpoint", fake_flush)
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
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
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
    assert not any("force-with-lease" in " ".join(call) for call in runner.calls)


def test_pending_retry_verifies_pyright_before_force_push(tmp_path: Any) -> None:
    responses = {
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
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
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("git", "fetch", "origin", "feature", "--quiet"): ok(("git", "fetch")),
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
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("make", "py-typecheck"): ok(("make", "py-typecheck")),
        ("git", "ls-remote", "--exit-code", "--heads", "origin", "feature"): ok(("git", "ls-remote"), "remoteoid\trefs/heads/feature\n"),
        ("git", "fetch", "origin", "feature", "--quiet"): ok(("git", "fetch")),
        ("git", "status", "--porcelain", "--untracked-files=all"): ok(("git", "status")),
        ("git", "push", "--force-with-lease=refs/heads/feature:remoteoid", "origin", "HEAD:refs/heads/feature"): ok(("git", "push")),
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
                (FailedJob(name="python-pyright", conclusion="failure"),),
            ),
        ),
    )
    assert pushed is True
    assert pending is False
    assert ("git", "push", "--force-with-lease=refs/heads/feature:remoteoid", "origin", "HEAD:refs/heads/feature") in runner.calls


def test_evaluate_failure_pending_reload_failed_jobs_before_force_push(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Any,
) -> None:
    monkeypatch.setattr(config, "CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS", 1)
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    responses = {
        ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): ok(("gh", "run", "view"), "FAIL\n"),
        ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
        ("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs"): ok(("gh", "run", "view"), jobs_json),
        ("git", "rev-parse", "HEAD"): ok(("git", "rev-parse"), "head\n"),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feature\n"),
        ("make", "py-typecheck"): _cr(("make", "py-typecheck"), rc=1),
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
    assert ("make", "py-typecheck") in runner.calls
    assert not any("force-with-lease" in " ".join(call) for call in runner.calls)


def test_run_ci_fix_pending_retry_defers_guidelines_to_compose_gate(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ctx = make_run_context(tmpdir=str(tmp_path), run_id="run-abc")
    calls: list[object] = []

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
    responses[("git", "add", "--", "fixed.py")] = ok(("git", "add"))
    responses[("make", "py-typecheck")] = ok(("make", "py-typecheck"))
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = ok((commit_script,))
    responses[("git", "symbolic-ref", "--short", "HEAD")] = ok(("git", "symbolic-ref"), "feature\n")
    responses[("git", "push", "origin", "feature")] = ok(("git", "push"))

    runner = RecordingRunner(responses)
    # empty baseline, vendor adds fixed.py; HEAD stays same after push → first-fixer-non-health
    runner.sequential[("git", "diff", "--name-only")] = [
        ok(("git", "diff")),           # _capture_baseline tracked
        ok(("git", "diff"), "fixed.py\n"), # _delta_paths tracked_now
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{head}\n"),
    ]
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
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
    responses[("make", "py-typecheck")] = _cr(("make", "py-typecheck"), 1)
    runner = RecordingRunner(responses)
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
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
    runner = RecordingRunner({})
    fix = ci_monitor.evaluate_failure(
        runner,
        run_id="42",
        repo="o/r",
        plan_file=None,
        transient_retries=0,
        _fix_attempts=0,
        cwd=None,
    )
    assert fix.status == config.NEEDS_USER_FIRST_FIXER_NON_HEALTH
    assert ("gh", "run", "rerun", "42", "--repo", "o/r", "--failed") not in runner.calls


def test_evaluate_failure_in_progress_defers_launch() -> None:
    launch_count = 0

    def launch_fn(_tier: str) -> TierAttempt:
        nonlocal launch_count
        launch_count += 1
        return TierAttempt("cursor", 0, 0, LaunchFailure("none", ""))

    runner = RecordingRunner({})
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
    assert not sleeps
    assert fix.status == config.NEEDS_USER_FIRST_FIXER_NON_HEALTH


def test_wait_for_ci_ready_polls_until_ready() -> None:
    """_wait_for_ci_ready polls every 15s and returns once the run exits in_progress."""
    in_progress = _cr(
        ("gh", "run", "view"),
        rc=3,
        stderr="is still in progress; logs will be available",
    )
    ready_log = ok(("gh", "run", "view"), "FAIL AssertionError\n")
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
            ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): ok(("gh", "run", "view"), "FAIL AssertionError: expected True\n"),
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
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
    responses[("make", "py-typecheck")] = _cr(("make", "py-typecheck"), rc=1)
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
    assert "python-pyright" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_per_job_exhausted_routes_needs_user_input() -> None:
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
    responses[("make", "py-typecheck")] = _cr(("make", "py-typecheck"), rc=1)
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
    assert ("make", "py-typecheck") in runner.calls
    assert fix.status == "fix-exhausted"
    assert fix.detail is not None
    assert fix.detail.startswith("ci-fix-exhausted")
    assert "python-pyright" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_upfront_ready_stash_when_transient_cap_exhausted() -> None:
    jobs_json = json.dumps({"jobs": []})
    log_responses = [
        ok(("gh", "run", "view"), "FAIL test\n"),
        ok(("gh", "run", "view"), "FAIL test\n"),
        ok(("gh", "run", "view"), "FAIL test\n"),
    ]
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
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
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
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
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
    responses[("git", "add", "--", "fixed.py")] = ok(("git", "add"))
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = ok((commit_script,))
    responses[("git", "symbolic-ref", "--short", "HEAD")] = ok(("git", "symbolic-ref"), "feature\n")
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), rc=1)

    runner = RecordingRunner(responses)
    runner.sequential[("git", "diff", "--name-only")] = [
        ok(("git", "diff")),
        ok(("git", "diff"), "fixed.py\n"),
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
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
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    responses = _baseline_responses(baseline_head)
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
    responses[("make", "py-typecheck")] = ok(("make", "py-typecheck"))
    responses[("git", "add", "--", "fixed.py")] = ok(("git", "add"))
    commit_script = "cli.py git commit"
    responses[(commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)")] = ok((commit_script,))
    responses[("git", "symbolic-ref", "--short", "HEAD")] = ok(("git", "symbolic-ref"), "feature\n")
    responses[("git", "push", "origin", "feature")] = _cr(("git", "push"), rc=1)

    runner = RecordingRunner(responses)
    runner.sequential[("git", "diff", "--name-only")] = [
        ok(("git", "diff")),
        ok(("git", "diff"), "fixed.py\n"),
    ]
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
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
    assert "python-pyright" in fix.detail
    assert "FAIL test" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_exhausted_surfaces_job_and_log_tail() -> None:
    """fix-exhausted detail carries the failing job name and redacted log tail."""
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})
    log_tail = "ruff check failed on foo.py:42\nE501 line too long in bar.py\n"
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), log_tail)
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
    responses[("make", "py-typecheck")] = _cr(("make", "py-typecheck"), rc=1)

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
    assert "python-pyright" in fix.detail
    # Redacted CI log tail (with its run pointer) is surfaced, not just the token.
    assert "ruff check failed on foo.py:42" in fix.detail
    assert "E501 line too long in bar.py" in fix.detail
    assert "CI log (run 42" in fix.detail
    assert "\n" in fix.detail


@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")
def test_evaluate_failure_launcher_exhausted_stalls() -> None:
    jobs_json = json.dumps({"jobs": []})
    responses = _baseline_responses()
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")] = ok(("gh", "run", "view"), "FAIL test\n")
    responses[("gh", "run", "view", "42", "--repo", "o/r", "--json", "jobs")] = ok(("gh", "run", "view"), jobs_json)
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
            ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
            ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed"): ok(("gh", "run", "view"), "FAIL test\n"),
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
            ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
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


def test_redact_in_collect_failed_logs_unit() -> None:
    sample = "token ghp_" + "x" * 40
    redacted = redact.redact(sample)
    assert config.REDACTED_TOKEN in redacted


# FINDING_14: poll_ci NO_CHECKS bail


# FINDING_15: run_ci_fix head-changed
def test_run_ci_fix_non_pending_head_changed_fails_closed() -> None:
    """Non-pending callers fail closed before legacy head-change handling."""
    baseline_head = "aaaa" * 10
    new_head = "bbbb" * 10

    def launch_fn(tier: str) -> TierAttempt:
        return TierAttempt(tier=tier, wrapper_rc=0, launcher_exit=0, failure=LaunchFailure("none", ""))

    responses = _baseline_responses()
    responses[("make", "py-typecheck")] = ok(("make", "py-typecheck"))
    runner = RecordingRunner(responses)
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{new_head}\n"),
    ]
    classified = ci_monitor.classify_failed_jobs(
        (FailedJob(name="python-pyright", conclusion="failure"),),
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
        (FailedJob(name="python-pyright", conclusion="failure"),),
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
    jobs_json = json.dumps({"jobs": [{"name": "python-pyright", "conclusion": "failure"}]})

    commit_script = "cli.py git commit"
    responses: dict[tuple[str, ...], CommandResult] = {
        ("git", "symbolic-ref", "--quiet", "HEAD"): ok(("git", "symbolic-ref")),
        ("gh", "run", "view", "77", "--repo", "o/r", "--log-failed"): ok(("gh", "run", "view"), "log"),
        ("gh", "run", "view", "77", "--repo", "o/r", "--json", "jobs"): ok(("gh", "run", "view"), jobs_json),
        ("git", "ls-files", "--others", "--exclude-standard"): ok(("git", "ls-files")),
        ("git", "diff", "--name-only", "--cached"): ok(("git", "diff")),
        ("git", "add", "--", "fixed.py"): ok(("git", "add")),
        ("git", "symbolic-ref", "--short", "HEAD"): ok(("git", "symbolic-ref"), "feat\n"),
        ("git", "fetch", "origin", "main", "--quiet"): ok(("git", "fetch")),
        ("git", "rev-list", "--count", "HEAD..origin/main"): ok(("git", "rev-list"), "0\n"),
        ("git", "push", "origin", "feat"): ok(("git", "push")),
        # both attempts use codex (always first tier, #3994)
        (commit_script, "--no-trailer", "-m", "Apply CI fixes (claude)"): ok((commit_script,)),
    }
    responses.update(_python_toolchain_stubs())

    runner = RecordingRunner(responses)
    # git diff --name-only: a1 baseline, a1 rollback-tracked, a2 baseline, a2 delta
    runner.sequential[("git", "diff", "--name-only")] = [
        ok(("git", "diff")),
        ok(("git", "diff")),
        ok(("git", "diff")),
        ok(("git", "diff"), "fixed.py\n"),
    ]
    # git rev-parse HEAD: a1 baseline, a1 head-check, a2 baseline, a2 head-check, a2 post-commit, a2 post-push
    runner.sequential[("git", "rev-parse", "HEAD")] = [
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{baseline_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{new_head}\n"),
        ok(("git", "rev-parse", "HEAD"), f"{new_head}\n"),
    ]
    # make py-typecheck: fail on attempt 1, pass on attempt 2
    runner.sequential[("make", "py-typecheck")] = [
        _cr(("make", "py-typecheck"), rc=1),
        ok(("make", "py-typecheck")),
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
        ): ok(("gh", "pr", "checks"), json.dumps([{"name": "ci", "bucket": "pass"}])),
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
        ("gh", "pr", "checks", "1", "--repo", "o/r", "--required"): ok(("gh", "pr", "checks"), "all required checks passed"),
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


def test_evaluate_failure_pending_push_only_skips_agentic_delegate(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_run_ci_fix(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        return ci_monitor.FixResult(status="pushed", winning_tier="claude")

    def fake_collect_failed_logs(*_args: object, **_kwargs: object) -> ci_monitor.LogCollectResult:
        return ci_monitor.LogCollectResult(text="", state="ready")

    def fake_read_failed_jobs(*_args: object, **_kwargs: object) -> tuple[list[FailedJob], str]:
        return [], "ready"

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
    assert fix.status == "pushed"


def test_evaluate_failure_normal_path_hands_off_without_logs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"collect": 0, "run_ci_fix": 0}

    def fake_run_ci_fix(*_args: object, **_kwargs: object) -> ci_monitor.FixResult:
        calls["run_ci_fix"] += 1
        return ci_monitor.FixResult(status="waterfall-failed", detail="should-not-run")

    def fake_collect_failed_logs(
        *_args: object,
        **_kwargs: object,
    ) -> ci_monitor.LogCollectResult:
        calls["collect"] += 1
        return ci_monitor.LogCollectResult(text="", state="ready")

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
    )
    assert calls == {"collect": 0, "run_ci_fix": 0}
    assert fix.status == config.NEEDS_USER_FIRST_FIXER_NON_HEALTH
    assert fix.detail == "first-fixer-non-health"


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


def test_verify_job_locally_uses_run_aware_breadcrumb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_job_locally writes a breadcrumb only when resolve_owned_run_id returns a run ID."""
    monkeypatch.setenv("LARCH_RUN_ID", "test-impl-run-7")
    breadcrumb_calls: list[tuple[str, str, str, str]] = []

    def fake_append(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        skill: str,
        step: str,
        text: str,
        cwd: str | None = None,
    ) -> bool:
        _ = repo_root, cwd
        breadcrumb_calls.append((run_id, skill, step, text))
        return True

    def fake_per_job(*, name: str, shard: str) -> tuple[str, ...] | None:  # noqa: ARG001  # pylint: disable=unused-argument
        return ("true",)

    monkeypatch.setattr(ci_monitor.run_log_flush, "progress_note", fake_append)
    monkeypatch.setattr(ci_monitor, "per_job_command", fake_per_job)

    fake_runner = RecordingRunner(
        responses={("true",): ok(("true",))},
    )
    result = ci_monitor.verify_job_locally(
        runner=fake_runner, name="py-test", shard="1", cwd=str(tmp_path)
    )

    assert result is True
    assert len(breadcrumb_calls) == 1
    run_id, skill, step, text = breadcrumb_calls[0]
    assert run_id == "test-impl-run-7"
    assert skill == "implement"
    assert step == "8"
    assert "py-test-1" in text


def test_verify_job_locally_skips_breadcrumb_without_run_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """verify_job_locally writes no breadcrumb when no run ID is resolvable."""
    monkeypatch.delenv("LARCH_RUN_ID", raising=False)
    breadcrumb_calls: list[object] = []

    def fake_append_no_run(
        _runner: object,
        *,
        repo_root: str,
        run_id: str,
        skill: str,
        step: str,
        text: str,
        cwd: str | None = None,
    ) -> bool:
        _ = repo_root, cwd
        breadcrumb_calls.append((run_id, skill, step, text))
        return True

    def fake_per_job_cmd(*, name: str, shard: str) -> tuple[str, ...] | None:  # noqa: ARG001  # pylint: disable=unused-argument
        return ("true",)

    monkeypatch.setattr(ci_monitor.run_log_flush, "progress_note", fake_append_no_run)
    monkeypatch.setattr(ci_monitor, "per_job_command", fake_per_job_cmd)

    fake_runner = RecordingRunner(
        responses={("true",): ok(("true",))},
    )
    _ = ci_monitor.verify_job_locally(
        runner=fake_runner, name="py-test", shard="1", cwd=str(tmp_path)
    )

    assert len(breadcrumb_calls) == 0


def test_prepare_failure_evidence_distinguishes_ready_and_error() -> None:
    runner = RecordingRunner({})
    key = ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")
    runner.sequential[key] = [
        ok(key, "failure body\n"),
        CommandResult(key, 1, "", "gh auth failed", 0.01),
    ]
    ready = ci_monitor.prepare_failure_evidence(runner, run_id="42", repo="o/r")
    error = ci_monitor.prepare_failure_evidence(runner, run_id="42", repo="o/r")
    assert ready.state == "ready"
    assert error.state == "error"


def test_resolve_failed_run_id_once_requires_failed_snapshot() -> None:
    runner = RecordingRunner({})
    key = ("gh", "pr", "checks", "7", "--repo", "o/r", "--json", "name,state,bucket,link")
    runner.sequential[key] = [
        ok(key, '[{"name":"CI","bucket":"pending","link":"https://github.com/o/r/actions/runs/41"}]'),
        ok(key, '[{"name":"CI","bucket":"fail","link":"https://github.com/o/r/actions/runs/42"}]'),
    ]
    assert ci_monitor.resolve_failed_run_id_once(runner, pr=7, repo="o/r") is None
    assert ci_monitor.resolve_failed_run_id_once(runner, pr=7, repo="o/r") == "42"


def test_prepare_failure_evidence_waits_for_in_progress_result() -> None:
    runner = RecordingRunner({})
    key = ("gh", "run", "view", "42", "--repo", "o/r", "--log-failed")
    runner.sequential[key] = [
        CommandResult(key, 1, "", "run is still in progress; logs will be available", 0.01),
        ok(key, "failure body\n"),
    ]
    now = [0.0]

    def sleep_fn(seconds: float) -> None:
        now[0] += seconds

    result = ci_monitor.prepare_failure_evidence(
        runner, run_id="42", repo="o/r", sleep_fn=sleep_fn, clock=lambda: now[0]
    )
    assert result.state == "ready"
    assert result.text.endswith("failure body\n")
