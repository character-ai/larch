# pyright: reportUnusedCallResult=false
"""Typed git operations over an injected proc.Runner."""

from __future__ import annotations

import contextlib
import os
import re
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from dataclasses import dataclass

import argparse
import sys
from larch.core import config
from larch.core import redact
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.retry import with_transient_retry
from larch.core import logging_util
from larch.implement import phantom
from larch.core import proc

_GIT_REF_LABEL_RE = re.compile(r"^[A-Za-z0-9._/-]+$")
_GIT_STAGE_BASE = 1
_GIT_STAGE_OURS = 2
_GIT_STAGE_THEIRS = 3
_COMMAND_NOT_FOUND_EXIT = 127
_LSOF_MIN_COLUMNS = 2
_PS_LINE_FIELDS = 2
_PATH_LOG_FIELDS = 2


def validate_base_remote_ref(*, base_remote: str, base_ref: str) -> str | None:
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


@dataclass(frozen=True)
class PathCommit:
    sha: str
    subject: str


def _run(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    timeout: float | None = None,
) -> CommandResult:
    if env is None:
        env = _git_subprocess_env()
    return runner.run(list(argv), cwd=cwd, env=env, timeout=timeout)


def _ensure_success(result: CommandResult) -> CommandResult:
    if result.returncode != 0:
        msg = f"git command failed ({result.returncode}): {' '.join(result.argv)}"
        raise ShipError(msg)
    return result


def rev_parse(runner: Runner, ref: str, *, cwd: str | None = None) -> str:
    result = _ensure_success(_run(runner, ["git", "rev-parse", ref], cwd=cwd))
    return result.stdout.strip()


def rev_parse_verify(runner: Runner, ref: str, *, cwd: str | None = None) -> str:
    result = _ensure_success(_run(runner, ["git", "rev-parse", "--verify", ref], cwd=cwd))
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


def log_path_commits(
    runner: Runner,
    path: str,
    *,
    rev_range: str | None = None,
    cwd: str | None = None,
) -> tuple[PathCommit, ...]:
    argv = ["git", "log", "--reverse", "--format=%H%x00%s"]
    if rev_range is not None:
        argv.append(rev_range)
    argv.extend(["--", path])
    result = _ensure_success(_run(runner, argv, cwd=cwd))
    commits: list[PathCommit] = []
    for line in result.stdout.splitlines():
        if not line:
            continue
        parts = line.split("\x00", 1)
        if len(parts) != _PATH_LOG_FIELDS or not parts[0]:
            msg = f"git log path history returned malformed line: {line!r}"
            raise ShipError(msg)
        commits.append(PathCommit(sha=parts[0], subject=parts[1]))
    return tuple(commits)


def try_log_subjects(
    runner: Runner,
    rev_range: str,
    *,
    cwd: str | None = None,
) -> LogSubjects:
    """Non-throwing log subjects (merge flush recovery parity with merge pr)."""
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
    timeout: float | None = None,
) -> CommandResult:
    return _run(
        runner,
        ["git", "fetch", remote, ref, "--quiet"],
        cwd=cwd,
        timeout=timeout,
    )


def show_file(
    runner: Runner,
    spec: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    return _run(runner, ["git", "show", spec], cwd=cwd)


def _output_mentions_index_lock(result: CommandResult) -> bool:
    output = f"{result.stdout}\n{result.stderr}".lower()
    return "index.lock" in output or ("unable to create" in output and "lock" in output)


def _git_index_lock_path(*, runner: Runner, cwd: str | None = None) -> Path | None:
    result = _run(runner, ["git", "rev-parse", "--absolute-git-dir"], cwd=cwd)
    if result.returncode != 0:
        return None
    git_dir = result.stdout.strip()
    if not git_dir:
        return None
    return Path(git_dir) / "index.lock"


def _paths_same(*, left: Path, right: Path) -> bool:
    try:
        return left.resolve() == right.resolve()
    except OSError:
        return left.absolute() == right.absolute()


def _lock_held_by_procfs(lock_path: Path) -> bool | None:
    proc_root = Path("/proc")
    if not proc_root.is_dir():
        return None
    try:
        resolved_lock = lock_path.resolve()
    except OSError:
        resolved_lock = lock_path.absolute()
    current_pid = os.getpid()
    probe_error = False
    for pid_dir in proc_root.iterdir():
        if not pid_dir.name.isdigit() or int(pid_dir.name) == current_pid:
            continue
        fd_dir = pid_dir / "fd"
        try:
            fds = list(fd_dir.iterdir())
        except FileNotFoundError:
            continue
        except OSError:
            probe_error = True
            continue
        for fd_path in fds:
            try:
                if fd_path.resolve() == resolved_lock:
                    return True
            except FileNotFoundError:
                continue
            except OSError:
                probe_error = True
    return None if probe_error else False


def _lock_held_by_lsof(runner: Runner, lock_path: Path, *, cwd: str | None = None) -> bool | None:
    result = runner.run(["lsof", str(lock_path)], cwd=cwd)
    if result.returncode == _COMMAND_NOT_FOUND_EXIT:
        return None
    if result.returncode != 0 and not result.stdout.strip():
        if result.stderr.strip():
            return None
        return False
    current_pid = os.getpid()
    for line in result.stdout.splitlines()[1:]:
        parts = line.split()
        if len(parts) < _LSOF_MIN_COLUMNS:
            continue
        try:
            pid = int(parts[1])
        except ValueError:
            continue
        if pid != current_pid:
            return True
    if result.returncode == 0:
        return False
    return None


def _argv0_is_git(argv0: str) -> bool:
    name = Path(argv0).name
    return name == "git" or name.startswith("git-")


def _proc_git_process_matches_repo(*, pid: int, git_dir: Path, repo_root: Path | None) -> bool:
    proc_dir = Path("/proc") / str(pid)
    try:
        raw_cmdline = (proc_dir / "cmdline").read_bytes()
    except OSError:
        return False
    if not raw_cmdline:
        return False
    argv = [part.decode("utf-8", errors="replace") for part in raw_cmdline.split(b"\0") if part]
    if not argv or not _argv0_is_git(argv[0]):
        return False
    text = "\n".join(argv)
    resolved_git_dir = str(git_dir.resolve())
    if resolved_git_dir in text:
        return True
    if repo_root is not None and str(repo_root.resolve()) in text:
        return True
    for arg in argv:
        if arg.startswith("--git-dir=") and _paths_same(left=Path(arg.removeprefix("--git-dir=")), right=git_dir):
            return True
        if repo_root is not None and arg.startswith("--work-tree=") and _paths_same(
            left=Path(arg.removeprefix("--work-tree=")),
            right=repo_root,
        ):
            return True
    if repo_root is not None:
        with contextlib.suppress(OSError):
            cwd_path = (proc_dir / "cwd").resolve()
            if cwd_path == repo_root.resolve() or repo_root.resolve() in cwd_path.parents:
                return True
    return False


def _ps_git_process_matches_repo(*, line: str, git_dir: Path, repo_root: Path | None) -> bool:
    parts = line.strip().split(maxsplit=1)
    if len(parts) != _PS_LINE_FIELDS or not parts[0].isdigit():
        return False
    args = parts[1]
    argv0 = args.split(maxsplit=1)[0]
    if not _argv0_is_git(argv0):
        return False
    resolved_git_dir = str(git_dir.resolve())
    if resolved_git_dir in args:
        return True
    return repo_root is not None and str(repo_root.resolve()) in args


def _repo_scoped_git_process_detected(runner: Runner, lock_path: Path, *, cwd: str | None = None) -> bool | None:
    git_dir = lock_path.parent
    root_result = _run(runner, ["git", "rev-parse", "--show-toplevel"], cwd=cwd)
    repo_root = Path(root_result.stdout.strip()) if root_result.returncode == 0 and root_result.stdout.strip() else None
    proc_root = Path("/proc")
    if proc_root.is_dir():
        try:
            for pid_dir in proc_root.iterdir():
                if not pid_dir.name.isdigit():
                    continue
                pid = int(pid_dir.name)
                if pid == os.getpid():
                    continue
                if _proc_git_process_matches_repo(pid=pid, git_dir=git_dir, repo_root=repo_root):
                    return True
            return False
        except OSError:
            pass
    ps = runner.run(["ps", "-eo", "pid,args"], cwd=cwd)
    if ps.returncode != 0:
        return None
    current_pid = str(os.getpid())
    for line in ps.stdout.splitlines()[1:]:
        if line.strip().startswith(current_pid + " "):
            continue
        if _ps_git_process_matches_repo(line=line, git_dir=git_dir, repo_root=repo_root):
            return True
    return False


def _index_lock_is_held(runner: Runner, lock_path: Path, *, cwd: str | None = None) -> bool:
    if not lock_path.exists():
        return False
    held = _lock_held_by_procfs(lock_path)
    if held is None:
        held = _lock_held_by_lsof(runner, lock_path, cwd=cwd)
    if held is not None:
        return held
    repo_scoped = _repo_scoped_git_process_detected(runner, lock_path, cwd=cwd)
    if repo_scoped is not None:
        return repo_scoped
    return True


def _try_remove_stale_index_lock(runner: Runner, *, cwd: str | None = None) -> tuple[bool, str]:
    lock_path = _git_index_lock_path(runner=runner, cwd=cwd)
    if lock_path is None:
        return False, "larch: stale .git/index.lock not removed: git-dir probe failed"
    lock_label = f"lock={lock_path}"
    if not lock_path.exists():
        return False, f"larch: stale .git/index.lock not removed: lock absent; {lock_label}"
    try:
        stat = lock_path.stat()
    except OSError as exc:
        return False, f"larch: stale .git/index.lock not removed: stat failed: {exc}; {lock_label}"
    if stat.st_size != 0:
        return False, f"larch: stale .git/index.lock not removed: non-empty lock; {lock_label}"
    if _index_lock_is_held(runner, lock_path, cwd=cwd):
        return False, f"larch: stale .git/index.lock not removed: lock held by process; {lock_label}"
    try:
        lock_path.unlink()
    except OSError as exc:
        return False, f"larch: stale .git/index.lock not removed: unlink failed: {exc}; {lock_label}"
    return True, f"larch: removed stale .git/index.lock; {lock_label}"


def _append_stderr(*, result: CommandResult, note: str) -> CommandResult:
    suffix = note if note.endswith("\n") else f"{note}\n"
    stderr = result.stderr
    if stderr and not stderr.endswith("\n"):
        stderr += "\n"
    return CommandResult(result.argv, result.returncode, result.stdout, stderr + suffix, result.duration)


def _run_with_stale_index_lock_retry(
    runner: Runner,
    argv: Sequence[str],
    *,
    cwd: str | None = None,
) -> CommandResult:
    result = _run(runner, argv, cwd=cwd)
    if result.returncode == 0:
        return result
    lock_path = _git_index_lock_path(runner=runner, cwd=cwd)
    if not _output_mentions_index_lock(result) and (lock_path is None or not lock_path.exists()):
        return result
    removed, diagnostic = _try_remove_stale_index_lock(runner, cwd=cwd)
    if not removed:
        return _append_stderr(result=result, note=diagnostic)
    retry = _run(runner, argv, cwd=cwd)
    return _append_stderr(result=retry, note=f"{diagnostic}; retrying git command once")


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
    return _run_with_stale_index_lock_retry(runner, argv, cwd=cwd)


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
    """Commit via temp file + interpret-trailers for ``cli.py git commit``."""
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
        return _run_with_stale_index_lock_retry(runner, argv, cwd=cwd)
    finally:
        Path(tmp_path).unlink()


def add(runner: Runner, *paths: str, cwd: str | None = None) -> CommandResult:
    argv = ["git", "add"]
    if paths:
        argv.extend(["--", *paths])
    return _run_with_stale_index_lock_retry(runner, argv, cwd=cwd)


def rm(runner: Runner, *paths: str, force: bool = False, cwd: str | None = None) -> CommandResult:
    argv = ["git", "rm"]
    if force:
        argv.append("-f")
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
    return _run_with_stale_index_lock_retry(runner, argv, cwd=cwd)


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
    """Non-raising unmerged-path probe (push rebase / conflict CLI parity)."""
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
    """Force-push recovery: clean-tree guard, fetch, lease push, race noop, one retry."""
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
    """Non-raising conflict-file probe for best-effort internal callers."""
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
    """Resolve topic-branch push remote (push rebase parity)."""
    for key in (f"branch.{branch}.pushRemote", f"branch.{branch}.remote"):
        result = _run(runner, ["git", "config", "--get", key], cwd=cwd)
        if result.returncode == 0:
            candidate = result.stdout.strip()
            if candidate and _GIT_REF_LABEL_RE.fullmatch(candidate):
                return candidate
    return "origin"


def rebase_in_progress(runner: Runner, *, cwd: str | None = None) -> bool:
    """True when git reports an active rebase (push rebase --continue guard)."""
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
    # Prefer the remote-tracking origin/main over a possibly-stale local main so a
    # mid-run rebase onto an advanced origin/main does not over-count inherited
    # already-merged commits (issue #5460).
    if _run(runner, ["git", "rev-parse", "--verify", "origin/main"], cwd=cwd).returncode == 0:
        base_ref = "origin/main"
    elif _run(runner, ["git", "rev-parse", "--verify", "main"], cwd=cwd).returncode == 0:
        base_ref = "main"
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
    logs_only = not paths or all(path.startswith("larch-logs/") for path in paths)
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
def _emit_kv(*, key: str, value: object) -> None:
    logging_util.emit_kv(key=key, value=str(value))


def _parse(*, parser: argparse.ArgumentParser, argv: list[str]) -> argparse.Namespace | None:
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
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 1
    if not args.message.strip():
        print("git-commit.sh: commit message must be non-empty", file=sys.stderr)
        return 1
    removed, diagnostic = _try_remove_stale_index_lock(proc)
    if removed:
        print(diagnostic, file=sys.stderr)
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
    _emit_kv(key="BRANCH", value=branch)
    return 0


def branch_info_main(argv: list[str]) -> int:
    if argv:
        print(f"git-branch-info.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    info = branch_info(proc)
    if info is None:
        return 1
    _emit_kv(key="HEAD_SHA", value=info.head_sha)
    _emit_kv(key="CURRENT_BRANCH", value=info.current_branch)
    return 0


def conflict_files_main(argv: list[str]) -> int:
    if argv:
        print(f"git-conflict-files.sh: unknown argument: {argv[0]}", file=sys.stderr)
        return 1
    result = _run(proc, ["git", "ls-files", "-u"])
    if result.returncode != 0:
        sys.stderr.write(result.stderr)
        return result.returncode
    for item in _parse_conflict_file_rows(result.stdout):
        _emit_kv(key="FILE", value=item.path)
        _emit_kv(key="STAGE_1", value=str(item.stage_1).lower())
        _emit_kv(key="STAGE_2", value=str(item.stage_2).lower())
        _emit_kv(key="STAGE_3", value=str(item.stage_3).lower())
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
    stage = ""
    file = ""
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--stage":
            if index + 1 >= len(argv):
                print("git-show-stage.sh: --stage requires a value", file=sys.stderr)
                return 1
            stage = argv[index + 1]
            index += 2
            continue
        if arg == "--file":
            if index + 1 >= len(argv):
                print("git-show-stage.sh: --file requires a value", file=sys.stderr)
                return 1
            file = argv[index + 1]
            index += 2
            continue
        print(f"git-show-stage.sh: unknown argument: {arg}", file=sys.stderr)
        return 1
    if not stage or not file:
        print("git-show-stage.sh: --stage and --file are required", file=sys.stderr)
        return 1
    if stage not in {"1", "2", "3"}:
        print(f"git-show-stage.sh: --stage must be 1, 2, or 3 (got: {stage})", file=sys.stderr)
        return 1
    result = show_file(proc, f":{stage}:{file}")
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    return result.returncode


def sync_local_main_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git sync-local-main")
    parser.add_argument("--base-remote", default="origin")
    parser.add_argument("--base-ref", default="main")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 1
    result, rc = sync_local_main(proc, base_remote=args.base_remote, base_ref=args.base_ref)
    if rc == 0:
        _emit_kv(key="RESULT", value=result)
    else:
        print(f"cli.py git sync-local-main: {result}", file=sys.stderr)
    return rc


def clean_tree_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py git clean-tree")
    parser.add_argument("--fail-closed", action="store_true")
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 2
    result = clean_tree(proc, fail_closed=args.fail_closed)
    _emit_kv(key="CLEAN", value=result.clean)
    if result.dirty_out:
        _emit_kv(key="DIRTY_OUT", value=result.dirty_out)
    if result.probe_error:
        _emit_kv(key="PROBE_ERROR", value=result.probe_error)
    return result.exit_code


def snapshot_untracked_main(argv: list[str]) -> int:
    output = ""
    nul = False
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--output":
            if index + 1 >= len(argv) or not argv[index + 1]:
                print("snapshot-untracked.sh: --output requires a value", file=sys.stderr)
                return 0
            output = argv[index + 1]
            index += 2
            continue
        if arg == "--nul":
            nul = True
            index += 1
            continue
        print(f"snapshot-untracked.sh: unknown flag: {arg}", file=sys.stderr)
        return 0
    if not output:
        print("snapshot-untracked.sh: --output is required", file=sys.stderr)
        return 0
    return snapshot_untracked(proc, output, nul=nul)


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
    _emit_kv(key="SYNC_STATUS", value=result.status)
    if result.ahead_count is not None:
        _emit_kv(key="AHEAD_COUNT", value=result.ahead_count)
    if result.error:
        _emit_kv(key="ERROR", value=result.error)
    return result.exit_code


def check_remote_branch_main(argv: list[str]) -> int:
    branch = ""
    remote = "origin"
    index = 0
    while index < len(argv):
        arg = argv[index]
        if arg == "--branch":
            branch = argv[index + 1] if index + 1 < len(argv) else ""
            index += 2
            continue
        if arg == "--remote":
            remote = argv[index + 1] if index + 1 < len(argv) else ""
            index += 2
            continue
        _emit_kv(key="STATE", value="error")
        _emit_kv(key="RC", value=1)
        _emit_kv(key="ERROR", value=f"unknown flag: {arg}")
        return 0
    if not branch:
        _emit_kv(key="STATE", value="error")
        _emit_kv(key="RC", value=1)
        _emit_kv(key="ERROR", value="--branch is required")
        return 0
    result = remote_branch_state(proc, branch, remote=remote)
    _emit_kv(key="STATE", value=result.state)
    _emit_kv(key="RC", value=result.rc)
    if result.error:
        _emit_kv(key="ERROR", value=result.error)
    return 0


def _emit_phantom_dirty_result(result: phantom.PhantomDirtyResult) -> None:
    _emit_kv(key="STATUS", value=result.status)
    if result.reason:
        _emit_kv(key="REASON", value=result.reason)
    if result.status == "phantom":
        _emit_kv(key="PHANTOM_COUNT", value=result.count)
        _emit_kv(key="PHANTOM_PATHS_FILE", value=result.paths_file)


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
        _emit_kv(key="STATUS", value="unknown")
        _emit_kv(key="REASON", value=parse_error)
        return 0

    if not re.fullmatch(r"^[A-Za-z0-9_.-]+$", step):
        _emit_kv(key="STATUS", value="unknown")
        _emit_kv(key="REASON", value="bad-step")
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
    args = _parse(parser=parser, argv=argv)
    if args is None:
        return 2
    print(f"→ phantom-probe: {args.step}", file=sys.stderr)
    result = phantom.probe_with_warn(
        proc,
        step=args.step,
        baseline_file=args.baseline_file,
    )
    _emit_kv(key="PHANTOM_STATUS", value=result.dirty.status)
    if result.dirty.reason:
        _emit_kv(key="PHANTOM_REASON", value=result.dirty.reason)
    if result.dirty.status == "phantom":
        _emit_kv(key="PHANTOM_COUNT", value=result.dirty.count)
        _emit_kv(key="PHANTOM_PATHS_FILE", value=result.dirty.paths_file)
    if result.append_warn_error:
        _emit_kv(key="PHANTOM_APPEND_WARN_ERROR", value=result.append_warn_error)
    return 0
