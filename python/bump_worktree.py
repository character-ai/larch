"""Shared drop/worktree helpers for version bump and changelog (no orchestration)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import git
from proc import Runner


@dataclass(frozen=True)
class DropResult:
    dropped: bool
    old_sha: str = ""
    error: str = ""


def porcelain_tracked_only(runner: Runner, *, cwd: str | None) -> list[str] | None:
    """Return tracked porcelain lines, or None when git status fails."""
    result = git.status_porcelain(runner, untracked_files="no", cwd=cwd)
    if result.returncode != 0:
        return None
    return [line for line in result.stdout.splitlines() if line]


def sorted_changed_files(
    runner: Runner,
    parent: str,
    child: str,
    *,
    cwd: str | None,
) -> str:
    result = git.diff_name_only(runner, parent, child, cwd=cwd)
    if result.returncode != 0:
        return ""
    files = result.stdout.splitlines()
    files = [f for f in files if f]
    files.sort(key=lambda s: s.encode("utf-8"))
    return "\n".join(files)


def find_commit_depth(
    runner: Runner,
    *,
    max_depth: int,
    subject_matches: Callable[[str], bool],
    cwd: str | None = None,
) -> int:
    """Return depth of the newest commit whose subject matches, or -1."""
    for depth in range(max_depth):
        ref = f"HEAD~{depth}"
        if git.try_rev_parse(runner, ref, cwd=cwd) is None:
            break
        subject = git.log_subject(runner, ref, cwd=cwd)
        if subject_matches(subject):
            return depth
    return -1


def find_subject_commit_depth(
    runner: Runner,
    *,
    max_depth: int,
    subject: str,
    cwd: str | None = None,
) -> int:
    """Return depth of the newest commit matching subject, or -1."""
    return find_commit_depth(
        runner,
        max_depth=max_depth,
        subject_matches=lambda logged: logged == subject,
        cwd=cwd,
    )


def drop_replay_commit(
    runner: Runner,
    *,
    found_at: int,
    cwd: str | None = None,
    reset_error: str = "reset failed",
    rebase_error: str = "rebase failed",
) -> str | None:
    """Replay history without HEAD~found_at. Return an error message or None on success."""
    if found_at == 0:
        reset = git.reset(runner, "--hard", "HEAD~1", cwd=cwd)
        if reset.returncode != 0:
            return reset_error
        return None

    rebase = git.rebase_onto(
        runner,
        f"HEAD~{found_at + 1}",
        f"HEAD~{found_at}",
        cwd=cwd,
    )
    if rebase.returncode != 0:
        abort = git.rebase(runner, "--abort", cwd=cwd)
        if abort.returncode != 0:
            return (
                f"{rebase_error}; rebase --abort failed "
                "(repository stuck mid-rebase; run git rebase --abort manually)"
            )
        return rebase_error
    return None
