"""Tests for pr.py."""

from __future__ import annotations


import git as git_module
import gh
import pytest

import pr as pr_module
from errors import ShipError
from proc import CommandResult
from run_context import RunContext


from test_support import RecordingRunner


_PORCELAIN_CLEAN = CommandResult(
    ("git", "status", "--porcelain", "--untracked-files=all"),
    0,
    "",
    "",
    0.01,
)
_HEAD_FEAT = CommandResult(
    ("git", "symbolic-ref", "--short", "HEAD"),
    0,
    "feat\n",
    "",
    0.01,
)


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


def test_ensure_pr_invalid_issue_raises() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid issue"):
        _ = pr_module.ensure_pr(runner, _ctx(issue=""), "body", title="t")


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
            _PORCELAIN_CLEAN,
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
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
            _PORCELAIN_CLEAN,
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
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
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            _PORCELAIN_CLEAN,
            _HEAD_FEAT,
            CommandResult(("git", "push", "origin"), 1, "", "rejected", 0.01),
            CommandResult(("git", "push", "origin"), 1, "", "rejected", 0.01),
            CommandResult(("git", "push", "origin"), 1, "", "rejected", 0.01),
        ],
    )

    with pytest.raises(ShipError, match="branch push failed"):
        _ = pr_module.ensure_pr(runner, _ctx(), "body", title="t")


def test_ensure_pr_passes_draft_flag(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = RecordingRunner(
        responses=[
            _PORCELAIN_CLEAN,
            _PORCELAIN_CLEAN,
            _HEAD_FEAT,
            CommandResult(("git", "push", "origin"), 0, "", "", 0.01),
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
    ) -> tuple[gh.PullRequest, bool]:
        _ = kwargs
        drafts.append(draft)
        return gh.PullRequest(3, "http://u", "OPEN", "feat"), True

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
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            _PORCELAIN_CLEAN,
            _HEAD_FEAT,
            CommandResult(("git", "push", "origin"), 0, "", "", 0.01),
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
    assert result.status == "existing"


def test_ensure_pr_force_push_recovery_on_existing_open(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            _PORCELAIN_CLEAN,
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 1, "", "rejected", 0.01),
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
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                " M x\n",
                "",
                0.01,
            ),
        ],
    )
    with pytest.raises(ShipError):
        _ = pr_module.ensure_pr(runner, _ctx(), "body", title="t")


def test_ensure_pr_threads_base_to_create() -> None:
    runner = RecordingRunner(
        responses=[
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            _PORCELAIN_CLEAN,
            _HEAD_FEAT,
            CommandResult(("git", "push", "origin"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, "https://github.com/o/r/pull/10\n", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, '[{"number":10,"url":"u","state":"OPEN","headRefName":"feat"}]', "", 0.01),
        ],
    )
    result = pr_module.ensure_pr(runner, _ctx(), "body", title="t", base="main")
    assert result.number == 10
    create_call = next(call for call in runner.calls if call[:3] == ["gh", "pr", "create"])
    assert "--base" in create_call
    assert "main" in create_call


def test_create_pr_parity_existing_open_uses_github_title() -> None:
    runner = RecordingRunner(
        responses=[
            _HEAD_FEAT,
            _PORCELAIN_CLEAN,
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":3,"url":"https://github.com/o/r/pull/3","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
            _PORCELAIN_CLEAN,
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
            CommandResult(
                ("gh", "pr", "view", "3"),
                0,
                "Existing title\n",
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo="o/r",
        branch="feat",
        title="fallback",
        body="body",
    )
    assert result.exit_code == 0
    assert result.status == "existing"
    assert result.title == "Existing title"


def test_create_pr_parity_dirty_tree_exit_1() -> None:
    runner = RecordingRunner(
        responses=[
            _HEAD_FEAT,
            CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                " M dirty.txt\n",
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="body",
    )
    assert result.exit_code == 1
    assert result.status == "push_failed"


def test_create_pr_parity_detached_head_exit_2() -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "symbolic-ref", "--short", "HEAD"), 1, "", "", 0.01),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="body",
    )
    assert result.exit_code == 2


def test_create_pr_parity_omits_repo_when_unresolved() -> None:
    runner = RecordingRunner(
        responses=[
            _HEAD_FEAT,
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("gh", "pr", "create"), 0, "https://github.com/o/r/pull/9\n", "", 0.01),
            CommandResult(
                ("gh", "pr", "list"),
                0,
                '[{"number":9,"url":"https://github.com/o/r/pull/9","state":"OPEN","headRefName":"feat"}]',
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo=None,
        branch="feat",
        title="t",
        body="body",
    )
    create_calls = [call for call in runner.calls if call[:3] == ["gh", "pr", "create"]]
    assert create_calls
    assert "--repo" not in create_calls[0]
    assert result.exit_code == 0


def test_create_branch_ignores_tag_with_same_name() -> None:
    branch = "dev-user/feature"
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "config", "user.name"), 0, "Dev-User\n", "", 0.01),
            CommandResult(
                ("git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"),
                1,
                "",
                "",
                0.01,
            ),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(
                ("git", "checkout", "-b", branch, "origin/main"),
                0,
                "",
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.create_branch(runner, branch=branch)
    assert result.status == "created"
    assert result.exit_code == 0
