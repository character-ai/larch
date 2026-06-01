"""Tests for tracking_issue.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import config
import tracking_issue
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
            return CommandResult(tuple(argv), 0, "", "", 0.01)
        result = self.responses[self._index]
        self._index += 1
        return result


def test_link_pr_closes_appends() -> None:
    body = "Summary\n"
    linked = tracking_issue.link_pr_closes(body, 42)
    assert "Closes #42" in linked


def test_rename_strips_legacy_prefix() -> None:
    runner = RecordingRunner()
    title = "[IN PROGRESS] [DONE] My feature"
    new = tracking_issue.rename(
        runner,
        "1",
        "done",
        repo="o/r",
        current_title=title,
    )
    assert new.startswith(config.TRACKING_ISSUE_PREFIX_BY_STATE["done"])
    assert "[IN PROGRESS]" not in new
