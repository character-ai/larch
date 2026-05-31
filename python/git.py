"""Typed git operations over an injected proc.Runner."""

from __future__ import annotations

import os
from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from errors import ShipError
from proc import CommandResult, Runner


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


def rebase_onto(
    runner: Runner,
    newbase: str,
    upstream: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    env = {**os.environ, "GIT_SEQUENCE_EDITOR": "true"}
    return _run(
        runner,
        ["git", "rebase", "--onto", newbase, upstream],
        cwd=cwd,
        env=env,
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
