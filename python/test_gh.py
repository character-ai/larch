"""Unit tests for gh.py using a stub Runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import gh
from errors import ShipError, TransientNetworkError
from proc import CommandResult


def _empty_str_lists() -> list[list[str]]:
    return []


def _empty_command_results() -> list[CommandResult]:
    return []


@dataclass
class RecordingRunner:
    calls: list[list[str]] = field(default_factory=_empty_str_lists)
    responses: list[CommandResult] = field(default_factory=_empty_command_results)
    _index: int = 0

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
        self.calls.append(list(argv))
        if self._index >= len(self.responses):
            msg = f"no response for call {argv}"
            raise AssertionError(msg)
        result = self.responses[self._index]
        self._index += 1
        return result


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
    assert len(runner.calls) == 3


def test_pr_create_uses_body_file_not_inline_body() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                0,
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
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
    assert "secret-body" not in create_argv
    body_path = create_argv[create_argv.index("--body-file") + 1]
    assert Path(body_path).is_file() is False


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
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
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
                '{"number":1,"url":"u","state":"OPEN","headRefName":"feat"}',
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
