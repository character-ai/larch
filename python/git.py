# pyright: reportUnusedCallResult=false
"""Typed git operations over an injected proc.Runner."""

from __future__ import annotations

import os
import re
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from dataclasses import dataclass

import argparse
import sys
import config
import redact
from errors import ShipError
from proc import CommandResult, Runner
from retry import with_transient_retry
import logging_util
import phantom
import proc

_GIT_REF_LABEL_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_GIT_STAGE_BASE = 1
_GIT_STAGE_OURS = 2
_GIT_STAGE_THEIRS = 3


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


def try_log_subjects(
    runner: Runner,
    rev_range: str,
    *,
    cwd: str | None = None,
) -> LogSubjects:
    """Non-throwing log subjects (merge flush recovery parity with merge-pr.sh)."""
    result = _run(runner, ["git", "log", "--format=%s", rev_range], cwd=cwd)
    if result.returncode != 0:
        return LogSubjects(subjects=())
    lines = tuple(line for line in result.stdout.splitlines() if line)
    return LogSubjects(subjects=lines)


def status_porcelain_paths(
    runner: Runner,
    path: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "status", "--porcelain", "--", path], cwd=cwd)


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
    only: bool = False,
    paths: Sequence[str] = (),
    pathspec_from_file: str | None = None,
    pathspec_file_nul: bool = False,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "commit", "-m", message]
    if only:
        argv.append("--only")
    if pathspec_from_file is not None:
        argv.append(f"--pathspec-from-file={pathspec_from_file}")
        if pathspec_file_nul:
            argv.append("--pathspec-file-nul")
    elif paths:
        argv.extend(["--", *paths])
    return _run(runner, argv, cwd=cwd)


def commit_with_trailer(
    runner: Runner,
    message: str,
    *,
    only: bool = False,
    no_trailer: bool = False,
    paths: Sequence[str] = (),
    pathspec_from_file: str | None = None,
    pathspec_file_nul: bool = False,
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
        if not no_trailer:
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
        if only:
            argv.append("--only")
        if pathspec_from_file is not None:
            argv.append(f"--pathspec-from-file={pathspec_from_file}")
            if pathspec_file_nul:
                argv.append("--pathspec-file-nul")
        elif paths:
            argv.extend(["--", *paths])
        return _run(runner, argv, cwd=cwd)
    finally:
        Path(tmp_path).unlink()


def add(runner: Runner, *paths: str, cwd: str | None = None) -> CommandResult:
    argv = ["git", "add"]
    if paths:
        argv.extend(["--", *paths])
    return _run(runner, argv, cwd=cwd)


def add_pathspec_file(
    runner: Runner,
    pathspec_from_file: str,
    *,
    pathspec_file_nul: bool = False,
    cwd: str | None = None,
) -> CommandResult:
    argv = ["git", "add", f"--pathspec-from-file={pathspec_from_file}"]
    if pathspec_file_nul:
        argv.append("--pathspec-file-nul")
    return _run(runner, argv, cwd=cwd)


def amend_add(
    runner: Runner,
    paths: Sequence[str],
    *,
    cwd: str | None = None,
) -> CommandResult:
    if not paths:
        return CommandResult(("git", "amend-add"), 1, "", "at least one file argument is required\n", 0.0)
    staged = add(runner, *paths, cwd=cwd)
    if staged.returncode != 0:
        return staged
    return _run(runner, ["git", "commit", "--amend", "--no-edit"], cwd=cwd)


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


def try_unmerged_paths(runner: Runner, *, cwd: str | None = None) -> list[str]:
    """Non-raising unmerged-path probe (rebase-push.sh / conflict CLI parity)."""
    result = _run(
        runner,
        ["git", "diff", "--name-only", "--diff-filter=U"],
        cwd=cwd,
    )
    if result.returncode != 0:
        return []
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


def local_branch_exists(runner: Runner, branch: str, *, cwd: str | None = None) -> bool:
    """True when ``refs/heads/<branch>`` exists (tags/remotes do not match)."""
    result = _run(
        runner,
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=cwd,
    )
    return result.returncode == 0


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


@dataclass(frozen=True)
class ForcePushResult:
    pushed: bool
    status: str
    branch: str = ""


def push_set_upstream(
    runner: Runner,
    remote: str,
    refspec: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "push", "-u", remote, refspec], cwd=cwd)


def force_push_recovery(
    runner: Runner,
    *,
    branch: str | None = None,
    remote: str = "origin",
    expected_remote_oid: str | None = None,
    cwd: str | None = None,
    sleeper: Callable[[float], None] | None = None,
) -> ForcePushResult:
    """Port git-force-push.sh: clean-tree guard, fetch, lease push, race noop, one retry."""
    if sleeper is None:
        sleeper = time.sleep

    head_branch = try_current_branch(runner, cwd=cwd)
    if not head_branch:
        return ForcePushResult(pushed=False, status="detached_head", branch="")
    if branch is not None and branch != head_branch:
        return ForcePushResult(
            pushed=False,
            status="branch_mismatch",
            branch=head_branch,
        )
    resolved_branch = head_branch

    status_result = status_porcelain(runner, cwd=cwd)
    if status_result.returncode != 0:
        return ForcePushResult(
            pushed=False,
            status="status_failed",
            branch=resolved_branch,
        )
    if status_result.stdout.strip():
        return ForcePushResult(
            pushed=False,
            status="dirty_worktree",
            branch=resolved_branch,
        )

    refspec = f"HEAD:refs/heads/{resolved_branch}"

    def _lease_push() -> CommandResult:
        if expected_remote_oid:
            lease = f"refs/heads/{resolved_branch}:{expected_remote_oid}"
            return _run(
                runner,
                ["git", "push", f"--force-with-lease={lease}", remote],
                cwd=cwd,
            )
        return force_push_with_lease(runner, remote, refspec, cwd=cwd)

    _ = fetch(runner, remote, resolved_branch, cwd=cwd)
    first = _lease_push()
    if first.returncode == 0:
        return ForcePushResult(pushed=True, status="pushed", branch=resolved_branch)

    _ = fetch(runner, remote, resolved_branch, cwd=cwd)
    local_head = try_rev_parse(runner, "HEAD", cwd=cwd)
    remote_ref = try_rev_parse(runner, f"{remote}/{resolved_branch}", cwd=cwd)
    if local_head and remote_ref and local_head == remote_ref:
        return ForcePushResult(pushed=True, status="noop_same_ref", branch=resolved_branch)

    sleeper(5.0)
    second = _lease_push()
    if second.returncode == 0:
        return ForcePushResult(pushed=True, status="pushed", branch=resolved_branch)
    return ForcePushResult(
        pushed=False,
        status="diverged_retry_failed",
        branch=resolved_branch,
    )


@dataclass(frozen=True)
class BranchInfo:
    head_sha: str
    current_branch: str


@dataclass(frozen=True)
class ConflictFile:
    path: str
    stage_1: bool
    stage_2: bool
    stage_3: bool


@dataclass(frozen=True)
class CleanTreeResult:
    clean: str
    dirty_out: str = ""
    probe_error: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class CountCommitsResult:
    count: int
    status: str


@dataclass(frozen=True)
class MainSyncResult:
    status: str
    ahead_count: int | None = None
    error: str = ""
    exit_code: int = 0


@dataclass(frozen=True)
class RemoteBranchState:
    state: str
    rc: int
    error: str = ""


def branch_info(runner: Runner, *, cwd: str | None = None) -> BranchInfo | None:
    head = _run(runner, ["git", "rev-parse", "--short", "HEAD"], cwd=cwd)
    if head.returncode != 0:
        return None
    branch_res = _run(runner, ["git", "branch", "--show-current"], cwd=cwd)
    branch_name = branch_res.stdout.strip() if branch_res.returncode == 0 else ""
    return BranchInfo(head_sha=head.stdout.strip(), current_branch=branch_name)


def _parse_conflict_file_rows(stdout: str) -> tuple[ConflictFile, ...]:
    order: list[str] = []
    stages: dict[str, set[int]] = {}
    for line in stdout.splitlines():
        if "\t" not in line:
            continue
        meta, path = line.split("\t", 1)
        parts = meta.split()
        if not parts:
            continue
        try:
            stage = int(parts[-1])
        except ValueError:
            continue
        if path not in stages:
            order.append(path)
            stages[path] = set()
        stages[path].add(stage)
    return tuple(
        ConflictFile(
            path,
            _GIT_STAGE_BASE in stages[path],
            _GIT_STAGE_OURS in stages[path],
            _GIT_STAGE_THEIRS in stages[path],
        )
        for path in order
    )


def conflict_files(runner: Runner, *, cwd: str | None = None) -> tuple[ConflictFile, ...]:
    result = _ensure_success(_run(runner, ["git", "ls-files", "-u"], cwd=cwd))
    return _parse_conflict_file_rows(result.stdout)


def try_conflict_files(runner: Runner, *, cwd: str | None = None) -> tuple[ConflictFile, ...]:
    """Non-raising conflict-file probe (git-conflict-files.sh parity)."""
    result = _run(runner, ["git", "ls-files", "-u"], cwd=cwd)
    if result.returncode != 0:
        return ()
    return _parse_conflict_file_rows(result.stdout)


def resolve_branch_push_remote(
    runner: Runner,
    branch: str,
    *,
    cwd: str | None = None,
) -> str:
    """Resolve topic-branch push remote (rebase-push.sh parity)."""
    for key in (f"branch.{branch}.pushRemote", f"branch.{branch}.remote"):
        result = _run(runner, ["git", "config", "--get", key], cwd=cwd)
        if result.returncode == 0:
            candidate = result.stdout.strip()
            if candidate and _GIT_REF_LABEL_RE.fullmatch(candidate):
                return candidate
    return "origin"


def rebase_in_progress(runner: Runner, *, cwd: str | None = None) -> bool:
    """True when git reports an active rebase (rebase-push.sh --continue guard)."""
    git_dir = _run(runner, ["git", "rev-parse", "--git-dir"], cwd=cwd)
    if git_dir.returncode != 0:
        return False
    rel = git_dir.stdout.strip()
    if not rel:
        return False
    base = Path(rel)
    if not base.is_absolute():
        base = Path(cwd) / base if cwd else Path.cwd() / base
    return (base / "rebase-merge").is_dir() or (base / "rebase-apply").is_dir()


def rebase_abort(runner: Runner, *, cwd: str | None = None) -> CommandResult:
    result = _run(runner, ["git", "rebase", "--abort"], cwd=cwd)
    if result.returncode == 0:
        return result
    return CommandResult(tuple(result.argv), 0, result.stdout, result.stderr, result.duration)


def sync_local_main(
    runner: Runner,
    *,
    base_remote: str = "origin",
    base_ref: str = "main",
    cwd: str | None = None,
) -> tuple[str, int]:
    current = try_current_branch(runner, cwd=cwd) or ""
    if current == "main":
        return "refusing to update local 'main' while checked out on main", 1
    if try_rev_parse(runner, "main", cwd=cwd) is None:
        return "absent", 0
    base_target = f"{base_remote}/{base_ref}"
    local_main = try_rev_parse(runner, "main", cwd=cwd)
    remote_main = try_rev_parse(runner, base_target, cwd=cwd)
    if local_main and remote_main and local_main == remote_main:
        return "already_current", 0
    updated = branch_force(runner, "main", base_target, cwd=cwd)
    if updated.returncode != 0:
        return "failed", 1
    return "updated", 0


def _one_line_summary(text: str) -> str:
    return text.replace("\n", " ").replace("\r", " ").replace("\t", " ")[:256]


def clean_tree(
    runner: Runner,
    *,
    fail_closed: bool = False,
    cwd: str | None = None,
) -> CleanTreeResult:
    result = _run(runner, ["git", "status", "--porcelain"], cwd=cwd)
    if result.returncode != 0:
        summary = _one_line_summary(result.stdout + result.stderr)
        if fail_closed:
            return CleanTreeResult(
                clean="unknown",
                probe_error=f"git exited {result.returncode} ({summary})",
                exit_code=1,
            )
        return CleanTreeResult(clean="true")
    if result.stdout:
        return CleanTreeResult(clean="false", dirty_out=_one_line_summary(result.stdout))
    return CleanTreeResult(clean="true")


def snapshot_untracked(
    runner: Runner,
    output: str,
    *,
    nul: bool = False,
    cwd: str | None = None,
) -> int:
    argv = ["git", "ls-files", "--others", "--exclude-standard"]
    if nul:
        argv.append("-z")
    result = _run(runner, argv, cwd=cwd)
    output_path = Path(output)
    tmp_path = Path(f"{output}.tmp")
    try:
        if result.returncode != 0:
            output_path.unlink(missing_ok=True)
            tmp_path.unlink(missing_ok=True)
            return 0
        if nul:
            parts = [p for p in result.stdout.split("\x00") if p]
            data = "\x00".join(sorted(parts))
            if data:
                data += "\x00"
        else:
            parts = [p for p in result.stdout.splitlines() if p]
            data = "\n".join(sorted(parts))
            if data:
                data += "\n"
        _ = tmp_path.write_text(data, encoding="utf-8")
        _ = tmp_path.replace(output_path)
    except OSError:
        output_path.unlink(missing_ok=True)
        tmp_path.unlink(missing_ok=True)
    return 0


def count_commits(runner: Runner, *, cwd: str | None = None) -> CountCommitsResult:
    base_ref = ""
    if _run(runner, ["git", "rev-parse", "--verify", "main"], cwd=cwd).returncode == 0:
        base_ref = "main"
    elif _run(runner, ["git", "rev-parse", "--verify", "origin/main"], cwd=cwd).returncode == 0:
        base_ref = "origin/main"
    if not base_ref:
        return CountCommitsResult(count=0, status="missing_main_ref")
    result = _run(runner, ["git", "rev-list", f"{base_ref}..HEAD", "--count"], cwd=cwd)
    if result.returncode != 0:
        return CountCommitsResult(count=0, status="git_error")
    text = result.stdout.strip()
    if not text.isdigit():
        return CountCommitsResult(count=0, status="git_error")
    return CountCommitsResult(count=int(text), status="ok")


def check_main_sync(runner: Runner, *, cwd: str | None = None) -> MainSyncResult:
    current = try_current_branch(runner, cwd=cwd) or ""
    if current != "main":
        return MainSyncResult(status="not-main")
    ahead_result = _run(runner, ["git", "rev-list", "--count", "origin/main..HEAD"], cwd=cwd)
    if ahead_result.returncode != 0 or not ahead_result.stdout.strip():
        return MainSyncResult(
            status="probe-error",
            error=f"git rev-list failed or produced empty output (exit {ahead_result.returncode})",
            exit_code=2,
        )
    ahead_text = ahead_result.stdout.strip()
    ahead = int(ahead_text) if ahead_text.isdigit() else 0
    if ahead == 0:
        return MainSyncResult(status="ok", ahead_count=0)
    log = _run(runner, ["git", "log", "origin/main..HEAD", "--format=%s"], cwd=cwd)
    if log.returncode != 0:
        return MainSyncResult(status="probe-error", ahead_count=ahead, error=f"git log failed (exit {log.returncode})", exit_code=2)
    subjects = [line for line in log.stdout.splitlines() if line]
    if len(subjects) != ahead:
        return MainSyncResult(
            status="probe-error",
            ahead_count=ahead,
            error=f"git log subject line count ({len(subjects)}) does not match AHEAD ({ahead})",
            exit_code=2,
        )
    all_flushes = all(subject.startswith(config.FLUSH_COMMIT_SUBJECT_PREFIX) for subject in subjects)
    diff = _run(runner, ["git", "diff", "--name-only", "origin/main", "HEAD"], cwd=cwd)
    if diff.returncode != 0:
        return MainSyncResult(status="probe-error", ahead_count=ahead, error=f"git diff --name-only failed (exit {diff.returncode})", exit_code=2)
    paths = [line for line in diff.stdout.splitlines() if line]
    logs_only = bool(paths) and all(path.startswith("larch-logs/") for path in paths)
    if all_flushes and logs_only:
        clean = _run(runner, ["git", "status", "--porcelain"], cwd=cwd)
        if clean.returncode != 0 or clean.stdout.strip():
            return MainSyncResult(
                status="probe-error",
                ahead_count=ahead,
                error="refusing reset: working tree is not clean (tracked or untracked changes present)",
                exit_code=2,
            )
        reset_result = _run(runner, ["git", "reset", "--hard", "origin/main"], cwd=cwd)
        if reset_result.returncode != 0:
            return MainSyncResult(status="probe-error", ahead_count=ahead, error=f"git reset --hard origin/main failed (exit {reset_result.returncode})", exit_code=2)
        return MainSyncResult(status="reset", ahead_count=ahead)
    return MainSyncResult(
        status="blocked",
        ahead_count=ahead,
        error=f"local main is {ahead} commit(s) ahead of origin/main with non-log changes; push or reconcile before re-running",
        exit_code=1,
    )


def remote_branch_state(
    runner: Runner,
    branch: str,
    *,
    remote: str = "origin",
    cwd: str | None = None,
) -> RemoteBranchState:
    def attempt() -> tuple[CommandResult, int, str]:
        result = _run(
            runner,
            ["git", "ls-remote", "--exit-code", "--heads", remote, branch],
            cwd=cwd,
        )
        combined = result.stdout + result.stderr
        return result, result.returncode, combined

    retried = with_transient_retry(attempt)
    result = retried.value
    if result.returncode == 0:
        return RemoteBranchState(state="present", rc=0)
    if result.returncode == 2:  # noqa: PLR2004 - git ls-remote absent rc
        return RemoteBranchState(state="absent", rc=2)
    err_raw = (
        _one_line_summary(result.stdout + result.stderr)
        or f"git ls-remote failed (exit {result.returncode})"
    )
    err = redact.redact_outbound(err_raw)
    return RemoteBranchState(state="error", rc=result.returncode, error=err)


# CLI entrypoints migrated from git_cli.py.
def _emit_kv(key: str, value: object) -> None:
    logging_util.emit_kv(key, str(value))


def _parse(parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
    try:
        return parser.parse_args(argv)
    except SystemExit:
        return None


def commit_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git commit", add_help=True)
    parser.add_argument("-m", dest="message", default="")
    parser.add_argument("--no-trailer", action="store_true")
    parser.add_argument("--only", action="store_true")
    parser.add_argument("--pathspec-from-file", default=None)
    parser.add_argument("--pathspec-file-nul", action="store_true")
    parser.add_argument("files", nargs="*")
    args = _parse(parser, argv)
    if args is None:
        return 1
    if not args.message.strip():
        print("git-commit.sh: commit message must be non-empty", file=sys.stderr)
        return 1
    if args.pathspec_from_file:
        staged = add_pathspec_file(
            proc,
            args.pathspec_from_file,
            pathspec_file_nul=args.pathspec_file_nul,
        )
    elif args.files:
        staged = add(proc, *args.files)
    else:
        staged = None
    if staged is not None and staged.returncode != 0:
        sys.stdout.write(staged.stdout)
        sys.stderr.write(staged.stderr)
        return staged.returncode
    result = commit_with_trailer(
        proc,
        args.message,
        only=args.only,
        no_trailer=args.no_trailer,
        paths=tuple(args.files),
        pathspec_from_file=args.pathspec_from_file,
        pathspec_file_nul=args.pathspec_file_nul,
    )
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def stage_main(argv: list[str]) -> int:
    if not argv:
        print("git-stage.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-stage.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = add(proc, *argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def amend_add_main(argv: list[str]) -> int:
    if not argv:
        print("git-amend-add.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-amend-add.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = amend_add(proc, argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def current_branch_main(argv: list[str]) -> int:
    if argv:
        print(f"git-current-branch.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    branch = try_current_branch(proc)
    if not branch:
        print("git-current-branch.sh: not on a named branch (detached HEAD or not a git repo)", file=sys.stderr)
        return 1
    _emit_kv("BRANCH", branch)
    return 0


def branch_info_main(argv: list[str]) -> int:
    if argv:
        print(f"git-branch-info.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    info = branch_info(proc)
    if info is None:
        return 1
    _emit_kv("HEAD_SHA", info.head_sha)
    _emit_kv("CURRENT_BRANCH", info.current_branch)
    return 0


def conflict_files_main(argv: list[str]) -> int:
    if argv:
        print(f"git-conflict-files.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    for item in try_conflict_files(proc):
        _emit_kv("FILE", item.path)
        _emit_kv("STAGE_1", str(item.stage_1).lower())
        _emit_kv("STAGE_2", str(item.stage_2).lower())
        _emit_kv("STAGE_3", str(item.stage_3).lower())
        print()
    return 0


def rebase_abort_main(argv: list[str]) -> int:
    if argv:
        print(f"git-rebase-abort.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 0
    _ = rebase_abort(proc)
    return 0


def rebase_skip_main(argv: list[str]) -> int:
    if argv:
        print(f"git-rebase-skip.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = rebase_skip(proc)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def checkout_ours_main(argv: list[str]) -> int:
    if not argv:
        print("git-checkout-ours.sh: at least one file argument is required", file=sys.stderr)
        print("usage: git-checkout-ours.sh <file> [<file> ...]", file=sys.stderr)
        return 1
    result = checkout_ours(proc, *argv)
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def show_stage_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git show-stage")
    parser.add_argument("--stage", required=True)
    parser.add_argument("--file", required=True)
    args = _parse(parser, argv)
    if args is None or args.stage not in {"1", "2", "3"}:
        return 1
    result = show_file(proc, f":{args.stage}:{args.file}")
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def sync_local_main_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git sync-local-main")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser, argv)
    if args is None:
        return 1
    result, rc = sync_local_main(proc, base_remote=args.base_remote, base_ref=args.base_ref)
    if rc == 0:
        _emit_kv("RESULT", result)
    else:
        print(f"git-sync-local-main.sh: {result}", file=sys.stderr)
    return rc


def clean_tree_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git clean-tree")
    parser.add_argument("--fail-closed", action="store_true")
    args = _parse(parser, argv)
    if args is None:
        return 2
    result = clean_tree(proc, fail_closed=args.fail_closed)
    _emit_kv("CLEAN", result.clean)
    if result.dirty_out:
        _emit_kv("DIRTY_OUT", result.dirty_out)
    if result.probe_error:
        _emit_kv("PROBE_ERROR", result.probe_error)
    return result.exit_code


def snapshot_untracked_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git snapshot-untracked", add_help=False)
    parser.add_argument("--output", default="")
    parser.add_argument("--nul", action="store_true")
    args = _parse(parser, argv)
    if args is None or not args.output:
        print("snapshot-untracked.sh: --output is required", file=sys.stderr)
        return 0
    return snapshot_untracked(proc, args.output, nul=args.nul)


def count_commits_main(argv: list[str]) -> int:
    if argv:
        print(f"git count-commits: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = count_commits(proc)
    status_file = os.environ.get("COUNT_COMMITS_STATUS_FILE", "")
    if status_file:
        try:
            with Path(status_file).open("w", encoding="utf-8") as handle:
                handle.write(result.status + "\n")
        except OSError:
            pass
    if result.status == "missing_main_ref":
        print("WARN: lib-count-commits.sh: neither local 'main' nor 'origin/main' exists; cannot determine commit base. Returning 0.", file=sys.stderr)
    print(result.count)
    return 0


def check_main_sync_main(argv: list[str]) -> int:
    if argv:
        print(f"check-main-sync.sh: unknown flag: {argv[0]}", file=sys.stderr)
        return 2
    result = check_main_sync(proc)
    _emit_kv("SYNC_STATUS", result.status)
    if result.ahead_count is not None:
        _emit_kv("AHEAD_COUNT", result.ahead_count)
    if result.error:
        _emit_kv("ERROR", result.error)
    return result.exit_code


def check_remote_branch_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git check-remote-branch", add_help=False)
    parser.add_argument("--branch", default="")
    parser.add_argument("--remote", default="origin")
    args = _parse(parser, argv)
    if args is None or not args.branch:
        _emit_kv("STATE", "error")
        _emit_kv("RC", 1)
        _emit_kv("ERROR", "--branch is required")
        return 0
    result = remote_branch_state(proc, args.branch, remote=args.remote)
    _emit_kv("STATE", result.state)
    _emit_kv("RC", result.rc)
    if result.error:
        _emit_kv("ERROR", result.error)
    return 0


def _emit_phantom_dirty_result(result: phantom.PhantomDirtyResult) -> None:
    _emit_kv("STATUS", result.status)
    if result.reason:
        _emit_kv("REASON", result.reason)
    if result.status == "phantom":
        _emit_kv("PHANTOM_COUNT", result.count)
        _emit_kv("PHANTOM_PATHS_FILE", result.paths_file)


def check_phantom_dirty_main(argv: list[str]) -> int:
    baseline = ""
    step = ""
    phantom_paths_dir = ""
    parse_error = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--baseline":
            if index + 1 >= len(argv):
                parse_error = "baseline-missing-value"
                break
            baseline = argv[index + 1]
            index += 2
            continue
        if arg == "--step":
            if index + 1 >= len(argv):
                parse_error = "step-missing-value"
                break
            step = argv[index + 1]
            index += 2
            continue
        if arg == "--phantom-paths-dir":
            if index + 1 >= len(argv):
                parse_error = "phantom-paths-dir-missing-value"
                break
            phantom_paths_dir = argv[index + 1]
            index += 2
            continue
        parse_error = "unknown-flag"
        break

    if not parse_error:
        if not baseline:
            parse_error = "baseline-required"
        elif not step:
            parse_error = "step-required"
        elif not phantom_paths_dir:
            parse_error = "phantom-paths-dir-required"

    if parse_error:
        _emit_kv("STATUS", "unknown")
        _emit_kv("REASON", parse_error)
        return 0

    if not re.fullmatch(r"^[A-Za-z0-9_.-]+$", step):
        _emit_kv("STATUS", "unknown")
        _emit_kv("REASON", "bad-step")
        return 0

    result = phantom.check_phantom_dirty(
        proc,
        step=step,
        baseline_file=baseline,
        phantom_paths_dir=phantom_paths_dir,
    )
    _emit_phantom_dirty_result(result)
    return 0


def phantom_probe_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git phantom-probe")
    parser.add_argument("--step", required=True)
    parser.add_argument("--baseline-file", default=None)
    args = _parse(parser, argv)
    if args is None:
        return 2
    print(f"→ phantom-probe: {args.step}", file=sys.stderr)
    result = phantom.probe_with_warn(
        proc,
        step=args.step,
        baseline_file=args.baseline_file,
    )
    _emit_kv("PHANTOM_STATUS", result.dirty.status)
    if result.dirty.reason:
        _emit_kv("PHANTOM_REASON", result.dirty.reason)
    if result.dirty.status == "phantom":
        _emit_kv("PHANTOM_COUNT", result.dirty.count)
        _emit_kv("PHANTOM_PATHS_FILE", result.dirty.paths_file)
    if result.append_warn_error:
        _emit_kv("PHANTOM_APPEND_WARN_ERROR", result.append_warn_error)
    return 0
