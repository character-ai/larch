"""Tests for default-branch CI health classification."""

from __future__ import annotations

from larch.core.proc import CommandResult
from larch.implement import main_health
from test_support import RecordingRunner


def _query(
    head_sha: str | None = None,
    *,
    repo: str = "o/r",
    upstream_repo: str | None = None,
) -> main_health.MainHealthQuery:
    return main_health.MainHealthQuery(
        repo=repo,
        upstream_repo=upstream_repo,
        base_branch="main",
        workflow="CI",
        limit=20,
        head_sha=head_sha,
    )


def _res(stdout: str, rc: int = 0) -> CommandResult:
    return CommandResult(("gh", "run", "list"), rc, stdout, "", 0.01)


def test_latest_matching_success_returns_pass() -> None:
    runner = RecordingRunner(
        responses=[
            _res('[{"databaseId":1,"status":"completed","conclusion":"success","headSha":"abc","event":"push"}]'),
        ],
    )

    result = main_health.read_main_health(runner, _query("abc"))

    assert result.status == "pass"
    assert result.head_sha == "abc"


def test_success_without_head_sha_returns_error() -> None:
    runner = RecordingRunner(
        responses=[
            _res('[{"databaseId":10,"status":"completed","conclusion":"success","headSha":"","event":"push"}]'),
        ],
    )

    result = main_health.read_main_health(runner, _query())

    assert result.status == "error"
    assert "without a head SHA" in result.detail


def test_latest_matching_failure_returns_fail_and_failed_run_id() -> None:
    runner = RecordingRunner(
        responses=[
            _res('[{"databaseId":2,"status":"completed","conclusion":"failure","headSha":"abc","event":"push"}]'),
        ],
    )

    result = main_health.read_main_health(runner, _query("abc"))

    assert result.status == "fail"
    assert result.failed_run_id == "2"


def test_matching_in_progress_returns_pending() -> None:
    runner = RecordingRunner(
        responses=[
            _res('[{"databaseId":3,"status":"in_progress","conclusion":null,"headSha":"abc","event":"push"}]'),
        ],
    )

    result = main_health.read_main_health(runner, _query("abc"))

    assert result.status == "pending"


def test_no_rows_no_sha_match_and_malformed_json_return_error() -> None:
    no_rows = RecordingRunner(responses=[_res("[]")])
    assert (
        main_health.read_main_health(no_rows, _query()).status
        == "error"
    )
    no_match = RecordingRunner(
        responses=[
            _res('[{"databaseId":4,"status":"completed","conclusion":"success","headSha":"old","event":"push"}]'),
        ],
    )
    assert (
        main_health.read_main_health(no_match, _query("abc")).status
        == "error"
    )
    malformed = RecordingRunner(responses=[_res("{")])
    assert (
        main_health.read_main_health(malformed, _query()).status
        == "error"
    )


def test_filtered_argv_uses_repo_bare_branch_event_workflow_limit_and_commit() -> None:
    runner = RecordingRunner(responses=[_res("[]")])

    _ = main_health.read_main_health(
        runner,
        main_health.MainHealthQuery(
            repo="o/r",
            base_branch="main",
            workflow="CI",
            limit=17,
            head_sha="abc",
        ),
    )

    call = runner.calls[0]
    assert call[0:5] == ["gh", "run", "list", "--repo", "o/r"]
    assert "--branch" in call
    assert call[call.index("--branch") + 1] == "main"
    assert call[call.index("--event") + 1] == "push"
    assert call[call.index("--workflow") + 1] == "CI"
    assert call[call.index("--limit") + 1] == "17"
    assert call[call.index("--commit") + 1] == "abc"


def test_forked_upstream_repo_uses_bare_main_branch() -> None:
    runner = RecordingRunner(responses=[_res("[]")])

    _ = main_health.read_main_health(runner, _query(repo="fork/r", upstream_repo="upstream/r"))

    call = runner.calls[0]
    assert call[call.index("--repo") + 1] == "upstream/r"
    assert call[call.index("--branch") + 1] == "main"
    assert "upstream/main" not in call


def test_wait_ignores_stale_green_for_specific_sha_until_timeout() -> None:
    runner = RecordingRunner(
        responses=[
            _res('[{"databaseId":5,"status":"completed","conclusion":"success","headSha":"old","event":"push"}]'),
            _res('[{"databaseId":5,"status":"completed","conclusion":"success","headSha":"old","event":"push"}]'),
        ],
    )
    now = [0.0]

    def clock() -> float:
        now[0] += 1.0
        return now[0]

    waited = main_health.wait_main_health(
        runner,
        main_health.MainHealthWaitQuery(health=_query("abc"), timeout=1, interval=0),
        clock=clock,
        sleep=lambda _seconds: None,
    )

    assert waited.health.status == "pending"
    assert waited.health.head_sha == "abc"


def test_same_sha_repository_failure_followed_by_success_returns_fail() -> None:
    runner = RecordingRunner(
        responses=[
            _res(
                "["
                '{"databaseId":9,"status":"completed","conclusion":"success","headSha":"abc","event":"push"},'
                '{"databaseId":8,"status":"completed","conclusion":"failure","headSha":"abc","event":"push"}'
                "]",
            ),
            CommandResult(("gh", "run", "view", "8"), 0, '{"jobs":[{"name":"pytest","conclusion":"failure"}]}', "", 0.01),
        ],
    )

    result = main_health.read_main_health(runner, _query("abc"))

    assert result.status == "fail"
    assert result.failed_run_id == "8"
