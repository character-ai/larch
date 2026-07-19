"""Unit tests for git.py using a stub Runner."""

from __future__ import annotations

import subprocess
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from larch.git import git
from larch.core import logging_util
from larch.core import retry
from larch.errors import ShipError
from larch.core.proc import CommandResult, ProcRunner
from test_support import RecordingRunner
from tests.support.foundation import make_adverse_push_repo


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


def test_add_refuses_forbidden_original_branch(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "BRANCH_NAME=feat/x\nORIGINAL_BRANCH_FORBIDDEN=true\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("SHIP_PR_STATE_FILE", str(state_file))
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"),
                0,
                "feat/x\n",
                "",
                0.01,
            ),
        },
    )

    with pytest.raises(ShipError, match="forbidden original branch"):
        _ = git.add(runner, "file.txt")


def test_add_refuses_forbidden_original_branch_via_implement_tmpdir(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "BRANCH_NAME=feat/x\nORIGINAL_BRANCH_FORBIDDEN=true\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("SHIP_PR_STATE_FILE", raising=False)
    monkeypatch.setenv("IMPLEMENT_TMPDIR", str(tmp_path))
    runner = StubRunner(
        {
            ("git", "symbolic-ref", "--short", "HEAD"): CommandResult(
                ("git", "symbolic-ref", "--short", "HEAD"),
                0,
                "feat/x\n",
                "",
                0.01,
            ),
        },
    )

    with pytest.raises(ShipError, match="forbidden original branch"):
        _ = git.add(runner, "file.txt")


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


def test_log_path_commits_parses_path_history() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner(
        {
            argv: CommandResult(
                argv,
                0,
                "abc123\x00Initial baseline\n"
                "def456\x00Shrink panel tier (#5978)\n",
                "",
                0.01,
            ),
        },
    )

    commits = git.log_path_commits(runner, "python/skill-closure-baseline.json")

    assert commits == (
        git.PathCommit(sha="abc123", subject="Initial baseline"),
        git.PathCommit(sha="def456", subject="Shrink panel tier (#5978)"),
    )


def test_log_path_commits_preserves_embedded_nul_in_subject() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner(
        {
            argv: CommandResult(
                argv,
                0,
                "abc123\x00Subject with \x00 embedded nul\n",
                "",
                0.01,
            ),
        },
    )

    commits = git.log_path_commits(runner, "python/skill-closure-baseline.json")

    assert commits == (
        git.PathCommit(sha="abc123", subject="Subject with \x00 embedded nul"),
    )


def test_log_path_commits_includes_rev_range_before_path() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "v1.0.0..HEAD",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner({argv: CommandResult(argv, 0, "", "", 0.01)})

    commits = git.log_path_commits(
        runner,
        "python/skill-closure-baseline.json",
        rev_range="v1.0.0..HEAD",
    )

    assert not commits


def test_log_path_commits_raises_on_malformed_output() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner({argv: CommandResult(argv, 0, "missing-delimiter\n", "", 0.01)})

    with pytest.raises(ShipError, match="malformed line"):
        _ = git.log_path_commits(runner, "python/skill-closure-baseline.json")


def test_log_path_commits_raises_on_empty_sha() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner(
        {argv: CommandResult(argv, 0, "\x00Subject only\n", "", 0.01)},
    )

    with pytest.raises(ShipError, match="malformed line"):
        _ = git.log_path_commits(runner, "python/skill-closure-baseline.json")


def test_log_path_commits_raises_on_git_failure() -> None:
    argv = (
        "git",
        "log",
        "--reverse",
        "--format=%H%x00%s",
        "--",
        "python/skill-closure-baseline.json",
    )
    runner = StubRunner({argv: CommandResult(argv, 128, "", "fatal", 0.01)})

    with pytest.raises(ShipError, match="git command failed"):
        _ = git.log_path_commits(runner, "python/skill-closure-baseline.json")


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
    runner = RecordingRunner()

    _ = git.rebase_continue(runner)
    env = dict(runner.records[-1].env or {})
    assert env.get("GIT_SEQUENCE_EDITOR") == "true"
    assert env.get("GIT_EDITOR") == "true"


def test_force_push_with_lease_expecting_argv() -> None:
    runner = StubRunner(
        {
            (
                "git",
                "push",
                "--force-with-lease=refs/heads/feat:abc123",
                "origin",
                "refs/heads/feat:refs/heads/feat",
            ): CommandResult(
                (
                    "git",
                    "push",
                    "--force-with-lease=refs/heads/feat:abc123",
                    "origin",
                    "refs/heads/feat:refs/heads/feat",
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


def _run_adverse_git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _make_adverse_push_repo(tmp_path: Path) -> tuple[Path, Path, str, str]:
    return make_adverse_push_repo(tmp_path)


def test_force_push_with_lease_expecting_ignores_adverse_tracking(tmp_path: Path) -> None:
    repo, origin, expected_oid, main_before = _make_adverse_push_repo(tmp_path)

    result = git.force_push_with_lease_expecting(
        ProcRunner(),
        "origin",
        "refs/heads/feature-x",
        expected_oid,
        cwd=str(repo),
    )

    assert result.returncode == 0
    assert _run_adverse_git(origin, "rev-parse", "refs/heads/feature-x") == _run_adverse_git(repo, "rev-parse", "HEAD")
    assert _run_adverse_git(origin, "rev-parse", "refs/heads/main") == main_before


def test_force_push_recovery_ignores_adverse_tracking(tmp_path: Path) -> None:
    repo, origin, expected_oid, main_before = _make_adverse_push_repo(tmp_path)

    result = git.force_push_recovery(
        ProcRunner(),
        branch="feature-x",
        expected_remote_oid=expected_oid,
        cwd=str(repo),
        sleeper=lambda _seconds: None,
    )

    assert result.pushed
    assert result.status == "pushed"
    assert _run_adverse_git(origin, "rev-parse", "refs/heads/feature-x") == _run_adverse_git(repo, "rev-parse", "HEAD")
    assert _run_adverse_git(origin, "rev-parse", "refs/heads/main") == main_before


def test_rebase_onto_strips_git_dir_override(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GIT_DIR", "/evil")
    monkeypatch.setenv("GIT_WORK_TREE", "/evil")
    runner = RecordingRunner()

    _ = git.rebase_onto(runner, "HEAD~2", "HEAD~1")
    env = dict(runner.records[-1].env or {})
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



def test_emit_kv_rejects_multiline_values() -> None:

    with pytest.raises(ValueError, match="newline"):
        logging_util.emit_kv(key="ERROR", value="line1\nline2")



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
