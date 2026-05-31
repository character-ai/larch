"""Unit tests for gh.py using a stub Runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path

import pytest

import config
import gh
from errors import ShipError
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
    pr = gh.pr_create(
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
    pr = gh.pr_create(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="b",
    )
    assert pr.number == 42
    assert len(runner.calls) == 3
    assert runner.calls[1][runner.calls[1].index("--body-file") + 1].endswith(".md")


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
        gh.pr_view(runner, 1, repo="o/r")


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
    with pytest.raises(ShipError):
        gh.pr_view(runner, 1, repo="o/r")
    assert len(runner.calls) == config.TRANSIENT_RETRY_MAX_ATTEMPTS


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
        gh.pr_view(runner, 1, repo="o/r")
