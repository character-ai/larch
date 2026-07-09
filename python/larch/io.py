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
import tempfile
from collections.abc import Iterable, Mapping
from pathlib import Path
from typing import TypeAlias, cast

KvRows: TypeAlias = Mapping[str, object] | Iterable[tuple[str, object]]
_CR_MODES = {"none", "suffix", "rstrip", "strip"}


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


def parse_kv(
    text: str,
    *,
    first_wins: bool = False,
    skip_empty_key: bool = False,
    cr_strip: str = "none",
    strip_value: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    skip_comments: bool = False,
) -> dict[str, str]:
    """Parse already-decoded ``KEY=value`` text into a dict.

    Defaults match the broadest larch envelope grammar: duplicate keys use the
    last value, empty keys are retained, comments are ordinary lines, and RHS
    bytes are not CR-stripped.  Pass ``skip_empty_key=True`` only for callers
    whose old parser rejected ``=value`` rows.
    """
    if cr_strip not in _CR_MODES:
        msg = f"unsupported cr_strip mode: {cr_strip}"
        raise ValueError(msg)
    pattern: re.Pattern[str] | None = re.compile(key_pattern) if isinstance(key_pattern, str) else key_pattern
    allow: set[str] | None = set(allowed_keys) if allowed_keys is not None else None
    out: dict[str, str] = {}
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
        if first_wins and key in out:
            continue
        out[key] = value
    return out


def kv_value(
    *, text: str,
    key: str,
    default: str = "",
    first_match: bool = True,
    cr_strip: str = "none",
) -> str:
    """Return one key's value from decoded ``KEY=value`` text."""
    if cr_strip not in _CR_MODES:
        msg = f"unsupported cr_strip mode: {cr_strip}"
        raise ValueError(msg)
    prefix = f"{key}="
    found = default
    for raw in _line_iter(text):
        if raw.startswith(prefix):
            found = _strip_cr(value=raw[len(prefix) :], mode=cr_strip)
            if first_match:
                return found
    return found


def read_text(path: str | Path, *, default: str | None = None, errors: str = "replace", reject_cr: bool = False) -> str:
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
    *, path: str | Path,
    key: str,
    default: str = "",
    first_match: bool = True,
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
    prefix = f"{key}="
    found: str | None = None
    for raw in _line_iter(text):
        if raw.startswith(prefix):
            value = _strip_cr(value=raw[len(prefix) :], mode=cr_strip)
            if empty_value_means_default and value == "":
                value = default
            if first_match:
                return value
            found = value
    return default if found is None else found


def read_kvs(
    path: str | Path,
    *,
    default: Mapping[str, str] | None = None,
    first_wins: bool = False,
    cr_strip: str = "none",
    skip_comments: bool = False,
    key_pattern: str | re.Pattern[str] | None = None,
    allowed_keys: Iterable[str] | None = None,
    errors: str = "replace",
    reject_cr: bool = False,
    reject_symlink: bool = False,
    on_error_default: bool = False,
) -> dict[str, str]:
    """Read a ``KEY=value`` file into a dict, preserving caller fallbacks."""
    fallback = dict(default or {})
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


def _open_exclusive_text(temp_path: Path, *, nofollow: bool, mode: int | None, newline: str | None):
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
            fd, tmp_name = tempfile.mkstemp(prefix=prefix, suffix=suffix, dir=str(dest.parent), text=True)
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
                with _open_exclusive_text(tmp_path, nofollow=nofollow, mode=mode, newline=newline) as handle:
                    handle.write(text)
            else:
                if nofollow and tmp_path.is_symlink():
                    raise OSError(f"refusing symlink temp: {tmp_path}")
                tmp_path.write_text(text, encoding="utf-8", newline=newline)
                if mode is not None:
                    tmp_path.chmod(mode)
        if nofollow and dest.is_symlink():
            raise OSError(f"refusing to replace symlink: {dest}")
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
    *, path: str | Path,
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
