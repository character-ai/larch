"""Unit tests for gh.py using a stub Runner."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from larch.core import config
from larch.git import gh
from larch.errors import ShipError, TransientNetworkError
from larch.core.proc import CommandResult

from test_support import RecordingRunner as _RecordingRunner


@dataclass
class RecordingRunner(_RecordingRunner):
    strict: bool = True


def test_pr_view_parses_json() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"b"}',
                "",
                0.01,
            ),
        ],
    )
    pr = gh.pr_view(runner, 1, repo="o/r")
    assert pr.number == 1
    assert pr.head_ref == "b"


def test_pr_view_timeout_raises_gh_read_timeout() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), config.EXIT_TIMEOUT, "", "", 120.0),
        ],
    )
    with pytest.raises(gh.GhReadTimeout):
        _ = gh.pr_view(runner, 1, repo="o/r", timeout=120.0)


def test_pr_view_exit_timeout_without_timeout_arg_raises_plain_ship_error() -> None:
    # Without a threaded timeout, an EXIT_TIMEOUT return is a generic read failure,
    # not the distinguishable GhReadTimeout that the CI monitor routes on.
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), config.EXIT_TIMEOUT, "", "", 0.01),
        ],
    )
    with pytest.raises(ShipError) as exc_info:
        _ = gh.pr_view(runner, 1, repo="o/r")
    assert not isinstance(exc_info.value, gh.GhReadTimeout)


def test_pr_create_deduplicates_existing() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":9,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    pr, _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
    )
    assert pr.number == 9
    assert len(runner.calls) == 1
    assert "--state" in runner.calls[0]
    assert "open" in runner.calls[0]


def test_pr_create_recovers_after_create_conflict() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "list"),
                0,
                "[]",
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "create"),
                1,
                "",
                "pull request for branch feat already exists",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":42,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    pr, _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
    )
    assert pr.number == 42
    assert len(runner.calls) == 3
    assert runner.calls[1][runner.calls[1].index("--body-file") + 1].endswith(".md")


def test_pr_create_recovers_from_conflict_stderr_url_when_list_empty() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                1,
                "",
                (
                    'a pull request for branch "feat" into branch "main" already exists:\n'
                    "https://github.com/o/r/pull/789\n"
                ),
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                1,
                "",
                "no such hosted repository",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "789"),
                0,
                '{"number":789,"url":"https://github.com/o/r/pull/789","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
    )
    assert pr.number == 789
    assert pr.url == "https://github.com/o/r/pull/789"
    assert pr.head_ref == "feat"
    assert len(runner.calls) == 4


def test_pr_create_uses_body_file_not_inline_body() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/1\n",
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="secret-body",
    )
    create_argv = runner.calls[1]
    assert "--body-file" in create_argv
    assert "--json" not in create_argv
    assert "secret-body" not in create_argv
    body_path = create_argv[create_argv.index("--body-file") + 1]
    assert Path(body_path).is_file() is False


def test_pr_create_resolves_success_from_post_create_list() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/123\n",
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":123,"url":"https://github.com/o/r/pull/123","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 123
    assert "--json" not in runner.calls[1]


def test_pr_create_resolves_success_from_stdout_url_when_list_lags() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/456\n",
                "",
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "456"),
                0,
                '{"number":456,"url":"https://github.com/o/r/pull/456","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 456
    assert pr.url == "https://github.com/o/r/pull/456"
    assert pr.head_ref == "feat"


def test_pr_create_prefers_stdout_url_over_stderr_when_both_present() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/100\n",
                "https://github.com/o/r/pull/999\n",
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "100"),
                0,
                '{"number":100,"url":"https://github.com/o/r/pull/100","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 100
    assert pr.url == "https://github.com/o/r/pull/100"


def test_pr_create_tries_stderr_url_after_invalid_stdout_url() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/100\n",
                "https://github.com/o/r/pull/999\n",
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "100"),
                0,
                '{"number":100,"url":"https://github.com/o/r/pull/100","state":"OPEN","headRefName":"other"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "view", "999"),
                0,
                '{"number":999,"url":"https://github.com/o/r/pull/999","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 999
    assert pr.url == "https://github.com/o/r/pull/999"


def test_pr_create_resolves_success_from_stderr_url_when_list_lags() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "",
                "warning: created\nhttps://github.com/o/r/pull/654\n",
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "654"),
                0,
                '{"number":654,"url":"https://github.com/o/r/pull/654","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 654
    assert pr.url == "https://github.com/o/r/pull/654"


def test_pr_create_success_without_url_does_not_use_current_branch_pr_view() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, "Created pull request\n", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="could not be resolved"):
        _ = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert len(runner.calls) == 3


def test_pr_create_recovers_url_when_pr_view_temporarily_missing() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.example.test/Owner/Repo/pull/456\n",
                "",
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "view", "456"), 1, "", "not found", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="could not be resolved"):
        _ = gh.pr_create(runner, repo="owner/repo", branch="feat", title="t", body="b")


def test_pr_create_recovers_conflict_url_when_list_and_view_fail() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                1,
                "",
                (
                    'a pull request for branch "feat" into branch "main" already exists:\n'
                    "https://github.com/o/r/pull/321\n"
                ),
                0.01,
            ),
            CommandResult(("gh", "pr", "list"), 1, "", "list failed", 0.01),
            CommandResult(("gh", "pr", "view", "321"), 1, "", "view failed", 0.01),
        ],
    )
    pr, created = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
    )
    assert created is False
    assert pr.number == 321
    assert pr.url == "https://github.com/o/r/pull/321"
    assert pr.head_ref == "feat"


def test_pr_create_propagates_transient_post_create_resolution() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/456\n",
                "",
                0.01,
            ),
            *[
                CommandResult(
                    ("gh", "pr", "list"),
                    1,
                    "",
                    "api.github.com: connection reset by peer",
                    0.01,
                )
                for _ in range(config.TRANSIENT_RETRY_MAX_ATTEMPTS)
            ],
        ],
    )
    with pytest.raises(TransientNetworkError):
        _ = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")


def test_pr_create_success_without_resolvable_pr_raises_ship_error() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "view"), 1, "", "no pull requests found", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="could not be resolved"):
        _ = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")


def test_pr_create_recorded_gh_transcript_no_json_flag() -> None:
    transcript_stdout = (Path(__file__).parent / "fixtures" / "gh-pr-create-success.txt").read_text(
        encoding="utf-8",
    )
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, transcript_stdout, "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "321"),
                0,
                '{"number":321,"url":"https://github.com/o/r/pull/321","state":"OPEN","headRefName":"feat"}',
                "",
                0.01,
            ),
        ],
    )
    pr, created = gh.pr_create(runner, repo="o/r", branch="feat", title="t", body="b")
    assert created is True
    assert pr.number == 321
    assert "--json" not in runner.calls[1]


def test_pr_merge_not_retried() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "merge", "1"), 0, "", "", 0.01),
        ],
    )
    _ = gh.pr_merge(runner, 1, repo="o/r")
    assert len(runner.calls) == 1


def test_read_helpers_parse_workflow_json() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "run", "list"),
                0,
                '[{"databaseId":11,"status":"completed","conclusion":"failure"}]',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "run", "view", "11"),
                0,
                '{"databaseId":11,"status":"completed","conclusion":"success"}',
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "run", "view", "11"),
                0,
                '{"jobs":[{"name":"lint","conclusion":"failure"},{"name":"ok","conclusion":"success"}]}',
                "",
                0.01,
            ),
        ],
    )
    runs = gh.run_list(runner, repo="o/r", branch="feat", limit=1)
    assert runs[0].database_id == 11
    assert "--limit" in runner.calls[0]
    run = gh.run_view(runner, 11, repo="o/r")
    assert run.conclusion == "success"
    failed = gh.failed_jobs(runner, 11, repo="o/r")
    assert [job.name for job in failed] == ["lint"]


def test_mutating_helpers_build_argv_without_retry() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "run", "rerun", "11"), 0, "", "", 0.01),
            CommandResult(("gh", "issue", "comment", "1"), 0, "", "", 0.01),
            CommandResult(("gh", "issue", "edit", "1"), 0, "", "", 0.01),
        ],
    )
    assert gh.run_rerun(runner, 11, repo="o/r").returncode == 0
    assert gh.issue_comment(runner, "1", "body", repo="o/r").returncode == 0
    assert gh.issue_edit(runner, "1", repo="o/r", title="t", body="b").returncode == 0
    assert runner.calls[0] == ["gh", "run", "rerun", "11", "--repo", "o/r", "--failed"]
    assert runner.calls[1][0:6] == ["gh", "issue", "comment", "1", "--repo", "o/r"]
    assert runner.calls[1][6] == "--body-file"
    assert runner.calls[2][0:6] == ["gh", "issue", "edit", "1", "--repo", "o/r"]
    assert runner.calls[2][6:8] == ["--title", "t"]
    assert runner.calls[2][8] == "--body-file"


def test_pr_view_raises_before_json_on_failure() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 1, "", "fatal", 0.01),
        ],
    )
    with pytest.raises(ShipError):
        _ = gh.pr_view(runner, 1, repo="o/r")


def test_pr_view_retries_transient_then_succeeds() -> None:
    transient = CommandResult(
        ("gh", "pr", "view", "1"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    success = CommandResult(
        ("gh", "pr", "view", "1"),
        0,
        '{"number":1,"url":"u","state":"OPEN","headRefName":"b"}',
        "",
        0.01,
    )
    runner = RecordingRunner(responses=[transient, transient, success])
    pr = gh.pr_view(runner, 1, repo="o/r")
    assert pr.number == 1
    assert len(runner.calls) == 3


def test_pr_view_exhausts_transient_retries() -> None:
    transient = CommandResult(
        ("gh", "pr", "view", "1"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    runner = RecordingRunner(
        responses=[transient, transient, transient],
    )
    with pytest.raises(TransientNetworkError) as exc_info:
        _ = gh.pr_view(runner, 1, repo="o/r")
    assert exc_info.value.result is transient
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_pr_view_read_returns_last_result_on_exhaustion() -> None:
    transient = CommandResult(
        ("gh", "pr", "view", "1"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    runner = RecordingRunner(
        responses=[transient, transient, transient],
    )
    result = gh.pr_view_read(runner, 1, repo="o/r")
    assert result.returncode == 1
    assert "Could not resolve host" in result.stderr
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_run_list_retries_transient_then_succeeds() -> None:
    transient = CommandResult(
        ("gh", "run", "list"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    success = CommandResult(
        ("gh", "run", "list"),
        0,
        '[{"databaseId":7,"status":"completed","conclusion":"success"}]',
        "",
        0.01,
    )
    runner = RecordingRunner(responses=[transient, success])
    runs = gh.run_list(runner, repo="o/r", branch="feat", limit=1)
    assert runs[0].database_id == 7
    assert len(runner.calls) == 2


def test_run_list_exhausts_transient_retries() -> None:
    transient = CommandResult(
        ("gh", "run", "list"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    runner = RecordingRunner(
        responses=[transient, transient, transient],
    )
    with pytest.raises(TransientNetworkError):
        _ = gh.run_list(runner, repo="o/r", branch="feat", limit=1)
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_run_view_retries_transient_then_succeeds() -> None:
    transient = CommandResult(
        ("gh", "run", "view", "11"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    success = CommandResult(
        ("gh", "run", "view", "11"),
        0,
        '{"databaseId":11,"status":"completed","conclusion":"success"}',
        "",
        0.01,
    )
    runner = RecordingRunner(responses=[transient, success])
    run = gh.run_view(runner, 11, repo="o/r")
    assert run.database_id == 11
    assert len(runner.calls) == 2


def test_run_view_exhausts_transient_retries() -> None:
    transient = CommandResult(
        ("gh", "run", "view", "11"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    runner = RecordingRunner(
        responses=[transient, transient, transient],
    )
    with pytest.raises(TransientNetworkError):
        _ = gh.run_view(runner, 11, repo="o/r")
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_failed_jobs_retries_transient_then_succeeds() -> None:
    transient = CommandResult(
        ("gh", "run", "view", "11"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    success = CommandResult(
        ("gh", "run", "view", "11"),
        0,
        '{"jobs":[{"name":"lint","conclusion":"failure"}]}',
        "",
        0.01,
    )
    runner = RecordingRunner(responses=[transient, success])
    failed = gh.failed_jobs(runner, 11, repo="o/r")
    assert [job.name for job in failed] == ["lint"]
    assert len(runner.calls) == 2


def test_failed_jobs_exhausts_transient_retries() -> None:
    transient = CommandResult(
        ("gh", "run", "view", "11"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    runner = RecordingRunner(
        responses=[transient, transient, transient],
    )
    with pytest.raises(TransientNetworkError):
        _ = gh.failed_jobs(runner, 11, repo="o/r")
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


def test_run_list_raises_on_malformed_row() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "run", "list"),
                0,
                '["not-a-dict"]',
                "",
                0.01,
            ),
        ],
    )
    with pytest.raises(ShipError, match="run list row"):
        _ = gh.run_list(runner, repo="o/r", branch="feat", limit=1)


def test_pr_create_passes_base_and_assignee() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/1\n",
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
        base="main",
        assignee="@me",
    )
    create_argv = runner.calls[1]
    assert "--base" in create_argv
    assert "main" in create_argv
    assert "--assignee" in create_argv
    assert "@me" in create_argv


def test_pr_create_redacts_title() -> None:
    token = "ghp_" + "a" * 36
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                "https://github.com/o/r/pull/1\n",
                "",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    _ = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title=f"PR {token}",
        body="b",
    )
    title_idx = runner.calls[1].index("--title") + 1
    assert token not in runner.calls[1][title_idx]


def test_pr_merge_not_retried_on_transient() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "merge", "1"),
                1,
                "",
                "fatal: Could not resolve host",
                0.01,
            ),
        ],
    )
    result = gh.pr_merge(runner, 1, repo="o/r")
    assert result.returncode == 1
    assert len(runner.calls) == 1


def test_pr_for_branch_returns_none_when_empty() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
        ],
    )
    assert gh.pr_for_branch(runner, "feat", repo="o/r") is None


def test_pr_for_branch_parses_open_pr() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":3,"url":"u","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    pr = gh.pr_for_branch(runner, "feat", repo="o/r")
    assert pr is not None
    assert pr.number == 3


def test_pr_for_branch_retries_transient_then_succeeds() -> None:
    transient = CommandResult(
        ("gh", "pr", "list"),
        1,
        "",
        "fatal: Could not resolve host",
        0.01,
    )
    success = CommandResult(
        ("gh", "pr", "list"),
        0,
        '[{"number":5,"url":"u","state":"OPEN","headRefName":"b"}]',
        "",
        0.01,
    )
    runner = RecordingRunner(responses=[transient, success])
    pr = gh.pr_for_branch(runner, "b", repo="o/r")
    assert pr is not None
    assert pr.number == 5
    assert len(runner.calls) == 2


def test_pr_merge_unknown_method_raises() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="unknown merge_method"):
        _ = gh.pr_merge(runner, 1, repo="o/r", merge_method="squish")


def test_pr_view_raises_ship_error_on_invalid_json() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "view", "1"), 0, "not-json", "", 0.01),
        ],
    )
    with pytest.raises(ShipError, match="JSON parse failed"):
        _ = gh.pr_view(runner, 1, repo="o/r")


def test_pr_view_raises_ship_error_on_missing_json_keys() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "1"),
                0,
                '{"number":1}',
                "",
                0.01,
            ),
        ],
    )
    with pytest.raises(ShipError, match="missing required keys"):
        _ = gh.pr_view(runner, 1, repo="o/r")


def test_pr_merge_builds_admin_argv() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "pr", "merge", "3"), 0, "", "", 0.01)],
    )
    result = gh.pr_merge(runner, 3, repo="o/r", admin=True)
    assert result.returncode == 0
    assert "--admin" in runner.calls[0]


def test_pr_merge_delete_branch_flag() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "pr", "merge", "3"), 0, "", "", 0.01)],
    )
    result = gh.pr_merge(runner, 3, repo="o/r", delete_branch=True)
    assert result.returncode == 0
    assert "--delete-branch" in runner.calls[0]


def test_pr_merge_state_read() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "pr", "view", "2"),
                0,
                '{"mergeStateStatus":"CLEAN","headRefOid":"abc"}',
                "",
                0.01,
            ),
        ],
    )
    state = gh.pr_merge_state(runner, 2, repo="o/r")
    assert state.merge_state_status == "CLEAN"
    assert state.head_ref_oid == "abc"


def test_pr_edit_body_uses_body_file() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "pr", "edit", "4"), 0, "", "", 0.01)],
    )
    result = gh.pr_edit_body(runner, 4, "hello", repo="o/r")
    assert result.returncode == 0
    assert "--body-file" in runner.calls[0]


def test_pr_edit_body_file_retries_and_threads_repo(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(config, "TRANSIENT_RETRY_BACKOFF_SEC", (0, 0))
    body_file = tmp_path / "body.md"
    _ = body_file.write_text("hello", encoding="utf-8")
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "edit", "4"), 1, "", "fatal: Could not resolve host", 0.01),
            CommandResult(("gh", "pr", "edit", "4"), 0, "", "", 0.01),
        ],
    )
    result = gh.pr_edit_body_file(runner, "4", str(body_file), repo="o/r")
    assert result.updated
    assert len(runner.calls) == 2
    assert runner.calls[0] == ["gh", "pr", "edit", "4", "--repo", "o/r", "--body-file", str(body_file)]


def test_pr_edit_body_file_omits_repo_when_absent(tmp_path: Path) -> None:
    body_file = tmp_path / "body.md"
    _ = body_file.write_text("hello", encoding="utf-8")
    runner = RecordingRunner(responses=[CommandResult(("gh", "pr", "edit", "4"), 0, "", "", 0.01)])
    result = gh.pr_edit_body_file(runner, "4", str(body_file), repo=None)
    assert result.updated
    assert runner.calls[0] == ["gh", "pr", "edit", "4", "--body-file", str(body_file)]


def test_body_file_args_fail_closed_on_truncation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_redact(_text: str) -> str:
        return "x [content truncated — safety]"

    monkeypatch.setattr(gh.redact, "redact", fake_redact)
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="redaction failed"):
        _ = gh.pr_edit_body(runner, 1, "secret", repo="o/r")


def test_pr_checks_text_fallback_word_boundaries() -> None:
    assert gh._pr_checks_text_all_pass("ci\tpass\t0\t0\n")  # pyright: ignore[reportPrivateUsage]
    assert not gh._pr_checks_text_all_pass("ci\tfail\t0\t0\n")  # pyright: ignore[reportPrivateUsage]


def test_pr_checks_text_fallback_when_json_unparseable() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "checks", "1"), 0, "not-json", "", 0.01),
            CommandResult(
                ("gh", "pr", "checks", "1"),
                0,
                "ci\tpass\t0\t0\n",
                "",
                0.01,
            ),
        ],
    )
    assert gh.pr_checks_all_pass(runner, 1, repo="o/r")


def test_find_issue_comment_id_by_marker() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":99,"body":"<!-- larch:final-summary -->\\nbody"}]',
                "",
                0.01,
            ),
        ],
    )
    comment_id = gh.find_issue_comment_id_by_marker(
        runner,
        "7",
        "<!-- larch:final-summary -->",
        repo="o/r",
    )
    assert comment_id == 99


def test_find_issue_comment_id_by_marker_paginated_json() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":1,"body":"other"}][{"id":101,"body":"<!-- larch:diagrams v1 -->\\nbody"}]',
                "",
                0.01,
            ),
        ],
    )
    comment_id = gh.find_issue_comment_id_by_marker(
        runner,
        "42",
        "<!-- larch:diagrams v1 -->",
        repo="owner/repo",
    )
    assert comment_id == 101


def test_find_issue_comment_id_by_marker_normalizes_bom_crlf() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "api"),
                0,
                '[{"id":100,"body":"\\ufeff<!-- larch:final-summary -->\\r\\nbody"}]',
                "",
                0.01,
            ),
        ],
    )
    comment_id = gh.find_issue_comment_id_by_marker(
        runner,
        "7",
        "<!-- larch:final-summary -->",
        repo="o/r",
    )
    assert comment_id == 100


def test_issue_create_uses_body_file_and_optional_repo() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "create"), 0, "", "", 0.01)],
    )
    result = gh.issue_create(runner, repo=None, title="t", body="body")
    assert result.returncode == 0
    assert runner.calls[0][0:4] == ["gh", "issue", "create", "--title"]
    assert "--repo" not in runner.calls[0]
    assert "--body-file" in runner.calls[0]


def test_issue_create_adds_repo_and_surfaces_failure() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "issue", "create"), 1, "", "fail", 0.01)],
    )
    result = gh.issue_create(runner, repo="o/r", title="t", body="body")
    assert result.returncode == 1
    assert "--repo" in runner.calls[0]
    assert "o/r" in runner.calls[0]


def test_run_logs_main_in_progress_exit_three(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("gh", "run", "view", "7"),
                1,
                "",
                "run is still in progress; logs will be available when it is complete",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(gh, "proc", runner)
    assert gh.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 3
    assert "Full log: https://github.com/o/r/actions/runs/7" in capsys.readouterr().out


def test_run_logs_main_failure_exit_one(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[CommandResult(("gh", "run", "view", "7"), 1, "", "boom", 0.01)])
    monkeypatch.setattr(gh, "proc", runner)
    assert gh.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 1
    assert "boom" in capsys.readouterr().out


def test_run_logs_main_tails_raw_log(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    raw = "\n".join(f"line-{idx}" for idx in range(105))
    runner = RecordingRunner(responses=[CommandResult(("gh", "run", "view", "7"), 0, raw, "", 0.01)])
    monkeypatch.setattr(gh, "proc", runner)
    assert gh.run_logs_main(["--run-id", "7", "--repo", "o/r"]) == 0
    out = capsys.readouterr().out
    lines = out.splitlines()
    assert "line-4" not in lines
    assert "line-5" in lines
    assert "line-104" in lines


_JOBS_DURATIONS_PAYLOAD = (
    '{"jobs":['
    '{"name":"test-harnesses (1)","startedAt":"2026-06-16T04:25:00Z",'
    '"completedAt":"2026-06-16T04:26:00Z","conclusion":"success"},'
    '{"name":"test-harnesses (2)","startedAt":"2026-06-16T04:25:00Z",'
    '"completedAt":"2026-06-16T04:25:45Z","conclusion":"success"},'
    '{"name":"lint","startedAt":"2026-06-16T04:25:00Z",'
    '"completedAt":"2026-06-16T04:30:00Z","conclusion":"success"},'
    '{"name":"test-harnesses (3)","startedAt":"2026-06-16T04:25:00Z",'
    '"completedAt":"0001-01-01T00:00:00Z","conclusion":"skipped"}'
    "]}"
)


def test_parse_job_durations_keys_by_shard_and_skips_unusable() -> None:
    # shard 1 = 60s, shard 2 = 45s; the "lint" job is non-matrix and the
    # zero-value completedAt on shard 3 (not-yet-completed) are both skipped.
    durations = gh.parse_job_durations_json(_JOBS_DURATIONS_PAYLOAD)
    assert durations == {1: 60.0, 2: 45.0}


def test_parse_job_durations_accepts_snake_case_stamps() -> None:
    payload = (
        '{"jobs":[{"name":"test-harnesses (5)",'
        '"started_at":"2026-06-16T04:25:00Z","completed_at":"2026-06-16T04:25:30Z"}]}'
    )
    assert gh.parse_job_durations_json(payload) == {5: 30.0}


def test_parse_job_durations_raises_on_missing_jobs_key() -> None:
    with pytest.raises(ShipError):
        _ = gh.parse_job_durations_json('{"jobs":"not-a-list"}')


def test_job_durations_reads_jobs_api() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "run", "view", "11"), 0, _JOBS_DURATIONS_PAYLOAD, "", 0.01),
        ],
    )
    assert gh.job_durations(runner, 11, repo="o/r") == {1: 60.0, 2: 45.0}


def test_job_durations_raises_on_failed_read() -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("gh", "run", "view", "11"), 1, "", "boom", 0.01)],
    )
    with pytest.raises(ShipError):
        _ = gh.job_durations(runner, 11, repo="o/r")
