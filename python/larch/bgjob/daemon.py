"""Daemon process implementation for bgjob."""

from __future__ import annotations

import contextlib
import os
import subprocess
import time
from pathlib import Path

from larch import io as larch_io
from larch.bgjob import model, registry
from larch.core import config, process_identity


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
    candidate = raw_owner_pid or os.environ.get(config.ENV_BGJOB_OWNER_PID, "") or os.environ.get(
        "LARCH_BG_POLL_GUARD_SESSION_PID", ""
    )
    return model.OwnerIdentity(recorded=_read_owner_identity(candidate))


def _safe_rows(rows: list[tuple[str, object]]) -> list[tuple[str, str]]:
    return [(key, model.reject_line_value(value, label=key)) for key, value in rows]


def _merge_rows(path: Path | None) -> list[tuple[str, str]]:
    if path is None or path.is_symlink() or not path.is_file():
        return []
    rows = larch_io.read_kvs(path, reject_symlink=True, on_error_default=True, reject_cr=True)
    return [(key, model.reject_line_value(value, label=key)) for key, value in rows.items()]


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
        sentinel.parent.mkdir(parents=True, exist_ok=True)
        if not sentinel.is_symlink():
            with contextlib.suppress(OSError):
                _ = sentinel.write_text("", encoding="utf-8")


def _terminate_child_group(child: process_identity.RecordedProcessIdentity, *, reason: str) -> None:
    _ = process_identity.terminate_validated_process_group(
        recorded=child,
        log_path=None,
        caller="bgjob-daemon",
        reason=reason,
    )


def _monitor(spec: model.JobSpec, child: subprocess.Popen[bytes]) -> int:
    child_identity = _capture_identity(child.pid, expected_signature=" ".join(spec.command[:2]))
    daemon_identity = _capture_identity(os.getpid())
    entry = model.RegistryEntry(
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
        stdout_log=spec.log_dir / f"{spec.step}.stdout.log",
        stderr_log=spec.log_dir / f"{spec.step}.stderr.log",
        result_env=model.result_env_path(tmpdir=spec.tmpdir, step=spec.step),
    )
    reg_path = registry.write_entry(entry)
    start = time.monotonic()
    owner_missing_since: float | None = None
    rc_token = "0"
    while True:
        rc = child.poll()
        if rc is not None:
            rc_token = str(rc)
            break
        elapsed = time.monotonic() - start
        if elapsed >= spec.budget_s:
            _terminate_child_group(child_identity, reason="timeout")
            rc_token = config.BGJOB_RC_TIMEOUT
            break
        if spec.owner.recorded is not None:
            owner_validation = process_identity.validate_process_identity(recorded=spec.owner.recorded)
            if owner_validation.ok:
                owner_missing_since = None
            elif owner_missing_since is None:
                owner_missing_since = time.monotonic()
            elif time.monotonic() - owner_missing_since >= config.BGJOB_OWNER_GRACE_S:
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
    stdout_log = spec.log_dir / f"{spec.step}.stdout.log"
    stderr_log = spec.log_dir / f"{spec.step}.stderr.log"
    with stdout_log.open("ab") as stdout_handle, stderr_log.open("ab") as stderr_handle:
        child = subprocess.Popen(  # lint-subprocess-via-runner: ok bgjob daemon intentionally owns the long-running child process group
            spec.command,
            stdout=stdout_handle,
            stderr=stderr_handle,
            start_new_session=True,
        )
        _ = os.write(pipe_fd, f"{child.pid} {os.getpgid(child.pid)}\n".encode())
        _ = os.close(pipe_fd)
        return _monitor(spec, child)


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
