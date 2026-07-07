"""Registry storage for bgjob daemons."""

from __future__ import annotations

import contextlib
import stat
import time
from pathlib import Path

from larch import io as larch_io
from larch.bgjob import model
from larch.core import process_identity


def _identity_rows(prefix: str, identity: process_identity.RecordedProcessIdentity | None) -> list[tuple[str, str]]:
    if identity is None:
        return []
    return [
        (f"{prefix}_PID", str(identity.pid)),
        (f"{prefix}_PGID", str(identity.pgid)),
        (f"{prefix}_START_TIME", identity.start_time),
        (f"{prefix}_COMMAND", identity.command_signature),
        (f"{prefix}_EXPECTED", identity.expected_signature),
    ]


def _parse_identity(rows: dict[str, str], prefix: str) -> process_identity.RecordedProcessIdentity | None:
    try:
        return process_identity.RecordedProcessIdentity(
            pid=int(rows[f"{prefix}_PID"]),
            pgid=int(rows[f"{prefix}_PGID"]),
            start_time=rows[f"{prefix}_START_TIME"],
            command_signature=rows[f"{prefix}_COMMAND"],
            expected_signature=rows.get(f"{prefix}_EXPECTED", ""),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _validated_path(path: Path, *, root: Path) -> Path | None:
    if path.is_symlink():
        return None
    try:
        resolved = path.resolve()
    except OSError:
        return None
    try:
        _ = resolved.relative_to(root.resolve())
    except ValueError:
        return None
    with contextlib.suppress(OSError):
        if path.exists() and not stat.S_ISREG(path.stat().st_mode):
            return None
    return resolved


def _resolved_dir(raw: str) -> Path | None:
    candidate = Path(raw)
    if candidate.is_symlink():
        return None
    resolved = candidate.resolve()
    if not resolved.is_dir():
        return None
    return resolved


def _dirs_from_rows(rows: dict[str, str]) -> tuple[Path, Path] | None:
    tmpdir = _resolved_dir(rows["TMPDIR"])
    log_dir = _resolved_dir(rows["LOG_DIR"])
    if tmpdir is None or log_dir is None:
        return None
    try:
        _ = log_dir.relative_to(tmpdir)
    except ValueError:
        return None
    return tmpdir, log_dir


def write_entry(entry: model.RegistryEntry) -> Path:
    path = model.registry_path(run_id=entry.run_id, step=entry.step)
    rows: list[tuple[str, str]] = [
        ("STEP", entry.step),
        ("RUN_ID", entry.run_id),
        ("TMPDIR", str(entry.tmpdir)),
        ("LOG_DIR", str(entry.log_dir)),
        ("CLONE_PATH", str(entry.clone_path)),
        ("START_EPOCH", str(entry.start_epoch)),
        ("BUDGET_S", str(entry.budget_s)),
        ("STDOUT_LOG", str(entry.stdout_log)),
        ("STDERR_LOG", str(entry.stderr_log)),
        ("RESULT_ENV", str(entry.result_env)),
    ]
    rows.extend(_identity_rows("DAEMON", entry.daemon))
    rows.extend(_identity_rows("CHILD", entry.child))
    rows.extend(_identity_rows("OWNER", entry.owner))
    safe_rows = [(key, model.reject_line_value(value, label=key)) for key, value in rows]
    larch_io.atomic_write(path=path, text=larch_io.format_kvs(safe_rows), nofollow=True, mode=0o600)
    return path


def read_entry(path: Path) -> model.RegistryEntry | None:
    if path.is_symlink() or not path.is_file():
        return None
    rows = larch_io.read_kvs(path, reject_symlink=True, on_error_default=True)
    daemon = _parse_identity(rows, "DAEMON")
    child = _parse_identity(rows, "CHILD")
    if daemon is None or child is None:
        return None
    try:
        dirs = _dirs_from_rows(rows)
        if dirs is None:
            return None
        tmpdir, log_dir = dirs
        stdout_log = _validated_path(Path(rows["STDOUT_LOG"]), root=log_dir)
        stderr_log = _validated_path(Path(rows["STDERR_LOG"]), root=log_dir)
        result_env = _validated_path(Path(rows["RESULT_ENV"]), root=model.bgjob_dir(tmpdir))
        if stdout_log is None or stderr_log is None or result_env is None:
            return None
        return model.RegistryEntry(
            step=model.validate_slug(rows["STEP"], label="step"),
            run_id=model.validate_slug(rows["RUN_ID"], label="run-id"),
            tmpdir=tmpdir,
            log_dir=log_dir,
            clone_path=Path(rows.get("CLONE_PATH", ".")).resolve(),
            daemon=daemon,
            child=child,
            owner=_parse_identity(rows, "OWNER"),
            start_epoch=int(rows["START_EPOCH"]),
            budget_s=int(rows["BUDGET_S"]),
            stdout_log=stdout_log,
            stderr_log=stderr_log,
            result_env=result_env,
        )
    except (KeyError, TypeError, ValueError, OSError):
        return None


def read_for(*, tmpdir: Path, step: str, run_id: str | None = None) -> tuple[Path, model.RegistryEntry | None]:
    clone_path = Path.cwd().resolve()
    active_run_id = run_id or model.default_run_id(tmpdir=tmpdir, clone_path=clone_path)
    path = model.registry_path(run_id=active_run_id, step=step)
    return path, read_entry(path)


def iter_entries() -> list[tuple[Path, model.RegistryEntry | None]]:
    root = model.registry_root()
    entries: list[tuple[Path, model.RegistryEntry | None]] = []
    for path in sorted(root.glob("*.env")):
        if path.is_symlink() or not path.is_file():
            continue
        entries.append((path, read_entry(path)))
    return entries


def unlink_entry(path: Path) -> None:
    if path.is_symlink():
        return
    with contextlib.suppress(FileNotFoundError):
        path.unlink()


def child_liveness(entry: model.RegistryEntry) -> model.LivenessVerdict:
    validation = process_identity.validate_process_identity(recorded=entry.child)
    if validation.ok:
        return model.LivenessVerdict(live=True, reason="ok")
    return model.LivenessVerdict(live=False, reason=validation.reason)


def daemon_liveness(entry: model.RegistryEntry) -> model.LivenessVerdict:
    validation = process_identity.validate_process_identity(recorded=entry.daemon)
    if validation.ok:
        return model.LivenessVerdict(live=True, reason="ok")
    return model.LivenessVerdict(live=False, reason=validation.reason)


def entry_expired(entry: model.RegistryEntry) -> bool:
    return time.time() - entry.start_epoch > entry.budget_s
