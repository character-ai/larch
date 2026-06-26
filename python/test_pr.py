"""Tests for pr.py."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import git as git_module
import gh
import pytest

from larch.core import config
import pr as pr_module
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.run_context import RunContext


from test_support import RecordingRunner, make_run_context


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
    base = make_run_context(issue="9")
    return base.with_(**kwargs)


def test_ensure_pr_invalid_issue_raises() -> None:
    runner = RecordingRunner()
    with pytest.raises(ShipError, match="invalid issue"):
        _ = pr_module.ensure_pr(runner=runner, ctx=_ctx(issue=""), body="body", title="t")


def test_ensure_pr_repo_unavailable() -> None:
    runner = RecordingRunner()
    result = pr_module.ensure_pr(
        runner=runner,
        ctx=_ctx(repo_unavailable=True),
        body="body",
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
    result = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body\n", title="t")
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
        *,
        runner: object,  # noqa: ARG001  # pylint: disable=unused-argument
        number: int,
        body: str,  # noqa: ARG001  # pylint: disable=unused-argument
        repo: str,  # noqa: ARG001  # pylint: disable=unused-argument
        cwd: str | None = None,  # noqa: ARG001  # pylint: disable=unused-argument
    ) -> None:
        edits.append(number)

    monkeypatch.setattr(gh, "pr_for_branch", fake_pr_for_branch)
    monkeypatch.setattr(pr_module.pr_body, "update_pr_body", fake_update)
    result = pr_module.ensure_pr(
        runner=runner,
        ctx=_ctx(pr_number=None),
        body="Summary only\n",
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
        _ = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body", title="t")


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
    _ = pr_module.ensure_pr(runner=runner, ctx=_ctx(draft=True), body="body", title="t")
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
    result = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body", title="t")
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
    result = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body", title="t")
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
        _ = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body", title="t")


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
    result = pr_module.ensure_pr(runner=runner, ctx=_ctx(), body="body", title="t", base="main")
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


def test_create_pr_parity_race_existing_uses_existing_title() -> None:
    runner = RecordingRunner(
        responses=[
            _HEAD_FEAT,
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
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
                (
                    '[{"number":9,"url":"https://github.com/o/r/pull/9",'
                    '"state":"OPEN","headRefName":"feat","title":"Actual title"}]'
                ),
                "",
                0.01,
            ),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo="o/r",
        branch="feat",
        title="Requested title",
        body="body",
    )
    assert result.status == "existing"
    assert result.title == "Actual title"


def test_create_pr_parity_redacts_body_before_create(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, str] = {}

    def fake_pr_create(
        _runner: Runner,
        *,
        body: str,
        **_kwargs: object,
    ) -> tuple[object, bool]:
        captured["body"] = body
        return (
            SimpleNamespace(number=9, url="https://github.com/o/r/pull/9", title="t"),
            True,
        )

    def fake_redact_pr_body(_body: str) -> str:
        return "REDACTED-PR-BODY\n"

    monkeypatch.setattr(pr_module.gh, "pr_create", fake_pr_create)
    monkeypatch.setattr(pr_module.pr_body, "redact_pr_body", fake_redact_pr_body)
    runner = RecordingRunner(
        responses=[
            _HEAD_FEAT,
            _PORCELAIN_CLEAN,
            CommandResult(("gh", "pr", "list"), 0, "[]", "", 0.01),
            CommandResult(("git", "push", "-u", "origin", "HEAD"), 0, "", "", 0.01),
        ],
    )
    result = pr_module.create_pr_parity(
        runner,
        repo="o/r",
        branch="feat",
        title="t",
        body="raw body with secret",
    )
    assert result.exit_code == 0
    assert captured["body"] == "REDACTED-PR-BODY\n"


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


def test_create_branch_retries_transient_fetch(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(config, "TRANSIENT_RETRY_BACKOFF_SEC", (0, 0))
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
            CommandResult(
                ("git", "fetch", "origin", "main", "--quiet"),
                1,
                "",
                "fatal: Could not resolve host",
                0.01,
            ),
            CommandResult(("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01),
            CommandResult(("git", "checkout", "-b", branch, "origin/main"), 0, "", "", 0.01),
        ],
    )
    result = pr_module.create_branch(runner, branch=branch)
    assert result.status == "created"
    assert [call[:2] for call in runner.calls].count(["git", "fetch"]) == 2


# CLI contract tests migrated from test_pr_cli.py.
def test_closes_issue_from_body_file(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    body = tmp_path / "body.md"
    _ = body.write_text("Hello\n\nCloses #3670\n", encoding="utf-8")
    assert pr_module.closes_issue_main(["--body-file", str(body)]) == 0
    assert capsys.readouterr().out.strip() == "3670"


def test_closes_issue_default_repo_failure_empty_stdout(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[CommandResult(("gh", "repo", "view"), 1, "", "no repo", 0.01)])
    monkeypatch.setattr(pr_module, "proc", runner)
    assert pr_module.closes_issue_main([]) == 0
    assert capsys.readouterr().out == "\n"


def test_closes_issue_default_current_pr_success(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[
        CommandResult(("gh", "repo", "view"), 0, "owner/repo\n", "", 0.01),
        CommandResult(("gh", "pr", "view"), 0, "Body\n\nCloses #1234\nCloses #5678\n", "", 0.01),
    ])
    monkeypatch.setattr(pr_module, "proc", runner)
    assert pr_module.closes_issue_main([]) == 0
    assert capsys.readouterr().out.strip() == "1234"


def test_body_update_missing_file(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(pr_module, "proc", RecordingRunner())
    assert pr_module.body_update_main(["--pr", "1", "--body-file", "/no/such/file"]) == 2
    out = capsys.readouterr().out
    assert "UPDATED=false" in out
    assert "body file not found" in out


def test_create_main_invalid_repo_stderr_prefix(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = tmp_path / "body.md"
    _ = body.write_text("body", encoding="utf-8")
    assert pr_module.create_main(
        ["--title", "t", "--body-file", str(body), "--repo", "not-valid", "--branch", "feat"],
    ) == 2
    err = capsys.readouterr().err
    assert err.startswith(
        "create-pr.sh: --repo must be OWNER/REPO using GitHub owner/repo characters",
    )


def test_create_main_detached_head_stderr_prefix(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    body = tmp_path / "body.md"
    _ = body.write_text("body", encoding="utf-8")

    def detached_head(_runner: Runner, *, cwd: str | None = None) -> None:
        _ = cwd

    monkeypatch.setattr(git_module, "try_current_branch", detached_head)
    assert pr_module.create_main(["--title", "t", "--body-file", str(body)]) == 2
    err = capsys.readouterr().err
    assert err.strip() == "create-pr.sh: not on a branch (detached HEAD)"


def test_create_main_missing_body_file_stderr_prefix(capsys: pytest.CaptureFixture[str]) -> None:
    assert pr_module.create_main(
        ["--title", "t", "--body-file", "/no/such/body-file", "--branch", "feat"],
    ) == 2
    err = capsys.readouterr().err
    assert err.startswith("create-pr.sh: cannot read body file:")


def test_checks_main_invalid_repo_exit_2(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(pr_module, "proc", RecordingRunner())
    assert pr_module.checks_main(["--pr", "5", "--repo", "not-valid"]) == 2
    err = capsys.readouterr().err
    assert err.startswith("gh-pr-checks.sh: --repo must be OWNER/REPO")


@pytest.mark.parametrize(
    ("status", "exit_code"),
    [("exists", 1), ("invalid", 2), ("fetch_failed", 2)],
)
def test_create_branch_main_no_kvs_on_non_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    status: str,
    exit_code: int,
) -> None:
    def fake_create_branch(*_a: object, **_k: object) -> pr_module.CreateBranchResult:
        return pr_module.CreateBranchResult(status, "dev/foo", exit_code=exit_code)

    monkeypatch.setattr(pr_module, "create_branch", fake_create_branch)
    rc = pr_module.create_branch_main(["--branch", "dev/foo"])
    assert rc == exit_code
    out = capsys.readouterr().out
    assert "BRANCH_NAME" not in out
    assert "ACTION" not in out
