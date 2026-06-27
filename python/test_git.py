"""Unit tests for git.py using a stub Runner."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import cast

import pytest

from larch.git import git
from larch.core import retry
from larch.errors import ShipError
from larch.core.proc import CommandResult, ProcRunner
from larch.implement import phantom
from test_support import RecordingRunner


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
        stdout: int | None = None,  # pylint: disable=unused-argument
        stderr: int | None = None,  # pylint: disable=unused-argument
    ) -> CommandResult:
        key = tuple(argv)
        if key not in self.responses:
            msg = f"unexpected argv: {argv}"
            raise AssertionError(msg)
        return self.responses[key]


def _immediate_retry(
    fn: Callable[[], tuple[CommandResult, int, str]],
    **_kwargs: object,
) -> retry.RetryResult[CommandResult]:
    value, rc, _content = fn()
    return retry.RetryResult(value=value, attempts=1, last_returncode=rc)


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


def test_snapshot_untracked_sorts_success_output(tmp_path: Path) -> None:
    output = tmp_path / "baseline.z"
    runner = StubRunner(
        {
            ("git", "ls-files", "--others", "--exclude-standard", "-z"): CommandResult(
                ("git", "ls-files", "--others", "--exclude-standard", "-z"),
                0,
                "b.txt\x00a.txt\x00",
                "",
                0.01,
            ),
        },
    )
    assert git.snapshot_untracked(runner, str(output), nul=True) == 0
    assert output.read_bytes() == b"a.txt\x00b.txt\x00"


def test_snapshot_untracked_removes_stale_output_on_failure(tmp_path: Path) -> None:
    output = tmp_path / "baseline.z"
    _ = output.write_text("stale", encoding="utf-8")
    tmp = tmp_path / "baseline.z.tmp"
    _ = tmp.write_text("stale tmp", encoding="utf-8")
    runner = StubRunner(
        {
            ("git", "ls-files", "--others", "--exclude-standard"): CommandResult(
                ("git", "ls-files", "--others", "--exclude-standard"),
                1,
                "",
                "fatal",
                0.01,
            ),
        },
    )
    assert git.snapshot_untracked(runner, str(output)) == 0
    assert not output.exists()
    assert not tmp.exists()


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


def test_commit_and_add_build_argv() -> None:
    runner = StubRunner(
        {
            ("git", "add", "--", "README.md"): CommandResult(
                ("git", "add", "--", "README.md"), 0, "", "", 0.01
            ),
            ("git", "commit", "-m", "Update docs for 1.0.0", "--only"): CommandResult(
                ("git", "commit", "-m", "Update docs for 1.0.0", "--only"),
                0,
                "",
                "",
                0.01,
            ),
        },
    )
    assert git.add(runner, "README.md").returncode == 0
    assert (
        git.commit(runner, "Update docs for 1.0.0", only=True).returncode == 0
    )


def _run_git(repo: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _ = _run_git(repo, "init", "-b", "main")
    _ = _run_git(repo, "config", "user.email", "test@example.com")
    _ = _run_git(repo, "config", "user.name", "Test")
    _ = (repo / "file.txt").write_text("base\n", encoding="utf-8")
    _ = _run_git(repo, "add", "file.txt")
    _ = _run_git(repo, "commit", "-m", "init")


def _not_held(
    _runner: object,
    _lock_path: Path,
    *,
    cwd: str | None = None,  # pylint: disable=unused-argument
) -> bool:
    _ = cwd
    return False


def _held(
    _runner: object,
    _lock_path: Path,
    *,
    cwd: str | None = None,  # pylint: disable=unused-argument
) -> bool:
    _ = cwd
    return True


def test_commit_removes_zero_byte_index_lock_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    _ = _run_git(repo, "add", "file.txt")
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    result = git.commit(ProcRunner(), "change", cwd=str(repo))

    assert result.returncode == 0
    assert not lock.exists()
    assert _run_git(repo, "log", "-1", "--format=%s").stdout.strip() == "change"


def test_commit_refuses_non_empty_index_lock(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    _ = _run_git(repo, "add", "file.txt")
    lock = repo / ".git" / "index.lock"
    _ = lock.write_text("active\n", encoding="utf-8")
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    result = git.commit(ProcRunner(), "change", cwd=str(repo))

    assert result.returncode != 0
    assert lock.exists()
    assert "non-empty lock" in result.stderr


def test_commit_refuses_zero_byte_index_lock_when_lock_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    _ = _run_git(repo, "add", "file.txt")
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _held)

    result = git.commit(ProcRunner(), "change", cwd=str(repo))

    assert result.returncode != 0
    assert lock.exists()
    assert "lock held by process" in result.stderr


def test_commit_retries_only_once(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    git_dir = tmp_path / ".git"
    git_dir.mkdir()
    lock = git_dir / "index.lock"
    lock.touch()
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "commit", "-m", "msg"), 128, "", "fatal: Unable to create index.lock\n", 0.01),
            CommandResult(("git", "rev-parse", "--absolute-git-dir"), 0, str(git_dir) + "\n", "", 0.01),
            CommandResult(("git", "rev-parse", "--absolute-git-dir"), 0, str(git_dir) + "\n", "", 0.01),
            CommandResult(("git", "commit", "-m", "msg"), 128, "", "fatal: still failed\n", 0.01),
        ],
    )
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    result = git.commit(runner, "msg")

    assert result.returncode == 128
    assert not lock.exists()
    assert [call[:3] for call in runner.calls].count(["git", "commit", "-m"]) == 2


def test_try_remove_stale_index_lock_ignores_unrelated_git_process(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    removed, diagnostic = git._try_remove_stale_index_lock(ProcRunner(), cwd=str(repo))  # pyright: ignore[reportPrivateUsage]

    assert removed
    assert "removed stale" in diagnostic
    assert not lock.exists()


def test_try_remove_stale_index_lock_refuses_when_lock_held(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _held)

    removed, diagnostic = git._try_remove_stale_index_lock(ProcRunner(), cwd=str(repo))  # pyright: ignore[reportPrivateUsage]

    assert not removed
    assert "lock=" in diagnostic
    assert lock.exists()


def test_index_lock_is_held_false_when_lock_absent(tmp_path: Path) -> None:
    lock = tmp_path / "repo" / ".git" / "index.lock"

    assert git._index_lock_is_held(RecordingRunner(), lock) is False  # pyright: ignore[reportPrivateUsage]


def test_add_removes_zero_byte_index_lock_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    result = git.add(ProcRunner(), "file.txt", cwd=str(repo))

    assert result.returncode == 0
    assert not lock.exists()
    assert _run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["file.txt"]


def test_add_pathspec_file_removes_zero_byte_index_lock_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    pathspec = tmp_path / "paths.txt"
    _ = pathspec.write_text("file.txt\n", encoding="utf-8")
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    result = git.add_pathspec_file(ProcRunner(), str(pathspec), cwd=str(repo))

    assert result.returncode == 0
    assert not lock.exists()
    assert _run_git(repo, "diff", "--cached", "--name-only").stdout.splitlines() == ["file.txt"]


def test_commit_main_pathspec_from_file_removes_zero_byte_index_lock_and_retries(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    _ = (repo / "file.txt").write_text("changed\n", encoding="utf-8")
    pathspec = tmp_path / "paths.txt"
    _ = pathspec.write_text("file.txt\n", encoding="utf-8")
    lock = repo / ".git" / "index.lock"
    lock.touch()
    monkeypatch.chdir(repo)
    monkeypatch.setattr(git, "proc", ProcRunner())
    monkeypatch.setattr(git, "_index_lock_is_held", _not_held)

    rc = git.commit_main(["--only", "--pathspec-from-file", str(pathspec), "-m", "msg"])

    assert rc == 0
    assert not lock.exists()
    assert _run_git(repo, "log", "-1", "--format=%s").stdout.strip() == "msg"


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


def test_diff_tree_name_only_invocation() -> None:
    runner = StubRunner(
        {
            ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD~1"): CommandResult(
                ("git", "diff-tree", "--no-commit-id", "--name-only", "-r", "HEAD~1"),
                0,
                "README.md\n",
                "",
                0.01,
            ),
        },
    )
    result = git.diff_tree_name_only(runner, "HEAD~1")
    assert result.returncode == 0
    assert "README.md" in result.stdout


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


def test_try_current_branch_detached() -> None:
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"),
                128,
                "",
                "fatal: HEAD detached",
                0.01,
            ),
        },
    )
    assert git.try_current_branch(runner) is None


def test_unmerged_paths_argv() -> None:
    runner = StubRunner(
        {
            ("git", "diff", "--name-only", "--diff-filter=U"): CommandResult(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                0,
                "a.txt\nb.txt\n",
                "",
                0.01,
            ),
        },
    )
    assert git.unmerged_paths(runner) == ["a.txt", "b.txt"]


def test_unmerged_paths_nonzero_diff_raises() -> None:
    runner = StubRunner(
        {
            ("git", "diff", "--name-only", "--diff-filter=U"): CommandResult(
                ("git", "diff", "--name-only", "--diff-filter=U"),
                1,
                "",
                "fatal: bad diff",
                0.01,
            ),
        },
    )
    with pytest.raises(ShipError, match="git command failed"):
        _ = git.unmerged_paths(runner)


def test_checkout_ours_argv() -> None:
    runner = StubRunner(
        {
            ("git", "checkout", "--ours", "--", "f.txt"): CommandResult(
                ("git", "checkout", "--ours", "--", "f.txt"),
                0,
                "",
                "",
                0.01,
            ),
        },
    )
    assert git.checkout_ours(runner, "f.txt").returncode == 0


def test_is_ancestor_mapping() -> None:
    runner = StubRunner(
        {
            ("git", "merge-base", "--is-ancestor", "main", "HEAD"): CommandResult(
                ("git", "merge-base", "--is-ancestor", "main", "HEAD"),
                0,
                "",
                "",
                0.01,
            ),
            ("git", "merge-base", "--is-ancestor", "other", "HEAD"): CommandResult(
                ("git", "merge-base", "--is-ancestor", "other", "HEAD"),
                1,
                "",
                "",
                0.01,
            ),
        },
    )
    assert git.is_ancestor(runner, "main", "HEAD") is True
    assert git.is_ancestor(runner, "other", "HEAD") is False


def test_rebase_continue_sets_editors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_DIR", "/evil")
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
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> CommandResult:
            _ = timeout, cwd, check, stdout, stderr
            captured["env"] = dict(env) if env else {}
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    _ = git.rebase_continue(CaptureRunner())
    env = cast("dict[str, str]", captured["env"])
    assert env.get("GIT_SEQUENCE_EDITOR") == "true"
    assert env.get("GIT_EDITOR") == "true"


def test_rebase_skip_argv() -> None:
    runner = StubRunner(
        {
            ("git", "rebase", "--skip"): CommandResult(
                ("git", "rebase", "--skip"), 0, "", "", 0.01
            ),
        },
    )
    assert git.rebase_skip(runner).returncode == 0


def test_force_push_with_lease_expecting_argv() -> None:
    runner = StubRunner(
        {
            (
                "git",
                "push",
                "--force-with-lease=refs/heads/feat:abc123",
                "origin",
            ): CommandResult(
                (
                    "git",
                    "push",
                    "--force-with-lease=refs/heads/feat:abc123",
                    "origin",
                ),
                0,
                "",
                "",
                0.01,
            ),
        },
    )
    result = git.force_push_with_lease_expecting(
        runner,
        "origin",
        "refs/heads/feat",
        "abc123",
    )
    assert result.returncode == 0


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
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> CommandResult:
            _ = timeout, cwd, check, stdout, stderr
            captured["env"] = dict(env) if env else {}
            return CommandResult(tuple(argv), 0, "", "", 0.01)

    _ = git.rebase_onto(CaptureRunner(), "HEAD~2", "HEAD~1")
    env = cast("dict[str, str]", captured["env"])
    assert "GIT_DIR" not in env
    assert "GIT_WORK_TREE" not in env
    assert env.get("GIT_SEQUENCE_EDITOR") == "true"


def test_try_log_subjects_empty_on_failure() -> None:
    runner = StubRunner(
        {
            ("git", "log", "--format=%s", "bad..HEAD"): CommandResult(
                ("git", "log", "--format=%s", "bad..HEAD"),
                1,
                "",
                "fatal",
                0.01,
            ),
        },
    )
    subjects = git.try_log_subjects(runner, "bad..HEAD")
    assert not subjects.subjects


def test_force_push_recovery_status_failed_on_git_status_error() -> None:
    runner = StubRunner(
        {
            (
                "git",
                "symbolic-ref",
                "--short",
                "HEAD",
            ): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"),
                0,
                "feat\n",
                "",
                0.01,
            ),
            (
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                1,
                "",
                "fatal",
                0.01,
            ),
        },
    )
    result = git.force_push_recovery(runner, branch="feat", remote="origin")
    assert not result.pushed
    assert result.status == "status_failed"


def test_force_push_recovery_noop_same_ref() -> None:
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01
            ),
            (
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                "",
                "",
                0.01,
            ),
            ("git", "fetch", "origin", "feat", "--quiet"): CommandResult(
                ("git", "fetch", "origin", "feat", "--quiet"), 0, "", "", 0.01
            ),
            (
                "git",
                "push",
                "--force-with-lease",
                "origin",
                "HEAD:refs/heads/feat",
            ): CommandResult(
                (
                    "git",
                    "push",
                    "--force-with-lease",
                    "origin",
                    "HEAD:refs/heads/feat",
                ),
                1,
                "",
                "rejected",
                0.01,
            ),
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"), 0, "abc\n", "", 0.01
            ),
            ("git", "rev-parse", "origin/feat"): CommandResult(
                ("git", "rev-parse", "origin/feat"), 0, "abc\n", "", 0.01
            ),
        },
    )
    result = git.force_push_recovery(
        runner,
        branch=None,
        remote="origin",
        sleeper=lambda _s: None,
    )
    assert result.pushed
    assert result.status == "noop_same_ref"


def test_force_push_recovery_diverged_retry_failed() -> None:
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01
            ),
            (
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                "",
                "",
                0.01,
            ),
            ("git", "fetch", "origin", "feat", "--quiet"): CommandResult(
                ("git", "fetch", "origin", "feat", "--quiet"), 0, "", "", 0.01
            ),
            (
                "git",
                "push",
                "--force-with-lease",
                "origin",
                "HEAD:refs/heads/feat",
            ): CommandResult(
                (
                    "git",
                    "push",
                    "--force-with-lease",
                    "origin",
                    "HEAD:refs/heads/feat",
                ),
                1,
                "",
                "rejected",
                0.01,
            ),
            ("git", "rev-parse", "HEAD"): CommandResult(
                ("git", "rev-parse", "HEAD"), 0, "local\n", "", 0.01
            ),
            ("git", "rev-parse", "origin/feat"): CommandResult(
                ("git", "rev-parse", "origin/feat"), 0, "remote\n", "", 0.01
            ),
        },
    )
    result = git.force_push_recovery(
        runner,
        branch=None,
        remote="origin",
        sleeper=lambda _s: None,
    )
    assert not result.pushed
    assert result.status == "diverged_retry_failed"


def test_force_push_recovery_branch_mismatch() -> None:
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01
            ),
        },
    )
    result = git.force_push_recovery(runner, branch="other", remote="origin")
    assert not result.pushed
    assert result.status == "branch_mismatch"


def test_force_push_recovery_dirty_worktree() -> None:
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"), 0, "feat\n", "", 0.01
            ),
            (
                "git",
                "status",
                "--porcelain",
                "--untracked-files=all",
            ): CommandResult(
                ("git", "status", "--porcelain", "--untracked-files=all"),
                0,
                " M dirty\n",
                "",
                0.01,
            ),
        },
    )
    result = git.force_push_recovery(runner, branch="feat", remote="origin")
    assert not result.pushed
    assert result.status == "dirty_worktree"


# CLI contract tests migrated from test_git_cli.py.
def _ok(stdout: str = "", stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 0, stdout, stderr, 0.01)


def _fail(stderr: str = "") -> CommandResult:
    return CommandResult(("cmd",), 1, "", stderr, 0.01)


def test_count_commits_missing_main_status_file(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_fail(), _fail()])
    monkeypatch.setattr(git, "proc", runner)
    status_file = tmp_path / "status"
    monkeypatch.setenv("COUNT_COMMITS_STATUS_FILE", str(status_file))
    assert git.count_commits_main([]) == 0
    assert capsys.readouterr().out.strip() == "0"
    assert status_file.read_text(encoding="utf-8").strip() == "missing_main_ref"


def test_branch_info_emits_detached_empty_branch(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[_ok("abc123\n"), _ok("\n")])
    monkeypatch.setattr(git, "proc", runner)
    assert git.branch_info_main([]) == 0
    out = capsys.readouterr().out
    assert "HEAD_SHA=abc123" in out
    assert "CURRENT_BRANCH=" in out


def test_clean_tree_fail_closed_probe_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[CommandResult(("git",), 128, "", "no repo\n", 0.01)])
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main(["--fail-closed"]) == 1
    out = capsys.readouterr().out
    assert "CLEAN=unknown" in out
    assert "PROBE_ERROR=git exited 128" in out


def test_clean_tree_clean_repo(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(responses=[CommandResult(("git", "status", "--porcelain"), 0, "", "", 0.01)])
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main([]) == 0
    out = capsys.readouterr().out
    assert "CLEAN=true" in out
    assert "DIRTY_OUT=" not in out


def test_clean_tree_dirty_default(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("git", "status", "--porcelain"), 0, "?? untracked.txt\n", "", 0.01)],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main([]) == 0
    out = capsys.readouterr().out
    assert "CLEAN=false" in out
    assert "DIRTY_OUT=" in out


def test_clean_tree_dirty_fail_closed(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses=[CommandResult(("git", "status", "--porcelain"), 0, "?? untracked.txt\n", "", 0.01)],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main(["--fail-closed"]) == 0
    out = capsys.readouterr().out
    assert "CLEAN=false" in out
    assert "DIRTY_OUT=" in out


def test_clean_tree_probe_failure_default_fail_open(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain"),
                1,
                "",
                "fatal: shim status failed\nsecond line\twith tab\n",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main([]) == 0
    out = capsys.readouterr().out
    assert "CLEAN=true" in out


def test_clean_tree_probe_failure_fail_closed_sanitizes_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "status", "--porcelain"),
                1,
                "",
                "fatal: shim status failed\nsecond line\twith tab\n",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.clean_tree_main(["--fail-closed"]) == 1
    out = capsys.readouterr().out
    assert "CLEAN=unknown" in out
    assert "PROBE_ERROR=git exited 1" in out
    assert "\t" not in out


def test_clean_tree_bad_arg_exit_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert git.clean_tree_main(["--unknown-flag"]) == 2
    assert "unknown" in capsys.readouterr().err.lower()


def test_check_phantom_dirty_clean_omits_optional_keys(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(git, "proc", runner)

    def _clean_probe(*_args: object, **_kwargs: object) -> phantom.PhantomDirtyResult:
        return phantom.PhantomDirtyResult(status="clean")

    monkeypatch.setattr(phantom, "check_phantom_dirty", _clean_probe)
    assert (
        git.check_phantom_dirty_main(
            ["--baseline", "/tmp/base.z", "--step", "s1", "--phantom-paths-dir", "/tmp/p"],
        )
        == 0
    )
    out = capsys.readouterr().out
    assert "STATUS=clean" in out
    assert "REASON=" not in out
    assert "PHANTOM_COUNT=" not in out
    assert "PHANTOM_PATHS_FILE=" not in out


def test_check_phantom_dirty_parse_error_emits_unknown(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner()
    monkeypatch.setattr(git, "proc", runner)
    assert git.check_phantom_dirty_main(["--unknown"]) == 0
    out = capsys.readouterr().out
    assert "STATUS=unknown" in out
    assert "REASON=unknown-flag" in out


def test_emit_kv_rejects_multiline_values() -> None:
    with pytest.raises(ValueError, match="newline"):
        git._emit_kv(key="ERROR", value="line1\nline2")  # pyright: ignore[reportPrivateUsage]


def test_snapshot_untracked_usage_does_not_create_output(tmp_path: Path) -> None:
    output = tmp_path / "should-not-exist.z"
    assert git.snapshot_untracked_main(["--unknown", str(output)]) == 0
    assert not output.exists()


def test_phantom_probe_clean_omits_optional_keys(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def _clean_probe(*_args: object, **_kwargs: object) -> phantom.PhantomProbeResult:
        return phantom.PhantomProbeResult(
            dirty=phantom.PhantomDirtyResult(status="clean"),
        )

    monkeypatch.setattr(phantom, "probe_with_warn", _clean_probe)
    assert git.phantom_probe_main(["--step", "s1"]) == 0
    out = capsys.readouterr().out
    assert "PHANTOM_STATUS=clean" in out
    assert "PHANTOM_COUNT=" not in out
    assert "PHANTOM_PATHS_FILE=" not in out


def test_commit_pathspec_file_nul_only_cli_argv(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    pathspec = tmp_path / "paths.z"
    _ = pathspec.write_bytes(b"space name.txt\0")
    runner = RecordingRunner()
    monkeypatch.setattr(git, "proc", runner)
    assert (
        git.commit_main(
            [
                "--only",
                "--pathspec-from-file",
                str(pathspec),
                "--pathspec-file-nul",
                "-m",
                "Commit selected paths",
            ],
        )
        == 0
    )
    assert [
        "git",
        "add",
        f"--pathspec-from-file={pathspec}",
        "--pathspec-file-nul",
    ] in runner.calls
    commit_calls = [call for call in runner.calls if call[:3] == ["git", "commit", "--file"]]
    assert commit_calls
    assert "--only" in commit_calls[0]
    assert f"--pathspec-from-file={pathspec}" in commit_calls[0]
    assert "--pathspec-file-nul" in commit_calls[0]


def test_commit_pathspec_file_nul_only_leaves_unrelated_staged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True, capture_output=True)
    _ = subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    _ = subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)
    _ = (repo / "staged.txt").write_text("base\n", encoding="utf-8")
    _ = (repo / "recovered.txt").write_text("base\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "staged.txt", "recovered.txt"], cwd=repo, check=True)
    _ = subprocess.run(["git", "commit", "-m", "init"], cwd=repo, check=True, capture_output=True)

    _ = (repo / "staged.txt").write_text("pre-existing staged\n", encoding="utf-8")
    _ = subprocess.run(["git", "add", "staged.txt"], cwd=repo, check=True)
    _ = (repo / "recovered.txt").write_text("recovered change\n", encoding="utf-8")
    spaced_dir = repo / "dir with space"
    spaced_dir.mkdir()
    _ = (spaced_dir / "new file.txt").write_text("new recovered\n", encoding="utf-8")

    pathspec = tmp_path / "paths.nul"
    _ = pathspec.write_bytes(b"recovered.txt\0dir with space/new file.txt\0")

    monkeypatch.chdir(repo)
    monkeypatch.setattr(git, "proc", ProcRunner())
    assert (
        git.commit_main(
            [
                "--only",
                "--pathspec-from-file",
                str(pathspec),
                "--pathspec-file-nul",
                "-m",
                "recover exact paths",
            ],
        )
        == 0
    )

    show = subprocess.run(
        ["git", "show", "--name-only", "--format=", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert "recovered.txt" in show
    assert "dir with space/new file.txt" in show
    assert "staged.txt" not in show

    cached = subprocess.run(
        ["git", "diff", "--cached", "--name-only"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.splitlines()
    assert cached == ["staged.txt"]


def test_show_stage_invalid_stage_emits_legacy_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert git.show_stage_main(["--stage", "4", "--file", "conflict.txt"]) == 1
    assert "git-show-stage.sh: --stage must be 1, 2, or 3 (got: 4)" in capsys.readouterr().err


def test_check_main_sync_not_main_cli(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(("git", "symbolic-ref"), 0, "feature\n", "", 0.01),
        ],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.check_main_sync_main([]) == 0
    assert "SYNC_STATUS=not-main" in capsys.readouterr().out


def test_check_remote_branch_parse_error_fail_open(capsys: pytest.CaptureFixture[str]) -> None:
    assert git.check_remote_branch_main([]) == 0
    out = capsys.readouterr().out
    assert "STATE=error" in out
    assert "RC=1" in out
    assert "ERROR=--branch is required" in out


def test_check_remote_branch_unknown_flag_fail_open(capsys: pytest.CaptureFixture[str]) -> None:
    assert git.check_remote_branch_main(["--bogus"]) == 0
    out = capsys.readouterr().out
    assert "STATE=error" in out
    assert "RC=1" in out
    assert "ERROR=unknown flag: --bogus" in out


def test_rebase_abort_main_idempotent_on_failed_abort(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    runner = RecordingRunner(
        responses=[
            CommandResult(
                ("git", "rebase", "--abort"),
                128,
                "",
                "fatal: no rebase in progress\n",
                0.01,
            ),
        ],
    )
    monkeypatch.setattr(git, "proc", runner)
    assert git.rebase_abort_main([]) == 0


def test_remote_branch_state_present() -> None:
    runner = StubRunner(
        {
            ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"): CommandResult(
                ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"),
                0,
                "abc\trefs/heads/feat\n",
                "",
                0.01,
            ),
        },
    )
    result = git.remote_branch_state(runner, "feat")
    assert result.state == "present"
    assert result.rc == 0


def test_remote_branch_state_absent() -> None:
    runner = StubRunner(
        {
            ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"): CommandResult(
                ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"),
                2,
                "",
                "",
                0.01,
            ),
        },
    )
    result = git.remote_branch_state(runner, "feat")
    assert result.state == "absent"
    assert result.rc == 2


def test_remote_branch_state_transport_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(git, "with_transient_retry", _immediate_retry)
    runner = StubRunner(
        {
            ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"): CommandResult(
                ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"),
                128,
                "",
                "fatal: auth failed\n",
                0.01,
            ),
        },
    )
    result = git.remote_branch_state(runner, "feat")
    assert result.state == "error"
    assert result.rc == 128
    assert result.error
    assert "\n" not in result.error


def test_check_remote_branch_main_present_absent_error(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(git, "with_transient_retry", _immediate_retry)
    cases = [
        (0, "present", 0, ""),
        (2, "absent", 2, ""),
        (128, "error", 128, "fatal: network"),
    ]
    for rc, state, expected_rc, stderr in cases:
        runner = RecordingRunner(
            responses=[
                CommandResult(
                    ("git", "ls-remote", "--exit-code", "--heads", "origin", "feat"),
                    rc,
                    "abc\trefs/heads/feat\n" if rc == 0 else "",
                    stderr,
                    0.01,
                ),
            ],
        )
        monkeypatch.setattr(git, "proc", runner)
        assert git.check_remote_branch_main(["--branch", "feat"]) == 0
        out = capsys.readouterr().out
        assert f"STATE={state}" in out
        assert f"RC={expected_rc}" in out
        if state == "error":
            assert "ERROR=" in out
