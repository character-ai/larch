"""Typed git operations over an injected proc.Runner."""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path
from dataclasses import dataclass

import config
from errors import ShipError
from proc import CommandResult, Runner

_GIT_REF_LABEL_RE = re.compile(r"^[A-Za-z0-9._/-]+$")


def validate_base_remote_ref(base_remote: str, base_ref: str) -> str | None:
    """Return an error message when base labels are unsafe for git argv."""
    if not _GIT_REF_LABEL_RE.fullmatch(base_remote):
        return "base_remote contains unsupported characters"
    if not _GIT_REF_LABEL_RE.fullmatch(base_ref):
        return "base_ref contains unsupported characters"
    return None


@dataclass(frozen=True)
class GitStatus:
    porcelain: str


@dataclass(frozen=True)
class LogSubjects:
    subjects: tuple[str, ...]


def _run(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
) -> CommandResult:
    if env is None:
        env = _git_subprocess_env()
    return runner.run(list(argv), cwd=cwd, env=env)


def _ensure_success(result: CommandResult) -> CommandResult:
    if result.returncode != 0:
        msg = f"git command failed ({result.returncode}): {' '.join(result.argv)}"
        raise ShipError(msg)
    return result


def rev_parse(runner: Runner, ref: str, *, cwd: str | None = None) -> str:
    result = _ensure_success(_run(runner, ["git", "rev-parse", ref], cwd=cwd))
    return result.stdout.strip()


def current_branch(runner: Runner, *, cwd: str | None = None) -> str:
    result = _ensure_success(_run(
        runner,
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=cwd,
    ))
    return result.stdout.strip()


def branch(runner: Runner, name: str, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "branch", name], cwd=cwd)


def branch_force(
    runner: Runner,
    name: str,
    start_point: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "branch", "-f", name, start_point], cwd=cwd)


def rev_count(
    runner: Runner,
    left: str,
    right: str,
    *,
    cwd: str | None = None,
) -> int:
    result = _ensure_success(_run(
        runner,
        ["git", "rev-list", "--count", f"{left}..{right}"],
        cwd=cwd,
    ))
    text = result.stdout.strip() or "0"
    try:
        return int(text)
    except ValueError as exc:
        msg = f"git rev-list --count returned non-integer stdout: {text!r}"
        raise ShipError(msg) from exc


def merge_base(
    runner: Runner,
    left: str,
    right: str,
    *,
    cwd: str | None = None,
) -> str:
    result = _ensure_success(_run(runner, ["git", "merge-base", left, right], cwd=cwd))
    return result.stdout.strip()


def rebase(
    runner: Runner,
    onto: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "rebase", onto], cwd=cwd)


def push(
    runner: Runner,
    remote: str,
    refspec: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "push", remote, refspec], cwd=cwd)


def force_push_with_lease(
    runner: Runner,
    remote: str,
    refspec: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(
        runner,
        ["git", "push", "--force-with-lease", remote, refspec],
        cwd=cwd,
    )


def reset(
    runner: Runner,
    mode: str,
    ref: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "reset", mode, ref], cwd=cwd)


def status(runner: Runner, *, cwd: str | None = None) -> GitStatus:
    result = _ensure_success(_run(runner, ["git", "status", "--porcelain"], cwd=cwd))
    return GitStatus(porcelain=result.stdout)


def log_subjects(
    runner: Runner,
    rev_range: str,
    *,
    cwd: str | None = None,
) -> LogSubjects:
    result = _ensure_success(_run(
        runner,
        ["git", "log", "--format=%s", rev_range],
        cwd=cwd,
    ))
    lines = tuple(line for line in result.stdout.splitlines() if line)
    return LogSubjects(subjects=lines)


def ls_files(
    runner: Runner,
    *paths: str,
    cwd: str | None = None,
) -> tuple[str, ...]:
    argv = ["git", "ls-files", *paths]
    result = _ensure_success(_run(runner, argv, cwd=cwd))
    return tuple(line for line in result.stdout.splitlines() if line)


def fetch(
    runner: Runner,
    remote: str,
    ref: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "fetch", remote, ref, "--quiet"], cwd=cwd)


def show_file(
    runner: Runner,
    spec: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "show", spec], cwd=cwd)


def commit(
    runner: Runner,
    message: str,
    *,
    only: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "commit", "-m", message]
    if only is not None:
        argv.extend(["--only", only])
    return _run(runner, argv, cwd=cwd)


def commit_with_trailer(
    runner: Runner,
    message: str,
    *,
    only: str | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Commit via temp file + interpret-trailers (parity with scripts/git-commit.sh)."""
    trailer = config.GIT_COMMIT_CO_AUTHORED_BY_TRAILER
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        delete=False,
    ) as handle:
        _ = handle.write(f"{message}\n")
        tmp_path = handle.name
    try:
        trailer_result = _run(
            runner,
            [
                "git",
                "interpret-trailers",
                "--in-place",
                "--if-exists",
                "addIfDifferent",
                "--if-missing",
                "add",
                "--trailer",
                trailer,
                tmp_path,
            ],
            cwd=cwd,
        )
        if trailer_result.returncode != 0:
            return trailer_result
        argv = ["git", "commit", "--file", tmp_path]
        if only is not None:
            argv.extend(["--only", only])
        return _run(runner, argv, cwd=cwd)
    finally:
        Path(tmp_path).unlink()


def add(runner: Runner, path: str, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "add", path], cwd=cwd)


def diff_name_status(
    runner: Runner,
    base: str,
    head: str,
    *,
    paths: Sequence[str] = (),
    find_renames: bool = False,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "diff"]
    if find_renames:
        argv.append("-M")
    argv.extend(["--name-status", base, head, "--", *paths])
    return _run(runner, argv, cwd=cwd)


def diff_name_only(
    runner: Runner,
    base: str,
    head: str,
    *,
    paths: Sequence[str] = (),
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "diff", "--name-only", base, head]
    if paths:
        argv.extend(["--", *paths])
    return _run(runner, argv, cwd=cwd)


def diff_tree_name_only(
    runner: Runner,
    ref: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(
        runner,
        ["git", "diff-tree", "--no-commit-id", "--name-only", "-r", ref],
        cwd=cwd,
    )


def _git_subprocess_env() -> dict[str, str]:
    """Minimal env for git helpers; drop GIT_DIR/GIT_WORK_TREE overrides."""
    env = {
        key: value
        for key, value in os.environ.items()
        if key not in ("GIT_DIR", "GIT_WORK_TREE")
    }
    env["GIT_SEQUENCE_EDITOR"] = "true"
    env["GIT_EDITOR"] = "true"
    return env


def try_current_branch(runner: Runner, *, cwd: str | None = None) -> str | None:
    result = _run(
        runner,
        ["git", "symbolic-ref", "--short", "HEAD"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def unmerged_paths(runner: Runner, *, cwd: str | None = None) -> list[str]:
    result = _ensure_success(_run(
        runner,
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=cwd,
    ))
    return [line for line in result.stdout.splitlines() if line]


def checkout_ours(
    runner: Runner,
    *paths: str,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "checkout", "--ours", "--", *paths]
    return _run(runner, argv, cwd=cwd)


def is_ancestor(
    runner: Runner,
    ancestor: str,
    descendant: str,
    *,
    cwd: str | None = None,
) -> bool:
    result = _run(
        runner,
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=cwd,
    )
    return result.returncode == 0


def rebase_continue(runner: Runner, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "rebase", "--continue"], cwd=cwd)


def rebase_skip(runner: Runner, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "rebase", "--skip"], cwd=cwd)


def force_push_with_lease_expecting(
    runner: Runner,
    remote: str,
    refspec: str,
    expected_oid: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    lease = f"{refspec}:{expected_oid}"
    return _run(
        runner,
        ["git", "push", f"--force-with-lease={lease}", remote],
        cwd=cwd,
    )


def rebase_onto(
    runner: Runner,
    newbase: str,
    upstream: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(
        runner,
        ["git", "rebase", "--onto", newbase, upstream],
        cwd=cwd,
    )


def rev_list_count(
    runner: Runner,
    rev_range: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "rev-list", "--count", rev_range], cwd=cwd)


def status_porcelain(
    runner: Runner,
    *,
    untracked_files: str = "all",
    cwd: str | None = None,
) -> CommandResult:
    return _run(
        runner,
        ["git", "status", "--porcelain", f"--untracked-files={untracked_files}"],
        cwd=cwd,
    )


def try_rev_parse(runner: Runner, ref: str, *, cwd: str | None = None) -> str | None:
    result = _run(runner, ["git", "rev-parse", ref], cwd=cwd)
    if result.returncode != 0:
        return None
    return result.stdout.strip()


def try_merge_base(
    runner: Runner,
    left: str,
    right: str,
    *,
    cwd: str | None = None,
) -> str | None:
    result = _run(runner, ["git", "merge-base", left, right], cwd=cwd)
    if result.returncode != 0:
        return None
    text = result.stdout.strip()
    return text or None


def log_subject(
    runner: Runner,
    ref: str,
    *,
    cwd: str | None = None,
) -> str:
    result = _run(runner, ["git", "log", "-1", "--format=%s", ref], cwd=cwd)
    if result.returncode != 0:
        return ""
    return result.stdout.strip()


def unstage(runner: Runner, path: str, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "reset", "HEAD", path], cwd=cwd)


def diff_quiet(
    runner: Runner,
    path: str,
    *,
    cached: bool = False,
    cwd: str | None = None,
) -> bool:
    """Return True when path has no working-tree or index diff."""
    argv = ["git", "diff", "--quiet", "--", path]
    if cached:
        argv = ["git", "diff", "--cached", "--quiet", "--", path]
    result = _run(runner, argv, cwd=cwd)
    return result.returncode == 0


def tracked_dirty_paths(runner: Runner, *, cwd: str | None = None) -> frozenset[str]:
    """Paths with tracked worktree/index changes vs HEAD (``git diff --name-only HEAD``)."""
    result = _run(runner, ["git", "diff", "--name-only", "HEAD"], cwd=cwd)
    return frozenset(line for line in result.stdout.splitlines() if line)


def untracked_dirty_paths(runner: Runner, *, cwd: str | None = None) -> frozenset[str]:
    """Untracked paths not ignored (``git ls-files --others --exclude-standard``)."""
    result = _run(
        runner,
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=cwd,
    )
    return frozenset(line for line in result.stdout.splitlines() if line)


def restore_staged(runner: Runner, path: str, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "restore", "--staged", "--", path], cwd=cwd)


def checkout_paths(runner: Runner, path: str, *, cwd: str | None = None) -> CommandResult:
    return _run(runner, ["git", "checkout", "--", path], cwd=cwd)


def paths_delta_revert(
    runner: Runner,
    baseline_tracked: frozenset[str],
    baseline_untracked: frozenset[str],
    *,
    cwd: str | None = None,
) -> None:
    """Revert tracked/untracked deltas since baseline (recovery waterfall parity)."""
    cur_tracked = tracked_dirty_paths(runner, cwd=cwd)
    cur_untracked = untracked_dirty_paths(runner, cwd=cwd)
    root = Path(cwd) if cwd else Path.cwd()
    for path in cur_tracked:
        if path in baseline_tracked:
            continue
        if path in cur_untracked:
            target = root / path
            if target.exists() or target.is_symlink():
                target.unlink(missing_ok=True)
        else:
            _ = restore_staged(runner, path, cwd=cwd)
            _ = checkout_paths(runner, path, cwd=cwd)
    for path in cur_untracked:
        if path in baseline_untracked:
            continue
        target = root / path
        if target.exists() or target.is_symlink():
            target.unlink(missing_ok=True)
