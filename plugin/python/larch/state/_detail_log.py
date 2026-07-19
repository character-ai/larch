"""Failure detail log validation and reading for stall recovery."""

# pyright: reportUnusedCallResult=false
# pyright: reportPrivateUsage=false
# pyright: reportUnusedFunction=false

from __future__ import annotations

import contextlib
import hashlib
import os
import stat
import sys
from pathlib import Path

MAX_OPTIONAL_EVIDENCE_BYTES = 65_536


def _read_optional_evidence(path: Path) -> str:
    if not path.exists() or path.is_symlink() or not path.is_file():
        return ""
    try:
        if path.stat().st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            return ""
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def _failure_detail_log_message(*, suffix: str, flag: str) -> str:
    if suffix == "non-absolute":
        return f"stall-recovery: {flag} must be absolute"
    if suffix == "symlink":
        return f"stall-recovery: {flag} must not be a symlink"
    if suffix in {"outside-tmpdir", "missing", "not-regular-file"}:
        return f"stall-recovery: {flag} outside implement tmpdir"
    if suffix == "oversize":
        return f"stall-recovery: {flag} exceeds 64KiB"
    if suffix == "unreadable":
        return f"stall-recovery: {flag} unreadable"
    return f"stall-recovery: {flag} invalid"


def _emit_failure_detail_log_message(*, suffix: str, flag: str) -> None:
    if suffix:
        print(_failure_detail_log_message(suffix=suffix, flag=flag), file=sys.stderr)


def _open_verify_failure_detail_log(*, path: Path) -> str:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            return "not-regular-file"
        if opened_stat.st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            return "oversize"
    except OSError as exc:
        if exc.errno == getattr(os, "ELOOP", 40):
            return "symlink"
        return "unreadable"
    finally:
        if fd is not None:
            os.close(fd)
    return ""


def _stat_and_open_check(*, path: Path) -> str:
    try:
        stat_result = path.stat()
    except FileNotFoundError:
        return "missing"
    except OSError:
        return "unreadable"
    if not stat.S_ISREG(stat_result.st_mode):
        return "not-regular-file"
    if stat_result.st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
        return "oversize"
    return _open_verify_failure_detail_log(path=path)


def classify_failure_detail_log(*, tmpdir: Path, path: Path) -> str:
    if not path.is_absolute():
        return "non-absolute"
    if path.is_symlink():
        return "symlink"
    try:
        _ = path.resolve(strict=False).relative_to(tmpdir.resolve())
    except (ValueError, OSError):
        return "outside-tmpdir"
    return _stat_and_open_check(path=path)


def validate_failure_detail_log(*, tmpdir: Path, path: Path, flag: str = "--failure-detail-log") -> bool:
    suffix = classify_failure_detail_log(tmpdir=tmpdir, path=path)
    _emit_failure_detail_log_message(suffix=suffix, flag=flag)
    return not suffix


def _materialize_truncated_failure_detail_log(*, tmpdir: Path, path: Path) -> str | None:
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        source_stat = os.fstat(fd)
        if not stat.S_ISREG(source_stat.st_mode):
            return None
        with os.fdopen(fd, "rb") as source:
            fd = None
            prefix = source.read(MAX_OPTIONAL_EVIDENCE_BYTES)
    except OSError:
        return None
    finally:
        if fd is not None:
            os.close(fd)
    digest = hashlib.sha256(
        f"{path.resolve(strict=False)}\0{source_stat.st_size}\0".encode() + prefix,
    ).hexdigest()[:16]
    sidecar = tmpdir / f"stall-recovery-failure-detail-log-{digest}.truncated.log"
    tmp = tmpdir / f".{sidecar.name}.{os.getpid()}.tmp"
    write_fd: int | None = None
    try:
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)
        write_fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(write_fd, "wb") as target:
            write_fd = None
            target.write(prefix)
        tmp.replace(sidecar)
        if classify_failure_detail_log(tmpdir=tmpdir, path=sidecar):
            return None
        return str(sidecar.resolve().relative_to(tmpdir.resolve()))
    except OSError:
        return None
    finally:
        if write_fd is not None:
            os.close(write_fd)
        with contextlib.suppress(OSError):
            tmp.unlink(missing_ok=True)


def _read_validated_failure_detail_log(*, tmpdir: Path, path: Path, flag: str = "--failure-detail-log") -> tuple[str, bool]:
    if not validate_failure_detail_log(tmpdir=tmpdir, path=path, flag=flag):
        return "", False
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd: int | None = None
    try:
        fd = os.open(path, flags)
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            print(f"stall-recovery: {flag} must be regular", file=sys.stderr)
            return "", False
        if st.st_size > MAX_OPTIONAL_EVIDENCE_BYTES:
            print(f"stall-recovery: {flag} exceeds 64KiB", file=sys.stderr)
            return "", False
        with os.fdopen(fd, "rb") as handle:
            fd = None
            return handle.read(MAX_OPTIONAL_EVIDENCE_BYTES).decode("utf-8", errors="replace"), True
    except OSError as exc:
        if exc.errno == getattr(os, "ELOOP", 40):
            print(f"stall-recovery: {flag} must not be a symlink", file=sys.stderr)
        else:
            print(f"stall-recovery: {flag} unreadable", file=sys.stderr)
        return "", False
    finally:
        if fd is not None:
            os.close(fd)


def _failure_detail_log_ledger_fields(*, ledger: Path, fallback: Path, field_name: str) -> list[tuple[str, int, str]]:
    found: list[tuple[str, int, str]] = []
    sequence = 0
    for path in (ledger, fallback):
        if not path.is_file() or path.is_symlink():
            continue
        try:
            rows = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for row in rows:
            sequence += 1
            values: dict[str, str] = {}
            for field in row.split("\t"):
                key, sep, value = field.partition("=")
                if sep:
                    values[key] = value
            value = values.get(field_name, "")
            if value:
                found.append((values.get("utc", ""), sequence, value))
    return found


def _latest_failure_detail_log_sidecar(*, tmpdir: Path, ledger: Path, fallback: Path) -> Path | None:
    candidates: list[tuple[str, int, Path]] = []
    for utc, sequence, value in _failure_detail_log_ledger_fields(
        ledger=ledger,
        fallback=fallback,
        field_name="failure_detail_log",
    ):
        if "\0" in value:
            continue
        rel_path = Path(value)
        if rel_path.is_absolute():
            continue
        candidate = tmpdir / rel_path
        if classify_failure_detail_log(tmpdir=tmpdir, path=candidate):
            continue
        candidates.append((utc, sequence, candidate))
    if not candidates:
        return None
    return max(candidates, key=lambda item: (item[0], item[1]))[2]


def _read_failure_detail_log_with_sidecar_fallback(
    *,
    tmpdir: Path,
    primary: str,
    ledger: Path,
    fallback: Path,
    allow_without_primary: bool = False,
) -> tuple[str, bool, str]:
    if primary:
        detail, valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=Path(primary))
        if valid:
            return detail, True, primary
    elif not allow_without_primary:
        return "", False, ""
    sidecar = _latest_failure_detail_log_sidecar(tmpdir=tmpdir, ledger=ledger, fallback=fallback)
    if sidecar is None:
        return "", False, ""
    detail, valid = _read_validated_failure_detail_log(tmpdir=tmpdir, path=sidecar)
    if not valid:
        return "", False, ""
    return detail, True, str(sidecar.resolve())
