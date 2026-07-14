# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Per-clone progress breadcrumb writer for larch statuslines."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import fcntl
import os
import re
import stat
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from larch.git.repo_roots import consumer_repo_root
from larch import io as larch_io


PROGRESS_DIRNAME = "progress"
PROGRESS_SUFFIX = ".log"
CURRENT_RUN_FILENAME = "current"
CURRENT_RUN_LOCK_FILENAME = ".current.lock"
RUN_BREADCRUMB_FILENAME = "breadcrumbs.log"
_HASH_HEX_CHARS = 16
_NEWLINE_CHARS = "\n\r"
_PRINTABLE_ASCII_MIN = 32
_ASCII_DELETE = 127
_C1_CONTROL_MIN = 0x80
_C1_CONTROL_MAX = 0x9F
_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]{1,128}")
_CLONE_HASH_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{16}")


@dataclass(frozen=True)
class PersistedRunResult:
    """Session-owned run identity recovered from persisted environment files."""

    run_id: str | None
    repo_root: Path | None


def _cache_home() -> Path:
    override = os.environ.get("LARCH_TEST_CACHE_HOME")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_CACHE_HOME")
    if xdg:
        return Path(xdg)
    return Path.home() / ".cache"


def progress_root() -> Path:
    return _cache_home() / "larch" / PROGRESS_DIRNAME


def _canonical_repo_root(repo_root: str | Path) -> Path:
    path = Path(repo_root).expanduser()
    try:
        return path.resolve()
    except OSError:
        return path.absolute()


def progress_path(repo_root: str | Path) -> Path:
    """Return the clone-scoped breadcrumb path for ``repo_root``."""
    canonical_root = consumer_repo_root(Path(repo_root).expanduser()) or _canonical_repo_root(repo_root)
    canonical = str(canonical_root)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:_HASH_HEX_CHARS]
    return progress_root() / f"{digest}{PROGRESS_SUFFIX}"


def validate_run_id(run_id: str) -> str:
    """Return a safe run ID, reserving ``current`` for the active-run pointer."""
    if not run_id:
        msg = "run ID must be non-empty"
        raise ValueError(msg)
    if run_id in {".", "..", CURRENT_RUN_FILENAME}:
        msg = f"reserved run ID: {run_id}"
        raise ValueError(msg)
    if _RUN_ID_PATTERN.fullmatch(run_id) is None:
        msg = "run ID must contain only letters, digits, dot, underscore, or dash"
        raise ValueError(msg)
    return run_id


def _persisted_run_id_candidates(tmpdir: str | Path) -> list[str]:
    candidates: list[str] = []
    root = Path(tmpdir)
    for path in (root / "session-env.sh", root / "source-env.sh"):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        candidates.extend(
            raw[len(prefix):].strip().strip("'\"")
            for raw in lines
            for prefix in ("LARCH_RUN_ID=", "export LARCH_RUN_ID=")
            if raw.startswith(prefix)
        )
    return candidates


def resolve_owned_run_id(
    *,
    explicit: str | None = None,
    tmpdir: str | Path | None = None,
    env: dict[str, str] | None = None,
) -> str | None:
    """Resolve a process-owned run ID without consulting the active pointer."""
    env_map = os.environ if env is None else env
    candidates = [value for value in (explicit, env_map.get("LARCH_RUN_ID")) if value]
    if tmpdir is not None:
        candidates.extend(_persisted_run_id_candidates(tmpdir))
    for candidate in candidates:
        with contextlib.suppress(ValueError):
            return validate_run_id(candidate)
    return None


def resolve_persisted_repo_root(*, tmpdir: str | Path) -> Path | None:
    """Resolve the persisted consumer root for a session-owned run."""
    root = Path(tmpdir)
    for path in (root / "source-env.sh", root / "session-env.sh"):
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for raw in lines:
            for prefix in ("REPO_ROOT=", "export REPO_ROOT="):
                if raw.startswith(prefix):
                    candidate = Path(raw[len(prefix):].strip().strip("'\""))
                    if candidate.is_absolute() and candidate.is_dir():
                        with contextlib.suppress(OSError):
                            return candidate.resolve()
    return None


def resolve_persisted_run(*, tmpdir: str | Path, env: dict[str, str] | None = None) -> PersistedRunResult:
    """Resolve the persisted run ID and consumer root without using an active pointer."""
    return PersistedRunResult(
        run_id=resolve_owned_run_id(tmpdir=tmpdir, env=env),
        repo_root=resolve_persisted_repo_root(tmpdir=tmpdir),
    )


def progress_clone_dir(repo_root: str | Path) -> Path:
    """Return the clone-scoped progress directory for ``repo_root``."""
    return progress_path(repo_root).with_suffix("")


def current_run_path(repo_root: str | Path) -> Path:
    return progress_clone_dir(repo_root) / CURRENT_RUN_FILENAME


def run_progress_dir(repo_root: str | Path, run_id: str) -> Path:
    return progress_clone_dir(repo_root) / validate_run_id(run_id)


def run_progress_path(repo_root: str | Path, run_id: str) -> Path:
    return run_progress_dir(repo_root, run_id) / RUN_BREADCRUMB_FILENAME


def _reject_line_part(value: object, *, label: str) -> str:
    text = str(value).strip()
    if not text:
        msg = f"{label} must be non-empty"
        raise ValueError(msg)
    if "\t" in text or any(ch in text for ch in _NEWLINE_CHARS):
        msg = f"{label} must be one line without tabs"
        raise ValueError(msg)
    if any(ord(ch) < _PRINTABLE_ASCII_MIN or ord(ch) == _ASCII_DELETE or _C1_CONTROL_MIN <= ord(ch) <= _C1_CONTROL_MAX for ch in text):
        msg = f"{label} must not contain control characters"
        raise ValueError(msg)
    if label == "text" and "://" in text:
        msg = "text must identify entities by number, not URL"
        raise ValueError(msg)
    return text


def breadcrumb_line(*, skill: str, step: str, text: str) -> str:
    skill_text = _reject_line_part(skill, label="skill")
    step_text = _reject_line_part(step, label="step")
    body = _reject_line_part(text, label="text")
    return f"[{skill_text} {step_text}] {body}\n"


def append_breadcrumb(repo_root: str | Path, skill: str, step: str, text: str) -> bool:
    """Append one active-run breadcrumb, returning ``False`` on any best-effort failure."""
    try:
        line = breadcrumb_line(skill=skill, step=step, text=text)
        clone_dir_fd: int = _open_existing_directory_fd(progress_clone_dir(repo_root))
        try:
            run_id: str | None = _read_active_run_id_from_dirfd(clone_dir_fd)
            if run_id is None:
                return False
            run_dir_fd: int = _open_or_create_subdir(clone_dir_fd, run_id)
            try:
                _append_line_in_dir(run_dir_fd, RUN_BREADCRUMB_FILENAME, line)
            finally:
                os.close(run_dir_fd)
        finally:
            os.close(clone_dir_fd)
    except (OSError, TypeError, ValueError):
        return False
    return True


def _dir_open_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _nofollow_file_flags(*, append: bool) -> int:
    flags = os.O_WRONLY | os.O_CREAT
    if append:
        flags |= os.O_APPEND
    else:
        flags |= os.O_EXCL
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _validate_dir_entry_name(name: str) -> None:
    if not name or name in {".", ".."} or "/" in name or "\\" in name:
        msg = f"unsafe directory entry name: {name!r}"
        raise ValueError(msg)


def _ensure_directory_fd(path: Path) -> int:
    """Create ``path`` and its parents, returning a verified live directory fd."""
    target = path.expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    if len(target.parts) == 1:
        return _open_verified_dir(Path(target.anchor))
    current_fd = _open_verified_dir(Path(target.anchor))
    try:
        for part in target.parts[1:]:
            next_fd = _open_or_create_subdir(current_fd, part)
            old_fd = current_fd
            current_fd = next_fd
            os.close(old_fd)
    except (OSError, ValueError):
        os.close(current_fd)
        raise
    return current_fd


def _ensure_directory(path: Path) -> None:
    """Create ``path`` and its parents without following symlink swaps."""
    dir_fd = _ensure_directory_fd(path)
    try:
        return
    finally:
        os.close(dir_fd)


def _open_existing_directory_fd(path: Path) -> int:
    """Open ``path`` and its parents without creating or following symlinks."""
    target: Path = path.expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    if len(target.parts) == 1:
        return _open_verified_dir(Path(target.anchor))
    current_fd: int = _open_verified_dir(Path(target.anchor))
    try:
        for part in target.parts[1:]:
            next_fd: int = _open_existing_subdir(current_fd, part)
            old_fd: int = current_fd
            current_fd = next_fd
            os.close(old_fd)
    except (OSError, ValueError):
        os.close(current_fd)
        raise
    return current_fd


def _open_or_create_subdir(parent_fd: int, name: str) -> int:
    """Open or create a verified directory entry under ``parent_fd``."""
    _validate_dir_entry_name(name)
    try:
        child_fd = os.open(name, _dir_open_flags(), dir_fd=parent_fd)
    except FileNotFoundError:
        with contextlib.suppress(FileExistsError):
            os.mkdir(name, 0o777, dir_fd=parent_fd)
        child_fd = os.open(name, _dir_open_flags(), dir_fd=parent_fd)
    try:
        stat_result = os.fstat(child_fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            msg = f"refusing non-directory progress path: {name}"
            raise OSError(msg)
    except OSError:
        os.close(child_fd)
        raise
    return child_fd


def _open_existing_subdir(parent_fd: int, name: str) -> int:
    """Open an existing verified directory entry under ``parent_fd``."""
    _validate_dir_entry_name(name)
    child_fd: int = os.open(name, _dir_open_flags(), dir_fd=parent_fd)
    try:
        stat_result: os.stat_result = os.fstat(child_fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            msg = f"refusing non-directory progress path: {name}"
            raise OSError(msg)
    except OSError:
        os.close(child_fd)
        raise
    return child_fd


def _open_verified_dir(path: Path) -> int:
    larch_io.assert_no_symlink_path_or_ancestors(path)
    fd = os.open(path, _dir_open_flags())
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISDIR(stat_result.st_mode):
            msg = f"refusing non-directory progress path: {path}"
            raise OSError(msg)
    except OSError:
        os.close(fd)
        raise
    return fd


def _readonly_file_flags() -> int:
    flags = os.O_RDONLY
    if hasattr(os, "O_NONBLOCK"):
        flags |= os.O_NONBLOCK
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    return flags


def _assert_safe_destination(dir_fd: int, name: str) -> None:
    try:
        stat_result = os.lstat(name, dir_fd=dir_fd)
    except FileNotFoundError:
        return
    if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISREG(stat_result.st_mode):
        msg = f"refusing unsafe progress target: {name}"
        raise OSError(msg)


def _atomic_write_once(dir_fd: int, name: str, text: str, *, mode: int, temp_name: str) -> None:
    fd = os.open(temp_name, _nofollow_file_flags(append=False), mode, dir_fd=dir_fd)
    replaced = False
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            msg = f"refusing non-regular temporary progress target: {temp_name}"
            raise OSError(msg)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            fd = -1
            _ = handle.write(text)
            handle.flush()
            os.fchmod(handle.fileno(), mode)
        _assert_safe_destination(dir_fd, name)
        os.replace(temp_name, name, src_dir_fd=dir_fd, dst_dir_fd=dir_fd)
        replaced = True
    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
                os.close(fd)
        if not replaced:
            with contextlib.suppress(OSError):
                os.unlink(temp_name, dir_fd=dir_fd)


def _atomic_write_in_dir(dir_fd: int, name: str, text: str, *, mode: int = 0o600, temp_prefix: str = ".current.") -> None:
    _validate_dir_entry_name(name)
    _validate_dir_entry_name(temp_prefix.rstrip("."))
    last_error: FileExistsError | None = None
    for _attempt in range(100):
        temp_name = f"{temp_prefix}{uuid.uuid4().hex}"
        try:
            _atomic_write_once(dir_fd, name, text, mode=mode, temp_name=temp_name)
        except FileExistsError as exc:
            last_error = exc
            continue
        return
    msg = f"could not create unique temporary progress file for {name}"
    raise OSError(msg) from last_error


def _append_line_in_dir(dir_fd: int, name: str, line: str) -> None:
    _validate_dir_entry_name(name)
    fd = os.open(name, _nofollow_file_flags(append=True), 0o600, dir_fd=dir_fd)
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            msg = f"refusing non-regular breadcrumb target: {name}"
            raise OSError(msg)
        with os.fdopen(fd, "a", encoding="utf-8") as handle:
            fd = -1
            _ = handle.write(line)
            handle.flush()
            with contextlib.suppress(OSError):
                os.fchmod(handle.fileno(), 0o600)
    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
                os.close(fd)


@contextlib.contextmanager
def _current_pointer_lock(clone_dir_fd: int):
    lock_fd = os.open(
        CURRENT_RUN_LOCK_FILENAME,
        _nofollow_file_flags(append=True),
        0o600,
        dir_fd=clone_dir_fd,
    )
    try:
        if not stat.S_ISREG(os.fstat(lock_fd).st_mode):
            raise OSError("refusing non-regular progress pointer lock")
        fcntl.flock(lock_fd, fcntl.LOCK_EX)
        yield
    finally:
        with contextlib.suppress(OSError):
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
        os.close(lock_fd)


def activate_run(repo_root: str | Path, run_id: str) -> None:
    safe_run_id = validate_run_id(run_id)
    clone_dir_fd = _ensure_directory_fd(progress_clone_dir(repo_root))
    try:
        with _current_pointer_lock(clone_dir_fd):
            run_dir_fd = _open_or_create_subdir(clone_dir_fd, safe_run_id)
            os.close(run_dir_fd)
            _atomic_write_in_dir(clone_dir_fd, CURRENT_RUN_FILENAME, f"{safe_run_id}\n", mode=0o600, temp_prefix=".current.")
    finally:
        os.close(clone_dir_fd)


def append_breadcrumb_for_run(repo_root: str | Path, run_id: str, skill: str, step: str, text: str) -> bool:
    """Append one run-scoped breadcrumb, returning ``False`` on best-effort failure."""
    try:
        line = breadcrumb_line(skill=skill, step=step, text=text)
        safe_run_id = validate_run_id(run_id)
        clone_dir = progress_clone_dir(repo_root)
        clone_dir_fd = _ensure_directory_fd(clone_dir)
        try:
            run_dir_fd = _open_or_create_subdir(clone_dir_fd, safe_run_id)
            try:
                _append_line_in_dir(run_dir_fd, RUN_BREADCRUMB_FILENAME, line)
            finally:
                os.close(run_dir_fd)
        finally:
            os.close(clone_dir_fd)
    except (OSError, TypeError, ValueError):
        return False
    return True


def _cutoff_timestamp(retention_days: int, now: float | None) -> float:
    return (time.time() if now is None else now) - (retention_days * 86400)


def _entry_mtime_for_cleanup(entry_path: Path, *, log_path: Path | None = None) -> float | None:
    try:
        if log_path is not None and not log_path.is_symlink() and log_path.is_file():
            return log_path.stat().st_mtime
        return entry_path.stat().st_mtime
    except OSError:
        return None


def read_active_run_id(repo_root: str | Path) -> str | None:
    """Return the active run ID for ``repo_root`` without creating progress state."""
    try:
        clone_dir_fd: int = _open_existing_directory_fd(progress_clone_dir(repo_root))
    except (OSError, TypeError, ValueError):
        return None
    try:
        return _read_active_run_id_from_dirfd(clone_dir_fd)
    finally:
        os.close(clone_dir_fd)


def deactivate_run(repo_root: str | Path, expected_run_id: str) -> bool:
    """Clear ``current`` only when it still names ``expected_run_id``."""
    try:
        safe_run_id = validate_run_id(expected_run_id)
        clone_dir_fd = _open_existing_directory_fd(progress_clone_dir(repo_root))
        try:
            with _current_pointer_lock(clone_dir_fd):
                stat_result = os.lstat(CURRENT_RUN_FILENAME, dir_fd=clone_dir_fd)
                if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISREG(stat_result.st_mode):
                    return False
                if _read_active_run_id_from_dirfd(clone_dir_fd) != safe_run_id:
                    return False
                os.unlink(CURRENT_RUN_FILENAME, dir_fd=clone_dir_fd)
        finally:
            os.close(clone_dir_fd)
    except (OSError, TypeError, ValueError):
        return False
    return True


def clear_active_run(repo_root: str | Path) -> bool:
    """Clear the active-run pointer regardless of its prior owner."""
    try:
        clone_dir_fd = _open_existing_directory_fd(progress_clone_dir(repo_root))
        try:
            with _current_pointer_lock(clone_dir_fd):
                stat_result = os.lstat(CURRENT_RUN_FILENAME, dir_fd=clone_dir_fd)
                if stat.S_ISLNK(stat_result.st_mode) or not stat.S_ISREG(stat_result.st_mode):
                    return False
                os.unlink(CURRENT_RUN_FILENAME, dir_fd=clone_dir_fd)
        finally:
            os.close(clone_dir_fd)
    except (OSError, TypeError, ValueError):
        return False
    return True


def _read_active_run_id(clone_dir: Path) -> str | None:  # pyright: ignore[reportUnusedFunction]
    """Return the normalized ``current`` pointer written by ``activate_run``."""
    pointer_path = clone_dir / CURRENT_RUN_FILENAME
    try:
        if pointer_path.is_symlink() or not pointer_path.is_file():
            return None
        with pointer_path.open("r", encoding="utf-8") as handle:
            first_line = handle.readline()
    except (OSError, UnicodeError):
        return None
    normalized = first_line.rstrip()
    if not normalized:
        return None
    try:
        return validate_run_id(normalized)
    except ValueError:
        return None


def _read_active_run_id_from_dirfd(dir_fd: int) -> str | None:
    try:
        fd = os.open(CURRENT_RUN_FILENAME, _readonly_file_flags(), dir_fd=dir_fd)
    except OSError:
        return None
    try:
        stat_result = os.fstat(fd)
        if not stat.S_ISREG(stat_result.st_mode):
            return None
        with os.fdopen(fd, "r", encoding="utf-8", errors="replace") as handle:
            fd = -1
            first_line = handle.readline()
    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
                os.close(fd)
    normalized = first_line.rstrip()
    if not normalized:
        return None
    try:
        return validate_run_id(normalized)
    except ValueError:
        return None


def _remove_tree_in_dirfd(dir_fd: int) -> None:
    try:
        entries = list(os.listdir(dir_fd))
    except OSError:
        return
    for name in entries:
        try:
            stat_result = os.lstat(name, dir_fd=dir_fd)
        except OSError:
            continue
        if stat.S_ISDIR(stat_result.st_mode):
            try:
                child_fd = os.open(name, _dir_open_flags(), dir_fd=dir_fd)
            except OSError:
                continue
            try:
                _remove_tree_in_dirfd(child_fd)
            finally:
                os.close(child_fd)
            with contextlib.suppress(OSError):
                os.rmdir(name, dir_fd=dir_fd)
        else:
            with contextlib.suppress(OSError):
                os.unlink(name, dir_fd=dir_fd)


def _is_clone_hash_name(name: str) -> bool:
    return _CLONE_HASH_PATTERN.fullmatch(name) is not None


def _cleanup_flat_progress_files(progress_dir: Path, *, cutoff: float) -> tuple[int, set[Path]]:
    removed = 0
    clone_dirs: set[Path] = set()
    for entry in progress_dir.glob(f"*{PROGRESS_SUFFIX}"):
        clone_name = entry.name.removesuffix(PROGRESS_SUFFIX)
        if _is_clone_hash_name(clone_name):
            clone_dirs.add(progress_dir / clone_name)
        try:
            if entry.is_symlink() or not entry.is_file():
                continue
            mtime = _entry_mtime_for_cleanup(entry)
            if mtime is None or mtime >= cutoff:
                continue
            entry.unlink()
            removed += 1
        except OSError:
            continue
    return removed, clone_dirs


def _clone_dirs_under(progress_dir: Path) -> set[Path]:
    clone_dirs: set[Path] = set()
    try:
        entries = list(progress_dir.iterdir())
    except OSError:
        return clone_dirs
    for entry in entries:
        try:
            if _is_clone_hash_name(entry.name) and not entry.is_symlink() and entry.is_dir():
                clone_dirs.add(entry)
        except OSError:
            continue
    return clone_dirs


def _maybe_remove_run_dir(dir_fd: int, child_name: str, active_run_id: str | None, cutoff: float) -> int:
    try:
        run_id = validate_run_id(child_name)
    except ValueError:
        return 0
    try:
        child_fd = os.open(child_name, _dir_open_flags(), dir_fd=dir_fd)
    except OSError:
        return 0
    try:
        stat_result = os.fstat(child_fd)
        if not stat.S_ISDIR(stat_result.st_mode) or run_id == active_run_id:
            return 0
        try:
            log_stat = os.stat(RUN_BREADCRUMB_FILENAME, dir_fd=child_fd, follow_symlinks=False)
            mtime = log_stat.st_mtime if stat.S_ISREG(log_stat.st_mode) else stat_result.st_mtime
        except OSError:
            mtime = stat_result.st_mtime
        if mtime >= cutoff:
            return 0
        _remove_tree_in_dirfd(child_fd)
        try:
            os.rmdir(child_name, dir_fd=dir_fd)
        except OSError:
            return 0
        return 1
    finally:
        os.close(child_fd)


def _cleanup_run_dirs_for_clone(clone_dir: Path, *, cutoff: float) -> int:
    try:
        dir_fd = _open_verified_dir(clone_dir)
    except OSError:
        return 0
    removed = 0
    try:
        active_run_id = _read_active_run_id_from_dirfd(dir_fd)
        try:
            children = list(os.listdir(dir_fd))  # noqa: PTH208 - dir_fd-based listdir required; Path.iterdir() does not accept an fd
        except OSError:
            return 0
        for child_name in children:
            removed += _maybe_remove_run_dir(dir_fd, child_name, active_run_id, cutoff)
    finally:
        os.close(dir_fd)
    return removed


def cleanup_old_progress_files(*, retention_days: int, root: Path | None = None, now: float | None = None) -> int:
    progress_dir = progress_root() if root is None else root
    if retention_days <= 0 or not progress_dir.is_dir() or progress_dir.is_symlink():
        return 0
    cutoff = _cutoff_timestamp(retention_days, now)
    removed, clone_dirs = _cleanup_flat_progress_files(progress_dir, cutoff=cutoff)
    clone_dirs.update(_clone_dirs_under(progress_dir))
    for clone_dir in sorted(clone_dirs):
        removed += _cleanup_run_dirs_for_clone(clone_dir, cutoff=cutoff)
    return removed


def progress_note_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress note")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id")
    _ = parser.add_argument("--skill", required=True)
    _ = parser.add_argument("--step", required=True)
    _ = parser.add_argument("text", nargs="+")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    text = " ".join(args.text)
    if args.run_id is None:
        _ = append_breadcrumb(args.repo_root, args.skill, args.step, text)
    else:
        _ = append_breadcrumb_for_run(args.repo_root, args.run_id, args.skill, args.step, text)
    return 0


def progress_activate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress activate")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    try:
        activate_run(args.repo_root, args.run_id)
    except (OSError, TypeError, ValueError) as exc:
        print(f"progress activate failed: {exc}", file=sys.stderr)
        return 2
    return 0


def progress_deactivate_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress deactivate")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    _ = parser.add_argument("--run-id", required=True)
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    _ = deactivate_run(args.repo_root, args.run_id)
    return 0


def progress_clear_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py progress clear")
    _ = parser.add_argument("--repo-root", default=str(Path.cwd()))
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) else 2
    _ = clear_active_run(args.repo_root)
    return 0
