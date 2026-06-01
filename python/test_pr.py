"""Tests for pr.py."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field

import git as git_module
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
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> gh.PullRequest:
        return existing

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_for_branch)
    result = pr_module.ensure_pr(runner, _ctx(), "body\n", title="t")
    assert result.status == "existing"
    assert result.number == 7


def test_ensure_pr_updates_body_without_ctx_pr_number(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "edit", "7"), 0, "", "", 0.01),
        ],
    )
    existing = gh.PullRequest(7, "http://u", "OPEN", "feat")
    edits: list[int] = []

    def fake_pr_for_branch(
        _runner: object,
        _branch: str,
        *,
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> gh.PullRequest:
        return existing

    def fake_update(
        _runner: object,
        number: int,
        _body: str,
        *,
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> None:
        edits.append(number)

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_for_branch)
    monkeypatch.setattr(pr_module.pr_body, "update_pr_body", fake_update)
    result = pr_module.ensure_pr(
        runner,
        _ctx(pr_number=None),
        "Summary only\n",
        title="t",
    )
    assert result.number == 7
    assert edits == [7]


def test_ensure_pr_raises_when_push_fails() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 1, "", "rejected", 0.01),
            CommandResult(("git", "push"), 1, "", "rejected", 0.01),
            CommandResult(("git", "push"), 1, "", "rejected", 0.01),
        ],
    )

    with pytest.raises(ShipError, match="branch push failed"):
        _ = pr_module.ensure_pr(runner, _ctx(), "body", title="t")


def test_ensure_pr_passes_draft_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, '{"number":3,"url":"u","state":"OPEN","headRefName":"feat"}', "", 0.01),
        ],
    )
    drafts: list[bool] = []

    def fake_create(
        _runner: object,
        *,
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        branch: str,  # noqa: ARG001  # pylint: disable=unused-argument
        title: str,  # noqa: ARG001  # pylint: disable=unused-argument
        body: str,  # noqa: ARG001  # pylint: disable=unused-argument
        draft: bool = False,
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
        **kwargs: object,  # pylint: disable=unused-argument
    ) -> gh.PullRequest:
        _ = kwargs
        drafts.append(draft)
        return gh.PullRequest(3, "http://u", "OPEN", "feat")

    def fake_pr_none(
        _runner: object,
        _branch: str,
        *,
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> None:
        return None

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_none)
    monkeypatch.setattr(gh, "pr_create", fake_create)
    _ = pr_module.ensure_pr(runner, _ctx(draft=True), "body", title="t")
    assert drafts == [True]


def test_ensure_pr_recovers_create_conflict() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(
                ("gh", "pr", "create"),
                1,
                "",
                "pull request for branch already exists https://github.com/o/r/pull/11",
                0.01,
            ),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":11,"url":"https://github.com/o/r/pull/11","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.ensure_pr(runner, _ctx(), "body", title="t")
    assert result.number == 11


def test_ensure_pr_force_push_recovery_on_existing_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, "", "", 0.01),
            CommandResult(("git", "push"), 1, "", "rejected", 0.01),
            CommandResult(("git", "push"), 0, "", "", 0.01),
        ],
    )
    existing = gh.PullRequest(7, "http://u", "OPEN", "feat")
    recoveries: list[bool] = []

    def fake_recovery(*_a: object, **_k: object) -> git_module.ForcePushResult:
        recoveries.append(True)
        return git_module.ForcePushResult(pushed=True, status="ok")

    def fake_pr_for_branch(
        _runner: object,
        _branch: str,
        *,
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> gh.PullRequest:
        return existing

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_for_branch)
    monkeypatch.setattr(git_module, "force_push_recovery", fake_recovery)
    result = pr_module.ensure_pr(runner, _ctx(), "body", title="t")
    assert result.status == "existing"
    assert recoveries == [True]


def test_ensure_pr_refuses_dirty_tree() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "status"), 0, " M x\n", "", 0.01),
        ],
    )
    with pytest.raises(ShipError):
        _ = pr_module.ensure_pr(runner, _ctx(), "body", title="t")
