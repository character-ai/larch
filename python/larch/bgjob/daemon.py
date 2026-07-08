"""Daemon process implementation for bgjob."""

from __future__ import annotations

import contextlib
import os
import re
import signal
import subprocess
import stat
import time
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

from larch import io as larch_io
from larch.bgjob import model, registry
from larch.core import config, process_identity, redact

_PACKED_ROW_TOKEN_RE = re.compile(r"[A-Z0-9_]+=.*")
_MIN_PACKED_ROW_TOKENS = 2


@dataclass(frozen=True)
class OwnerValidationState:
    missing_since: float | None = None
    failure_count: int = 0


@dataclass(frozen=True)
class OwnerValidationStep:
    state: OwnerValidationState
    orphaned: bool
    validation: process_identity.ValidationResult | None = None


def _capture_identity(pid: int, *, expected_signature: str = "") -> process_identity.RecordedProcessIdentity:
    deadline = time.monotonic() + 5.0
    while time.monotonic() < deadline:
        identity = process_identity.read_process_identity(pid=pid, expected_signature=expected_signature)
        if identity is not None:
            return identity
        time.sleep(0.05)
    msg = f"could not capture process identity for pid {pid}"
    raise RuntimeError(msg)


def _read_owner_identity(raw_pid: str) -> process_identity.RecordedProcessIdentity | None:
    if not raw_pid or not raw_pid.isdigit():
        return None
    return process_identity.read_process_identity(pid=int(raw_pid))


def owner_identity_from_env(raw_owner_pid: str | None) -> model.OwnerIdentity:
    candidate = (
        raw_owner_pid
        or os.environ.get(config.ENV_BGJOB_OWNER_PID, "")
        or os.environ.get("LARCH_CLAUDE_PID", "")
        or os.environ.get(config.ENV_CLAUDE_PID, "")
        or os.environ.get("LARCH_BG_POLL_GUARD_SESSION_PID", "")
    )
    if candidate:
        recorded = _read_owner_identity(candidate)
        if recorded is None:
            raise RuntimeError(f"could not capture process identity for owner pid {candidate}")
        return model.OwnerIdentity(recorded=recorded)
    raise RuntimeError("could not capture process identity for owner pid: missing session owner pid")


def _safe_rows(rows: list[tuple[str, object]]) -> list[tuple[str, str]]:
    return [(key, model.reject_line_value(value, label=key)) for key, value in rows]


def _merge_rows(path: Path | None) -> list[tuple[str, str]]:
    if path is None or path.is_symlink() or not path.is_file():
        return []
    try:
        text = larch_io.read_text(path, reject_cr=True)
    except (OSError, UnicodeError):
        return []
    reserved = {config.BGJOB_RC_KEY, config.BGJOB_ELAPSED_KEY, "STEP"}
    merged = {
        key: value
        for key, value in larch_io.read_kvs(path, reject_symlink=True, on_error_default=True, reject_cr=True).items()
        if key and key not in reserved
    }
    for line in text.splitlines():
        if line.count("=") < _MIN_PACKED_ROW_TOKENS:
            continue
        tokens = line.split()
        if len(tokens) < _MIN_PACKED_ROW_TOKENS or any(_PACKED_ROW_TOKEN_RE.fullmatch(token) is None for token in tokens):
            continue
        for token in tokens:
            key, value = token.split("=", 1)
            if not key or key in reserved:
                continue
            merged[key] = model.reject_line_value(value, label=key)
    return list(merged.items())


def write_result(*, spec: model.JobSpec, rc: str, elapsed_s: int) -> None:
    result = model.result_env_path(tmpdir=spec.tmpdir, step=spec.step)
    result.parent.mkdir(parents=True, exist_ok=True)
    rows: list[tuple[str, object]] = [
        (config.BGJOB_RC_KEY, rc),
        (config.BGJOB_ELAPSED_KEY, str(elapsed_s)),
        ("STEP", spec.step),
    ]
    rows.extend(_merge_rows(spec.merge_result_env))
    larch_io.atomic_write(path=result, text=larch_io.format_kvs(_safe_rows(rows)), nofollow=True, mode=0o600)
    for sentinel in spec.sentinel_paths:
        safe_sentinel = model.ensure_under(sentinel, spec.tmpdir, label="sentinel")
        larch_io.atomic_write(path=safe_sentinel, text="", nofollow=True, mode=0o600)


def _terminate_child_group(child: process_identity.RecordedProcessIdentity, *, reason: str) -> None:
    _ = process_identity.terminate_validated_process_group(
        recorded=child,
        log_path=None,
        caller="bgjob-daemon",
        reason=reason,
    )


def _append_orphan_diagnostic(
    *,
    spec: model.JobSpec,
    validation: process_identity.ValidationResult,
    failure_count: int,
) -> None:
    stderr_log = spec.log_dir / f"{spec.step}.stderr.log"
    current = validation.current
    rows: list[tuple[str, object]] = [
        ("BGJOB_ORPHAN_REASON", validation.reason),
        ("OWNER_PID", spec.owner.recorded.pid if spec.owner.recorded is not None else ""),
        ("OWNER_FAILURE_COUNT", failure_count),
    ]
    if current is not None:
        rows.extend(
            [
                ("OWNER_CURRENT_PGID", current.pgid),
                ("OWNER_CURRENT_START_TIME", current.start_time),
                ("OWNER_CURRENT_COMMAND", process_identity.bounded_command(current.command_signature)),
            ]
        )
    with contextlib.suppress(OSError, TypeError, UnicodeError, ValueError):
        spec.log_dir.mkdir(parents=True, exist_ok=True)
        safe_rows = _safe_rows(rows)
        text = redact.redact_outbound(larch_io.format_kvs(safe_rows))
        with _open_verified_log_handle(stderr_log, root=spec.log_dir) as handle:
            _ = handle.write(text.encode("utf-8"))


def _open_verified_log_handle(path: Path, *, root: Path) -> BinaryIO:
    if root.is_symlink() or not root.is_dir():
        raise ValueError(f"log root must be a regular directory: {root}")
    verified_root = root.resolve()
    verified_path = model.ensure_under(path, verified_root, label="log file")
    if path.is_symlink():
        raise ValueError(f"log file must not be a symlink: {path}")
    flags = os.O_WRONLY | os.O_APPEND | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(verified_path, flags, 0o600)
    try:
        opened_stat = os.fstat(fd)
        if not stat.S_ISREG(opened_stat.st_mode):
            raise ValueError(f"log file must be regular: {path}")
        return os.fdopen(fd, "ab")
    except Exception:
        with contextlib.suppress(OSError):
            os.close(fd)
        raise


def _check_owner_validation(
    *,
    spec: model.JobSpec,
    state: OwnerValidationState,
    now: float,
) -> OwnerValidationStep:
    if spec.owner.recorded is None:
        return OwnerValidationStep(state=state, orphaned=False)
    validation = process_identity.validate_process_identity(recorded=spec.owner.recorded)
    if validation.ok:
        return OwnerValidationStep(state=OwnerValidationState(), orphaned=False, validation=validation)
    failure_count = state.failure_count + 1
    failure_threshold = max(1, config.BGJOB_OWNER_VALIDATION_FAILURE_THRESHOLD)
    if failure_count < failure_threshold:
        next_state = OwnerValidationState(missing_since=None, failure_count=failure_count)
        return OwnerValidationStep(state=next_state, orphaned=False, validation=validation)
    missing_since = now if state.missing_since is None else state.missing_since
    next_state = OwnerValidationState(missing_since=missing_since, failure_count=failure_count)
    return OwnerValidationStep(
        state=next_state,
        orphaned=now - missing_since >= config.BGJOB_OWNER_GRACE_S,
        validation=validation,
    )


def _monitor(spec: model.JobSpec, child: subprocess.Popen[bytes], child_identity: process_identity.RecordedProcessIdentity, reg_path: Path) -> int:
    start = time.monotonic()
    owner_state = OwnerValidationState()
    rc_token = "0"
    while True:
        now = time.monotonic()
        rc = child.poll()
        if rc is not None:
            rc_token = str(rc)
            break
        elapsed = now - start
        if elapsed >= spec.budget_s:
            _terminate_child_group(child_identity, reason="timeout")
            rc_token = config.BGJOB_RC_TIMEOUT
            break
        owner_step = _check_owner_validation(spec=spec, state=owner_state, now=now)
        owner_state = owner_step.state
        if owner_step.orphaned and owner_step.validation is not None:
            _append_orphan_diagnostic(
                spec=spec,
                validation=owner_step.validation,
                failure_count=owner_step.state.failure_count,
            )
            _terminate_child_group(child_identity, reason="orphaned")
            rc_token = config.BGJOB_RC_ORPHANED
            break
        time.sleep(config.BGJOB_DAEMON_POLL_INTERVAL_S)
    elapsed_s = int(time.monotonic() - start)
    if rc_token in {config.BGJOB_RC_TIMEOUT, config.BGJOB_RC_ORPHANED}:
        with contextlib.suppress(Exception):
            _ = child.wait(timeout=5)
    write_result(spec=spec, rc=rc_token, elapsed_s=elapsed_s)
    registry.unlink_entry(reg_path)
    return 0


def _daemon_child(spec: model.JobSpec, pipe_fd: int) -> int:
    os.setsid()
    spec.log_dir.mkdir(parents=True, exist_ok=True)
    result = model.result_env_path(tmpdir=spec.tmpdir, step=spec.step)
    result.parent.mkdir(parents=True, exist_ok=True)
    with contextlib.suppress(OSError):
        result.unlink()
    stdout_log = spec.log_dir / f"{spec.step}.stdout.log"
    stderr_log = spec.log_dir / f"{spec.step}.stderr.log"
    child: subprocess.Popen[bytes] | None = None
    child_identity: process_identity.RecordedProcessIdentity | None = None
    reg_path: Path | None = None
    pipe_closed = False
    pgid = 0
    try:
        with _open_verified_log_handle(stdout_log, root=spec.log_dir) as stdout_handle, _open_verified_log_handle(
            stderr_log, root=spec.log_dir
        ) as stderr_handle:
            try:
                child = subprocess.Popen(  # lint-subprocess-via-runner: ok bgjob daemon intentionally owns the long-running child process group  # pylint: disable=consider-using-with
                    spec.command,
                    stdout=stdout_handle,
                    stderr=stderr_handle,
                    start_new_session=True,
                )
                child_identity = _capture_identity(child.pid, expected_signature=" ".join(spec.command[:2]))
                daemon_identity = _capture_identity(os.getpid())
                reg_path = registry.write_entry(
                    model.RegistryEntry(
                        step=spec.step,
                        run_id=spec.run_id,
                        tmpdir=spec.tmpdir,
                        log_dir=spec.log_dir,
                        clone_path=Path.cwd().resolve(),
                        daemon=daemon_identity,
                        child=child_identity,
                        owner=spec.owner.recorded,
                        start_epoch=int(time.time()),
                        budget_s=spec.budget_s,
                        stdout_log=stdout_log,
                        stderr_log=stderr_log,
                        result_env=result,
                    )
                )
                pgid = os.getpgid(child.pid)
                _ = os.write(pipe_fd, f"{child.pid} {pgid}\n".encode())
                _ = os.close(pipe_fd)
                pipe_closed = True
                return _monitor(spec, child, child_identity, reg_path)
            except Exception:
                if child_identity is not None:
                    _terminate_child_group(child_identity, reason="startup-failed")
                elif child is not None:
                    with contextlib.suppress(Exception):
                        _ = os.killpg(child.pid, signal.SIGKILL)
                if child is not None:
                    with contextlib.suppress(Exception):
                        _ = child.wait(timeout=5)
                if reg_path is not None:
                    registry.unlink_entry(reg_path)
                raise
    finally:
        if not pipe_closed:
            with contextlib.suppress(OSError):
                _ = os.close(pipe_fd)


def start_daemon(spec: model.JobSpec) -> int:
    read_fd, write_fd = os.pipe()
    pid = os.fork()
    if pid == 0:
        _ = os.close(read_fd)
        with contextlib.suppress(BaseException):
            rc = _daemon_child(spec, write_fd)
            os._exit(rc)
        os._exit(2)
    _ = os.close(write_fd)
    with os.fdopen(read_fd, "rb") as handle:
        line = handle.readline().decode("utf-8", errors="replace").strip()
    if not line:
        return 2
    parts = line.split()
    if len(parts) != config.BGJOB_START_PIPE_PARTS:
        return 2
    print(f"{config.BGJOB_STATUS_KEY}={config.BGJOB_STATUS_STARTED} STEP={spec.step} PGID={parts[1]}")
    return 0
