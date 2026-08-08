# pyright: reportUnusedCallResult=false
"""Typed git operations over an injected proc.Runner."""

from __future__ import annotations

import contextlib
import os
import re
import time
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from dataclasses import dataclass

from larch.core import config
from larch.core import redact
from larch.errors import ShipError
from larch.core.proc import CommandResult, Runner
from larch.core.retry import with_transient_retry
from larch.core.repo_roots import RepoRootProbeOptions, repo_root_probe

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

def assert_original_branch_write_allowed(*, branch: str) -> None:
    state_file = os.environ.get("SHIP_PR_STATE_FILE", "")
    if not state_file:
        implement_tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
        if implement_tmpdir:
            state_file = str(Path(implement_tmpdir) / "ship-pr-state.sh")
    if not state_file or not branch:
        return
    path = Path(state_file)
    if not path.is_file() or path.is_symlink():
        return
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return
    values: dict[str, str] = {}
    for line in lines:
        key, sep, value = line.partition("=")
        if sep:
            values[key] = value
    if values.get("ORIGINAL_BRANCH_FORBIDDEN", "").strip().lower() == "true" and values.get("BRANCH_NAME", "") == branch:
        raise ShipError(f"refusing commit or push on forbidden original branch: {branch}")

def _assert_branch_write_allowed(runner: Runner, *, cwd: str | None = None) -> None:
    if not os.environ.get("SHIP_PR_STATE_FILE", "") and not os.environ.get(config.ENV_IMPLEMENT_TMPDIR, ""):
        return
    branch = try_current_branch(runner, cwd=cwd)
    if branch:
        assert_original_branch_write_allowed(branch=branch)

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

def switch_branch(
    runner: Runner,
    name: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    """Switch to one caller-validated local branch."""
    return _run(runner, ["git", "switch", name], cwd=cwd)

def delete_branch(
    runner: Runner,
    name: str,
    *,
    force: bool = False,
    cwd: str | None = None,
) -> CommandResult:
    """Delete one caller-validated local branch."""
    flag = "-D" if force else "-d"
    return _run(runner, ["git", "branch", flag, name], cwd=cwd)

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
    root_result = repo_root_probe(runner=runner, options=RepoRootProbeOptions(runner_cwd=cwd))
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
    _assert_branch_write_allowed(runner, cwd=cwd)
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

def add(runner: Runner, *paths: str, cwd: str | None = None) -> CommandResult:
    _assert_branch_write_allowed(runner, cwd=cwd)
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


def force_push_with_lease_expecting(
    runner: Runner,
    remote: str,
    refspec: str,
    expected_oid: str,
    *,
    cwd: str | None = None,
) -> CommandResult:
    lease = f"{refspec}:{expected_oid}"
    push_refspec = f"{refspec}:{refspec}"
    return _run(
        runner,
        ["git", "push", f"--force-with-lease={lease}", remote, push_refspec],
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
                ["git", "push", f"--force-with-lease={lease}", remote, refspec],
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
class CountCommitsResult:
    count: int
    status: str

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


def _one_line_summary(text: str) -> str:
    return text.replace("\n", " ").replace("\r", " ").replace("\t", " ")[:256]

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
