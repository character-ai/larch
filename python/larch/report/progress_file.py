# pyright: reportUnusedCallResult=false, reportUnusedFunction=false
"""Per-clone progress breadcrumb writer for larch statuslines."""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import os
import re
import stat
import sys
import time
import uuid
from pathlib import Path
from typing import Final

from larch.git.repo_roots import consumer_repo_root
from larch import io as larch_io


PROGRESS_DIRNAME = "progress"
PROGRESS_SUFFIX = ".log"
CURRENT_RUN_FILENAME = "current"
RUN_BREADCRUMB_FILENAME = "breadcrumbs.log"
_HASH_HEX_CHARS = 16
_NEWLINE_CHARS = "\n\r"
_PRINTABLE_ASCII_MIN = 32
_ASCII_DELETE = 127
_C1_CONTROL_MIN = 0x80
_C1_CONTROL_MAX = 0x9F
_RUN_ID_PATTERN: Final[re.Pattern[str]] = re.compile(r"[A-Za-z0-9._-]+")
_CLONE_HASH_PATTERN: Final[re.Pattern[str]] = re.compile(r"[0-9a-f]{16}")


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
    """Append one breadcrumb, returning ``False`` on any best-effort failure."""
    try:
        line = breadcrumb_line(skill=skill, step=step, text=text)
        path = progress_path(repo_root)
        larch_io.assert_no_symlink_path_or_ancestors(path)
        _ensure_directory(path.parent)
        larch_io.assert_no_symlink_path_or_ancestors(path)
        flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
        if hasattr(os, "O_NONBLOCK"):
            flags |= os.O_NONBLOCK
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(path, flags, 0o600)
        try:
            stat_result = os.fstat(fd)
            if not stat.S_ISREG(stat_result.st_mode):
                raise OSError(f"refusing non-regular breadcrumb target: {path}")
            with os.fdopen(fd, "a", encoding="utf-8") as handle:
                fd = -1
                _ = handle.write(line)
        finally:
            if fd >= 0:
                with contextlib.suppress(OSError):
                    os.close(fd)
        with contextlib.suppress(OSError):
            path.chmod(0o600)
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


def _ensure_directory(path: Path) -> None:
    """Create ``path`` and its parents without following symlink swaps."""
    target = path.expanduser()
    if not target.is_absolute():
        target = Path.cwd() / target
    if len(target.parts) == 1:
        return
    current_fd = _open_verified_dir(Path(target.anchor))
    try:
        for part in target.parts[1:]:
            _validate_dir_entry_name(part)
            try:
                next_fd = os.open(part, _dir_open_flags(), dir_fd=current_fd)
            except FileNotFoundError:
                with contextlib.suppress(FileExistsError):
                    os.mkdir(part, 0o777, dir_fd=current_fd)
                next_fd = os.open(part, _dir_open_flags(), dir_fd=current_fd)
            try:
                stat_result = os.fstat(next_fd)
                if not stat.S_ISDIR(stat_result.st_mode):
                    msg = f"refusing non-directory progress path: {target}"
                    raise OSError(msg)
            except OSError:
                os.close(next_fd)
                raise
            os.close(current_fd)
            current_fd = next_fd
    finally:
        os.close(current_fd)


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


def activate_run(repo_root: str | Path, run_id: str) -> None:
    safe_run_id = validate_run_id(run_id)
    clone_dir = progress_clone_dir(repo_root)
    run_dir = run_progress_dir(repo_root, safe_run_id)
    pointer_path = current_run_path(repo_root)
    larch_io.assert_no_symlink_path_or_ancestors(clone_dir)
    larch_io.assert_no_symlink_path_or_ancestors(run_dir)
    larch_io.assert_no_symlink_path_or_ancestors(pointer_path)
    _ensure_directory(clone_dir)
    _ensure_directory(run_dir)
    larch_io.assert_no_symlink_path_or_ancestors(clone_dir)
    larch_io.assert_no_symlink_path_or_ancestors(run_dir)
    larch_io.assert_no_symlink_path_or_ancestors(pointer_path)
    dir_fd = _open_verified_dir(clone_dir)
    try:
        _atomic_write_in_dir(dir_fd, CURRENT_RUN_FILENAME, f"{safe_run_id}\n", mode=0o600, temp_prefix=".current.")
    finally:
        os.close(dir_fd)


def append_breadcrumb_for_run(repo_root: str | Path, run_id: str, skill: str, step: str, text: str) -> bool:
    """Append one run-scoped breadcrumb, returning ``False`` on best-effort failure."""
    try:
        line = breadcrumb_line(skill=skill, step=step, text=text)
        run_dir = run_progress_dir(repo_root, run_id)
        path = run_dir / RUN_BREADCRUMB_FILENAME
        larch_io.assert_no_symlink_path_or_ancestors(path)
        _ensure_directory(run_dir)
        larch_io.assert_no_symlink_path_or_ancestors(path)
        dir_fd = _open_verified_dir(run_dir)
        try:
            _append_line_in_dir(dir_fd, RUN_BREADCRUMB_FILENAME, line)
        finally:
            os.close(dir_fd)
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
