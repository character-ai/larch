"""Unit tests for gh.py using a stub Runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import gh
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


def test_pr_merge_not_retried() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("gh", "pr", "merge", "1"), 0, "", "", 0.01),
        ],
    )
    _ = gh.pr_merge(runner, 1, repo="o/r")
    assert len(runner.calls) == 1
