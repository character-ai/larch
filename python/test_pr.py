"""Tests for pr.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import gh
import pytest

import pr as pr_module
from errors import ShipError
from proc import CommandResult
from run_context import RunContext


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


def _ctx(**kwargs: object) -> RunContext:
    base = RunContext(
        branch="feat",
        issue="9",
        repo="o/r",
        run_id="run-1",
        tmpdir="/tmp/impl",
        merge=True,
        draft=False,
        forked=False,
        manifest_path="/tmp/impl/manifest.json",
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
    )
    return base.with_(**kwargs)


def test_ensure_pr_repo_unavailable() -> None:
    runner = RecordingRunner()
    result = pr_module.ensure_pr(
        runner,
        _ctx(repo_unavailable=True),
        "body",
        title="t",
    )
    assert result.status == "local-only"


def test_ensure_pr_reuses_existing_open(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 0, "", "", 0.01),
        ],
    )
    existing = gh.PullRequest(7, "http://u", "OPEN", "feat")

    def fake_pr_for_branch(
        _runner: object,
        _branch: str,
        *,
        repo: str,  # noqa: ARG001
        cwd: str | None = None,  # noqa: ARG001
    ) -> gh.PullRequest:
        return existing

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_for_branch)
    result = pr_module.ensure_pr(runner, _ctx(), "body\n", title="t")
    assert result.status == "existing"
    assert result.number == 7


def test_ensure_pr_refuses_dirty_tree() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, " M x\n", "", 0.01),
        ],
    )
    with pytest.raises(ShipError):
        _ = pr_module.ensure_pr(runner, _ctx(), "body", title="t")
