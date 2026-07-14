# ruff: noqa: PLR0913,C901,PLR0912,PLR0915
# pyright: reportUnusedCallResult=false
"""Shared text, KEY=value, and atomic-write helpers for larch.

The helpers preserve the repository's existing ``KEY=value`` wire formats.
Callers choose duplicate-key, carriage-return, empty-key, symlink, and
fallback behavior explicitly so moving code here does not change on-disk or
stdout envelope semantics.
"""

from __future__ import annotations

import contextlib
import os
import re
import shutil
import stat
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import Literal, TypeAlias, cast, overload

KvRows: TypeAlias = Mapping[str, object] | Iterable[tuple[str, object]]
DuplicatePolicy: TypeAlias = Literal["first", "last", "all"]
_CR_MODES = {"none", "suffix", "rstrip", "strip"}
_DUPLICATE_POLICIES = {"first", "last", "all"}


def _duplicate_policy(
    *,
    duplicate_policy: DuplicatePolicy | None,
    legacy_first: bool | None,
    legacy_name: str,
    default: DuplicatePolicy,
    allow_all: bool,
) -> DuplicatePolicy:
    """Resolve a new duplicate policy and its temporary boolean adapter."""
    if duplicate_policy is not None and duplicate_policy not in _DUPLICATE_POLICIES:
        msg = f"unsupported duplicate_policy: {duplicate_policy}"
        raise ValueError(msg)
    if duplicate_policy == "all" and not allow_all:
        msg = "duplicate_policy='all' requires a multi-value codec read"
        raise ValueError(msg)
    if legacy_first is None:
        return duplicate_policy or default
    legacy_policy: DuplicatePolicy = "first" if legacy_first else "last"
    if duplicate_policy is not None and duplicate_policy != legacy_policy:
        msg = (
            f"conflicting duplicate policy: {legacy_name}={legacy_first!r} "
            f"and duplicate_policy={duplicate_policy!r}"
        )
        raise ValueError(msg)
    return duplicate_policy or legacy_policy


def assert_no_symlink_path_or_ancestors(path: Path) -> None:
    """Raise when ``path`` or any ancestor is a symlink."""
    current = path
    while True:
        if current.is_symlink():
            msg = f"refusing symlinked path or ancestor: {current}"
            raise OSError(msg)
        if current == current.parent:
            break
        current = current.parent


def _absolute_lexical(path: Path) -> Path:
    """Return an absolute path without resolving symlinks."""
    return path if path.is_absolute() else Path.cwd() / path


def _assert_contained(*, path: Path, root: Path) -> tuple[Path, Path]:
    absolute_path = _absolute_lexical(path)
    absolute_root = _absolute_lexical(root)
    try:
        absolute_path.relative_to(absolute_root)
    except ValueError as exc:
        raise OSError(f"artifact path escapes trusted root: {path}") from exc
    return absolute_path, absolute_root


def _assert_no_symlink_components(path: Path) -> None:
    current = path
    while True:
        try:
            mode = current.lstat().st_mode
        except FileNotFoundError:
            pass
        else:
            if stat.S_ISLNK(mode):
                raise OSError(f"refusing symlinked path or ancestor: {current}")
        if current == current.parent:
            return
        current = current.parent


def validate_trusted_directory(
    path: str | Path, *, root: str | Path | None = None
) -> Path:
    """Validate a real, non-symlinked artifact directory and its ancestors."""
    directory = _absolute_lexical(Path(path))
    if root is not None:
        _assert_contained(path=directory, root=Path(root))
    _assert_no_symlink_components(directory)
    try:
        mode = directory.lstat().st_mode
    except FileNotFoundError as exc:
        raise OSError(f"trusted artifact directory is missing: {directory}") from exc
    if not stat.S_ISDIR(mode):
        raise OSError(f"trusted artifact root is not a directory: {directory}")
    return directory


def ensure_trusted_directory(
    path: str | Path, *, root: str | Path | None = None, mode: int = 0o700
) -> Path:
    """Create an artifact directory without accepting symlinked components."""
    directory = _absolute_lexical(Path(path))
    if root is not None:
        _assert_contained(path=directory, root=Path(root))
    _assert_no_symlink_components(directory.parent)
    missing: list[Path] = []
    current = directory
    while not current.exists() and not current.is_symlink():
        missing.append(current)
        current = current.parent
    validate_trusted_directory(current)
    for candidate in reversed(missing):
        candidate.mkdir(mode=mode)
        validate_trusted_directory(
            candidate, root=root if candidate == directory else None
        )
    return validate_trusted_directory(directory, root=root)


def _open_trusted_regular(path: Path, *, root: Path) -> int:
    absolute_path, absolute_root = _assert_contained(path=path, root=root)
    validate_trusted_directory(absolute_root)
    _assert_no_symlink_components(absolute_path)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(absolute_path, flags)
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"trusted artifact is not a regular file: {absolute_path}")
        current = absolute_path.stat(follow_symlinks=False)
        if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
            raise OSError(f"trusted artifact changed while opening: {absolute_path}")
        return fd
    except Exception:
        os.close(fd)
        raise


def read_trusted_text(
    path: str | Path,
    *,
    root: str | Path,
    errors: str = "strict",
    reject_cr: bool = False,
) -> str:
    """Read a contained regular file through a validated no-follow descriptor."""
    fd = _open_trusted_regular(Path(path), root=Path(root))
    with os.fdopen(fd, "r", encoding="utf-8", errors=errors, newline="") as handle:
        text = handle.read()
    if reject_cr and "\r" in text:
        raise ValueError(f"carriage return not allowed in {path}")
    return text


def read_trusted_tail(
    path: str | Path, *, root: str | Path, offset: int
) -> tuple[int, bytes]:
    """Read a regular artifact from ``offset`` through a pinned root descriptor."""
    fd = _open_trusted_regular(Path(path), root=Path(root))
    with os.fdopen(fd, "rb") as handle:
        size = os.fstat(handle.fileno()).st_size
        start = 0 if size < offset else offset
        handle.seek(start)
        data = handle.read()
    return start + len(data), data


def trusted_file_present(path: str | Path, *, root: str | Path) -> bool:
    """Return false only for a wholly absent path; reject every unsafe entry."""
    absolute_path, absolute_root = _assert_contained(path=Path(path), root=Path(root))
    validate_trusted_directory(absolute_root)
    _assert_no_symlink_components(absolute_path.parent)
    try:
        mode = absolute_path.lstat().st_mode
    except FileNotFoundError:
        return False
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise OSError(f"trusted artifact is not a regular file: {absolute_path}")
    return True


def trusted_atomic_write(
    path: str | Path,
    text: str,
    *,
    root: str | Path,
    mode: int = 0o600,
    newline: str | None = None,
) -> None:
    """Publish a contained artifact via a descriptor-relative atomic replace."""
    destination, absolute_root = _assert_contained(path=Path(path), root=Path(root))
    root_stat = validate_trusted_directory(absolute_root).stat(follow_symlinks=False)
    validate_trusted_directory(destination.parent, root=absolute_root)
    relative_parent = destination.parent.relative_to(absolute_root)
    directory_flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        directory_flags |= os.O_DIRECTORY
    if hasattr(os, "O_NOFOLLOW"):
        directory_flags |= os.O_NOFOLLOW
    root_fd = os.open(absolute_root, directory_flags)
    parent_fd = root_fd
    try:
        opened_root = os.fstat(root_fd)
        current_root = absolute_root.stat(follow_symlinks=False)
        if (
            (opened_root.st_dev, opened_root.st_ino)
            != (root_stat.st_dev, root_stat.st_ino)
            or (current_root.st_dev, current_root.st_ino)
            != (opened_root.st_dev, opened_root.st_ino)
        ):
            raise OSError(f"trusted artifact root changed while opening: {absolute_root}")
        for component in relative_parent.parts:
            next_fd = os.open(component, directory_flags, dir_fd=parent_fd)
            if parent_fd != root_fd:
                os.close(parent_fd)
            parent_fd = next_fd
        try:
            existing = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        except FileNotFoundError:
            pass
        else:
            if not stat.S_ISREG(existing.st_mode):
                raise OSError(f"trusted artifact is not a regular file: {destination}")
        temp_name = f".{destination.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
        write_flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            write_flags |= os.O_NOFOLLOW
        fd = os.open(temp_name, write_flags, mode, dir_fd=parent_fd)
    except Exception:
        if parent_fd != root_fd:
            os.close(parent_fd)
        os.close(root_fd)
        raise
    published = False
    try:
        opened = os.fstat(fd)
        if not stat.S_ISREG(opened.st_mode):
            raise OSError(f"trusted temporary artifact is not regular: {destination}")
        os.fchmod(fd, mode)
        with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as handle:
            fd = -1
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        current_root = absolute_root.stat(follow_symlinks=False)
        if (current_root.st_dev, current_root.st_ino) != (
            opened_root.st_dev,
            opened_root.st_ino,
        ):
            raise OSError(f"trusted artifact root changed before publication: {absolute_root}")
        os.replace(temp_name, destination.name, src_dir_fd=parent_fd, dst_dir_fd=parent_fd)
        published = True
        final = os.stat(destination.name, dir_fd=parent_fd, follow_symlinks=False)
        if not stat.S_ISREG(final.st_mode):
            raise OSError(f"trusted artifact is not a regular file: {destination}")
    finally:
        if fd >= 0:
            with contextlib.suppress(OSError):
                os.close(fd)
        if not published:
            with contextlib.suppress(OSError):
                os.unlink(temp_name, dir_fd=parent_fd)
        if parent_fd != root_fd:
            with contextlib.suppress(OSError):
                os.close(parent_fd)
        with contextlib.suppress(OSError):
            os.close(root_fd)


def _strip_cr(*, value: str, mode: str) -> str:
    if mode == "none":
        return value
    if mode == "suffix":
        return value.removesuffix("\r")
    if mode == "rstrip":
        return value.rstrip("\r")
    if mode == "strip":
        return value.strip("\r")
    msg = f"unsupported cr_strip mode: {mode}"
    raise ValueError(msg)


def _line_iter(text: str) -> list[str]:
    return [line.removesuffix("\r") for line in text.split("\n")]


def _read_utf8(path: Path, *, errors: str) -> str:
    with path.open("r", encoding="utf-8", errors=errors, newline="") as handle:
        return handle.read()


@overload
def parse_kv(
    text: str,
    *,
    duplicate_policy: Literal["all"],
    first_wins: bool | None = None,
    skip_empty_key: bool = False,
    cr_strip: str = "none",
    strip_value: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    skip_comments: bool = False,
) -> dict[str, list[str]]: ...


@overload
def parse_kv(
    text: str,
    *,
    duplicate_policy: Literal["first", "last"] | None = None,
    first_wins: bool | None = None,
    skip_empty_key: bool = False,
    cr_strip: str = "none",
    strip_value: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    skip_comments: bool = False,
) -> dict[str, str]: ...


def parse_kv(
    text: str,
    *,
    duplicate_policy: DuplicatePolicy | None = None,
    first_wins: bool | None = None,
    skip_empty_key: bool = False,
    cr_strip: str = "none",
    strip_value: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    skip_comments: bool = False,
) -> dict[str, str] | dict[str, list[str]]:
    """Parse already-decoded ``KEY=value`` text into a dict.

    Defaults match the broadest larch envelope grammar: duplicate keys use the
    last value, empty keys are retained, comments are ordinary lines, and RHS
    bytes are not CR-stripped.  Pass ``skip_empty_key=True`` only for callers
    whose old parser rejected ``=value`` rows.
    """
    if cr_strip not in _CR_MODES:
        msg = f"unsupported cr_strip mode: {cr_strip}"
        raise ValueError(msg)
    pattern: re.Pattern[str] | None = (
        re.compile(key_pattern) if isinstance(key_pattern, str) else key_pattern
    )
    allow: set[str] | None = set(allowed_keys) if allowed_keys is not None else None
    policy = _duplicate_policy(
        duplicate_policy=duplicate_policy,
        legacy_first=first_wins,
        legacy_name="first_wins",
        default="last",
        allow_all=True,
    )
    out: dict[str, str] | dict[str, list[str]] = {}
    for raw in _line_iter(text):
        if not raw:
            continue
        if skip_comments and raw.startswith("#"):
            continue
        if "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        if skip_empty_key and not key:
            continue
        if allow is not None and key not in allow:
            continue
        if pattern is not None and pattern.fullmatch(key) is None:
            continue
        value = _strip_cr(value=value, mode=cr_strip)
        if strip_value:
            value = value.strip()
        if policy == "all":
            values = cast("dict[str, list[str]]", out)
            values.setdefault(key, []).append(value)
            continue
        if policy == "first" and key in out:
            continue
        out[key] = value
    return out


def kv_value(
    *,
    text: str,
    key: str,
    default: str = "",
    duplicate_policy: Literal["first", "last"] | None = None,
    first_match: bool | None = None,
    cr_strip: str = "none",
) -> str:
    """Return one key's value from decoded ``KEY=value`` text."""
    if cr_strip not in _CR_MODES:
        msg = f"unsupported cr_strip mode: {cr_strip}"
        raise ValueError(msg)
    policy = _duplicate_policy(
        duplicate_policy=duplicate_policy,
        legacy_first=first_match,
        legacy_name="first_match",
        default="first",
        allow_all=False,
    )
    prefix = f"{key}="
    found = default
    for raw in _line_iter(text):
        if raw.startswith(prefix):
            found = _strip_cr(value=raw[len(prefix) :], mode=cr_strip)
            if policy == "first":
                return found
    return found


def read_text(
    path: str | Path,
    *,
    default: str | None = None,
    errors: str = "replace",
    reject_cr: bool = False,
) -> str:
    """Read UTF-8 text, optionally returning ``default`` when absent.

    ``errors`` is intentionally a read-layer option. ``parse_kv`` receives a
    decoded string and has no decoding policy.
    """
    p = Path(path)
    if default is not None and not p.is_file():
        return default
    text = _read_utf8(p, errors=errors)
    if reject_cr and "\r" in text:
        msg = f"carriage return not allowed in {p}"
        raise ValueError(msg)
    return text


def read_kv(
    *,
    path: str | Path,
    key: str,
    default: str = "",
    duplicate_policy: Literal["first", "last"] | None = None,
    first_match: bool | None = None,
    cr_strip: str = "none",
    errors: str = "replace",
    on_error_default: bool = False,
    empty_value_means_default: bool = False,
    reject_symlink: bool = False,
) -> str:
    """Read one ``KEY=value`` entry from a file with caller-selected policy."""
    p = Path(path)
    if reject_symlink and p.is_symlink():
        return default
    if not p.is_file():
        return default
    try:
        text = _read_utf8(p, errors=errors)
    except (OSError, UnicodeError):
        if on_error_default:
            return default
        raise
    policy = _duplicate_policy(
        duplicate_policy=duplicate_policy,
        legacy_first=first_match,
        legacy_name="first_match",
        default="first",
        allow_all=False,
    )
    prefix = f"{key}="
    found: str | None = None
    for raw in _line_iter(text):
        if raw.startswith(prefix):
            value = _strip_cr(value=raw[len(prefix) :], mode=cr_strip)
            if empty_value_means_default and value == "":
                value = default
            if policy == "first":
                return value
            found = value
    return default if found is None else found


@overload
def read_kvs(
    path: str | Path,
    *,
    duplicate_policy: Literal["all"],
    default: Mapping[str, list[str]] | None = None,
    first_wins: bool | None = None,
    cr_strip: str = "none",
    skip_comments: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    errors: str = "replace",
    reject_cr: bool = False,
    reject_symlink: bool = False,
    on_error_default: bool = False,
) -> dict[str, list[str]]: ...


@overload
def read_kvs(
    path: str | Path,
    *,
    duplicate_policy: Literal["first", "last"] | None = None,
    default: Mapping[str, str] | None = None,
    first_wins: bool | None = None,
    cr_strip: str = "none",
    skip_comments: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    errors: str = "replace",
    reject_cr: bool = False,
    reject_symlink: bool = False,
    on_error_default: bool = False,
) -> dict[str, str]: ...


def read_kvs(
    path: str | Path,
    *,
    default: Mapping[str, str] | Mapping[str, list[str]] | None = None,
    duplicate_policy: DuplicatePolicy | None = None,
    first_wins: bool | None = None,
    cr_strip: str = "none",
    skip_comments: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    errors: str = "replace",
    reject_cr: bool = False,
    reject_symlink: bool = False,
    on_error_default: bool = False,
) -> dict[str, str] | dict[str, list[str]]:
    """Read a ``KEY=value`` file into a dict, preserving caller fallbacks."""
    fallback = cast("dict[str, str] | dict[str, list[str]]", dict(default or {}))
    p = Path(path)
    if reject_symlink and p.is_symlink():
        return fallback
    if not p.is_file():
        return fallback
    try:
        text = _read_utf8(p, errors=errors)
    except (OSError, UnicodeError):
        if on_error_default:
            return fallback
        raise
    if reject_cr and "\r" in text:
        msg = f"carriage return not allowed in {p}"
        raise ValueError(msg)
    return parse_kv(
        text,
        duplicate_policy=duplicate_policy,
        first_wins=first_wins,
        cr_strip=cr_strip,
        skip_comments=skip_comments,
        key_pattern=key_pattern,
        allowed_keys=allowed_keys,
    )


def format_kvs(values: KvRows, *, sort_keys: bool = False) -> str:
    r"""Format mapping or tuple rows as ``KEY=value\n`` without changing order."""
    if isinstance(values, Mapping):
        mapping = cast("Mapping[str, object]", values)
        rows = list(mapping.items())
    else:
        rows = list(values)
    if sort_keys:
        rows = sorted(rows, key=lambda item: str(item[0]))
    return "".join(f"{key}={value}\n" for key, value in rows)


def _temp_path(*, path: Path, temp_name: str | Path | None, suffix: str) -> Path:
    if temp_name is None:
        return path.with_name(path.name + suffix)
    temp = Path(temp_name)
    if temp.is_absolute() or temp.parent != Path():
        return temp
    return path.with_name(str(temp))


def _open_exclusive_text(
    temp_path: Path, *, nofollow: bool, mode: int | None, newline: str | None
):
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if nofollow and hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(temp_path, flags, 0o600 if mode is None else mode)
    try:
        if mode is not None:
            os.fchmod(fd, mode)
        return os.fdopen(fd, "w", encoding="utf-8", newline=newline)
    except Exception:
        os.close(fd)
        raise


def atomic_write(  # lint-keyword-only: ok shared write helper supports legacy positional path/text calls
    path: str | Path,
    text: str,
    *,
    create_parent: bool = True,
    mode: int | None = None,
    prefix: str | None = None,
    suffix: str = ".tmp",
    temp_name: str | Path | None = None,
    replace_method: str = "replace",
    nofollow: bool = False,
    exclusive: bool = False,
    newline: str | None = None,
) -> None:
    """Atomically write UTF-8 text with configurable legacy temp behavior.

    ``replace_method='move'`` preserves callers that historically used
    ``shutil.move``.  ``exclusive`` uses ``O_CREAT|O_EXCL`` and pre-unlinks a
    fixed stale temp after refusing symlink temps when ``nofollow`` is set.
    """
    dest = Path(path)
    if nofollow:
        check_dest = dest.expanduser()
        if not check_dest.is_absolute():
            check_dest = Path.cwd() / check_dest
        assert_no_symlink_path_or_ancestors(check_dest)
    if create_parent:
        dest.parent.mkdir(parents=True, exist_ok=True)
    if nofollow and dest.is_symlink():
        raise OSError(f"refusing to write through symlink: {dest}")
    if replace_method not in {"replace", "move"}:
        msg = f"unsupported replace_method: {replace_method}"
        raise ValueError(msg)

    tmp_path: Path | None = None
    tmp_name: str | None = None
    fd: int | None = None
    fixed_temp = temp_name is not None or prefix is None
    try:
        if prefix is not None and temp_name is None:
            fd, tmp_name = tempfile.mkstemp(
                prefix=prefix, suffix=suffix, dir=str(dest.parent), text=True
            )
            tmp_path = Path(tmp_name)
            if nofollow and tmp_path.is_symlink():
                raise OSError(f"refusing symlink temp: {tmp_path}")
            with os.fdopen(fd, "w", encoding="utf-8", newline=newline) as handle:
                fd = None
                handle.write(text)
            if mode is not None:
                tmp_path.chmod(mode)
        else:
            tmp_path = _temp_path(path=dest, temp_name=temp_name, suffix=suffix)
            if exclusive and fixed_temp:
                if nofollow and tmp_path.is_symlink():
                    raise OSError(f"refusing symlink temp: {tmp_path}")
                with contextlib.suppress(FileNotFoundError):
                    tmp_path.unlink()
                with _open_exclusive_text(
                    tmp_path, nofollow=nofollow, mode=mode, newline=newline
                ) as handle:
                    handle.write(text)
            else:
                if nofollow and tmp_path.is_symlink():
                    raise OSError(f"refusing symlink temp: {tmp_path}")
                tmp_path.write_text(text, encoding="utf-8", newline=newline)
                if mode is not None:
                    tmp_path.chmod(mode)
        if nofollow and dest.is_symlink():
            raise OSError(f"refusing to replace symlink: {dest}")
        if nofollow:
            check_dest = dest.expanduser()
            if not check_dest.is_absolute():
                check_dest = Path.cwd() / check_dest
            assert_no_symlink_path_or_ancestors(check_dest)
        if replace_method == "move":
            shutil.move(str(tmp_path), str(dest))
        else:
            tmp_path.replace(dest)
    except Exception:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if tmp_path is not None and not tmp_path.is_symlink():
            with contextlib.suppress(OSError):
                tmp_path.unlink()
        raise


def write_text(*, path: str | Path, text: str, create_parent: bool = True) -> None:
    """Write UTF-8 text, creating the parent by default."""
    p = Path(path)
    if create_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")


def append_text(*, path: str | Path, text: str, create_parent: bool = True) -> None:
    """Append UTF-8 text, creating the parent by default."""
    p = Path(path)
    if create_parent:
        p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as handle:
        handle.write(text)


def write_kvs(
    *,
    path: str | Path,
    values: KvRows,
    sort_keys: bool = False,
    atomic: bool = True,
    create_parent: bool = True,
    mode: int | None = None,
) -> None:
    """Write ``KEY=value`` rows and raise ``OSError`` on failure."""
    text = format_kvs(values, sort_keys=sort_keys)
    if atomic:
        atomic_write(path=path, text=text, create_parent=create_parent, mode=mode)
    else:
        p = Path(path)
        if create_parent:
            p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
        if mode is not None:
            p.chmod(mode)
