"""Unit tests for git.py using a stub Runner."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import cast

import pytest

import git
from errors import ShipError
from proc import CommandResult


@dataclass
class StubRunner:
    responses: dict[tuple[str, ...], CommandResult]

    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,  # pylint: disable=unused-argument
        cwd: str | None = None,  # pylint: disable=unused-argument
        env: Mapping[str, str] | None = None,  # pylint: disable=unused-argument
        check: bool = False,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        if key not in self.responses:
            msg = f"unexpected argv: {argv}"
            raise AssertionError(msg)
        return self.responses[key]


def test_rev_parse_builds_argv() -> None:
    runner = StubRunner(
        {
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"),
                0,
                "abc\n",
                "",
                0.01,
            ),
        },
    )
    assert git.rev_parse(runner, "HEAD") == "abc"


def test_status_parses_porcelain() -> None:
    runner = StubRunner(
        {
            ("git", "status", "--porcelain"): CommandResult(
                ("git", "status", "--porcelain"),
                0,
                " M file.txt\n",
                "",
                0.01,
            ),
        },
    )
    status = git.status(runner)
    assert "file.txt" in status.porcelain


def test_log_subjects() -> None:
    runner = StubRunner(
        {
            ("git", "log", "--format=%s", "main..HEAD"): CommandResult(
                ("git", "log", "--format=%s", "main..HEAD"),
                0,
                "first\nsecond\n",
                "",
                0.01,
            ),
        },
    )
    subjects = git.log_subjects(runner, "main..HEAD")
    assert subjects.subjects == ("first", "second")


def test_operation_helpers_build_expected_argv() -> None:
    responses = {
        ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
            ("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01
        ),
        ("git", "branch", "topic"): CommandResult(
            ("git", "branch", "topic"), 0, "", "", 0.01
        ),
        ("git", "rev-list", "--count", "main..HEAD"): CommandResult(
            ("git", "rev-list", "--count", "main..HEAD"), 0, "2\n", "", 0.01
        ),
        ("git", "merge-base", "main", "HEAD"): CommandResult(
            ("git", "merge-base", "main", "HEAD"), 0, "abc\n", "", 0.01
        ),
        ("git", "rebase", "main"): CommandResult(
            ("git", "rebase", "main"), 0, "", "", 0.01
        ),
        ("git", "push", "origin", "HEAD"): CommandResult(
            ("git", "push", "origin", "HEAD"), 0, "", "", 0.01
        ),
        ("git", "push", "--force-with-lease", "origin", "HEAD"): CommandResult(
            ("git", "push", "--force-with-lease", "origin", "HEAD"), 0, "", "", 0.01
        ),
        ("git", "reset", "--hard", "HEAD"): CommandResult(
            ("git", "reset", "--hard", "HEAD"), 0, "", "", 0.01
        ),
        ("git", "ls-files", "a.txt", "b.txt"): CommandResult(
            ("git", "ls-files", "a.txt", "b.txt"), 0, "a.txt\n", "", 0.01
        ),
    }
    runner = StubRunner(responses)
    assert git.current_branch(runner) == "feat"
    assert git.branch(runner, "topic").returncode == 0
    assert git.rev_count(runner, "main", "HEAD") == 2
    assert git.merge_base(runner, "main", "HEAD") == "abc"
    assert git.rebase(runner, "main").returncode == 0
    assert git.push(runner, "origin", "HEAD").returncode == 0
    assert git.force_push_with_lease(runner, "origin", "HEAD").returncode == 0
    assert git.reset(runner, "--hard", "HEAD").returncode == 0
    assert git.ls_files(runner, "a.txt", "b.txt") == ("a.txt",)


def test_rev_count_raises_ship_error_on_non_integer_stdout() -> None:
    runner = StubRunner(
        {
            ("git", "rev-list", "--count", "main..HEAD"): CommandResult(
                ("git", "rev-list", "--count", "main..HEAD"),
                0,
                "not-a-number\n",
                "",
                0.01,
            ),
        },
    )
    with pytest.raises(ShipError, match="non-integer stdout"):
        _ = git.rev_count(runner, "main", "HEAD")


def test_fetch_and_show_file_argv() -> None:
    runner = StubRunner(
        {
            ("git", "fetch", "origin", "main", "--quiet"): CommandResult(
                ("git", "fetch", "origin", "main", "--quiet"), 0, "", "", 0.01
            ),
            ("git", "show", "HEAD:file.txt"): CommandResult(
                ("git", "show", "HEAD:file.txt"), 0, "content\n", "", 0.01
            ),
        },
    )
    assert git.fetch(runner, "origin", "main").returncode == 0
    shown = git.show_file(runner, "HEAD:file.txt")
    assert shown.stdout == "content\n"


def test_diff_and_rebase_helpers() -> None:
    runner = StubRunner(
        {
            ("git", "diff", "--name-only", "base", "HEAD"): CommandResult(
                ("git", "diff", "--name-only", "base", "HEAD"),
                0,
                "a.txt\n",
                "",
                0.01,
            ),
            ("git", "diff", "-M", "--name-status", "base", "HEAD", "--", "skills"): CommandResult(
                ("git", "diff", "-M", "--name-status", "base", "HEAD", "--", "skills"),
                0,
                "M\tskills/x/SKILL.md\n",
                "",
                0.01,
            ),
            ("git", "rebase", "--onto", "HEAD~2", "HEAD~1"): CommandResult(
                ("git", "rebase", "--onto", "HEAD~2", "HEAD~1"), 0, "", "", 0.01
            ),
        },
    )
    names = git.diff_name_only(runner, "base", "HEAD")
    assert "a.txt" in names.stdout
    status = git.diff_name_status(
        runner,
        "base",
        "HEAD",
        paths=("skills",),
        find_renames=True,
    )
    assert "SKILL.md" in status.stdout
    assert git.rebase_onto(runner, "HEAD~2", "HEAD~1").returncode == 0


def test_value_helper_raises_on_failure() -> None:
    runner = StubRunner(
        {
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"),
                128,
                "",
                "fatal",
                0.01,
            ),
        },
    )
    with pytest.raises(ShipError):
        _ = git.rev_parse(runner, "HEAD")


def test_rebase_onto_strips_git_dir_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_DIR", "/evil")
    monkeypatch.setenv("GIT_WORK_TREE", "/evil")
    captured: dict[str, object] = {}

    class CaptureRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
        ) -> CommandResult:
            _ = timeout, cwd, check
            captured["env"] = dict(env) if env else {}
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    _ = git.rebase_onto(CaptureRunner(), "HEAD~2", "HEAD~1")
    env = cast(dict[str, str], captured["env"])
    assert "GIT_DIR" not in env
    assert "GIT_WORK_TREE" not in env
    assert env.get("GIT_SEQUENCE_EDITOR") == "true"
