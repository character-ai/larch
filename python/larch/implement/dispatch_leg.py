# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Subprocess leg execution and process-group management."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import json
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from larch.core import config
from larch.core import process_identity
from larch.implement.dispatch_helpers import _current_cli_path

# Deadline constants used by commit-route composites (defined here as they
# drive leg-timeout sizing and the public outer-timeout constants).
_ACTIVE_LEG_JSON_FILE = config.ACTIVE_LEG_IDENTITY_FILE
_ACTIVE_LEG_PGID_FILE = config.ACTIVE_LEG_LEGACY_PGID_FILE
_CHECKS_DEADLINE_MS = 10_800_000
_COMMIT_ROUTE_DEADLINE_MS = 3_600_000
_STEP5_RESUME_DEADLINE_MS = 21_600_000
_REBASE_CHECKPOINT_DEADLINE_MS = 900_000
_COMPOSITE_OUTER_SLACK_MS = 300_000
CHECKS_COMMIT_ROUTE_OUTER_TIMEOUT_MS = (
    _CHECKS_DEADLINE_MS + _COMMIT_ROUTE_DEADLINE_MS + _REBASE_CHECKPOINT_DEADLINE_MS + _COMPOSITE_OUTER_SLACK_MS
)
CHECKS_STEP5_RESUME_OUTER_TIMEOUT_MS = _CHECKS_DEADLINE_MS + _STEP5_RESUME_DEADLINE_MS + _COMPOSITE_OUTER_SLACK_MS

TIMING_LEDGER_MIN_COLUMNS = 7
_STEP5_RESUME_COMMIT_RELAY_KEYS = ("COMMITTED", "ERROR", "SHA", "COMMIT_OUTCOME", "NEXT_ACTION")
_COMMIT_ROUTE_SUCCESS_OUTCOMES = frozenset({"ok", "noop"})
_COMMIT_ROUTE_FAILURE_LOG_MAX = 12000

CommitRouteOutcome = Literal["continue", "seeded-stall", "seed-failed", "noop"]


@dataclass
class _LegCleanupState:
    active: subprocess.Popen[str] | None = None
    hooks_installed: bool = False
    active_record: dict[str, object] | None = None


_LEG_STATE = _LegCleanupState()


def _timeout_stdout(result: subprocess.TimeoutExpired) -> str:
    output = result.output
    if isinstance(output, bytes):
        return output.decode(errors="replace")
    return output or ""


def _timeout_stderr(result: subprocess.TimeoutExpired) -> str:
    stderr = result.stderr
    if isinstance(stderr, bytes):
        return stderr.decode(errors="replace")
    return stderr or ""


def _active_leg_pgid_path() -> Path | None:
    tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir:
        return None
    return Path(tmpdir) / _ACTIVE_LEG_PGID_FILE


def _active_leg_json_path() -> Path | None:
    tmpdir = os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir:
        return None
    return Path(tmpdir) / _ACTIVE_LEG_JSON_FILE


def _active_leg_kill_log_path(*, implement_tmpdir: str | None = None) -> Path | None:
    tmpdir = implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir:
        return None
    return Path(tmpdir) / config.ACTIVE_LEG_KILL_LOG_FILE


def _legacy_active_leg_pgid_path(*, implement_tmpdir: str | None = None) -> Path | None:
    tmpdir = implement_tmpdir or os.environ.get(config.ENV_IMPLEMENT_TMPDIR, "")
    if not tmpdir:
        return None
    return Path(tmpdir) / _ACTIVE_LEG_PGID_FILE


def _descendants(pid: int) -> list[int]:
    return list(process_identity.collect_descendants(pid=pid))


def _active_leg_owner_token(*, env: dict[str, str] | None = None) -> str:
    if env is not None and env.get(config.ENV_ACTIVE_LEG_OWNER_TOKEN):
        return env[config.ENV_ACTIVE_LEG_OWNER_TOKEN]
    return os.environ.get(config.ENV_ACTIVE_LEG_OWNER_TOKEN, "")


def _expected_signature(argv: Sequence[str]) -> str:
    return " ".join(str(part) for part in argv)


def _publish_active_leg_record(pid: int, *, argv: Sequence[str], env: dict[str, str] | None = None) -> dict[str, object] | None:
    path = _active_leg_json_path()
    if path is None:
        return None
    owner_token = _active_leg_owner_token(env=env)
    identity = process_identity._read_stable_process_identity(  # pylint: disable=protected-access
        pid=pid,
        expected_signature=_expected_signature(argv),
        require_pgid_match=True,
    )
    if identity is None:
        return None
    record: dict[str, object] = {
        "pid": identity.pid,
        "pgid": identity.pgid,
        "start_time": identity.start_time,
        "command_signature": identity.command_signature,
        "expected_signature": identity.expected_signature,
        "owner_token": owner_token,
        "writer_pid": os.getpid(),
        "created_at": time.time(),
    }
    with contextlib.suppress(OSError):
        process_identity.write_identity_record(
            path=path,
            recorded=identity,
            extra={
                "owner_token": owner_token,
                "writer_pid": os.getpid(),
                "created_at": record["created_at"],
            },
        )
    return record


def _publish_active_leg_pgid(pid: int) -> None:
    path = _active_leg_pgid_path()
    if path is None:
        return
    with contextlib.suppress(OSError):
        pgid = os.getpgid(pid)
        path.write_text(f"{pgid}\n", encoding="ascii")


def _clear_active_leg_pgid() -> None:
    path = _active_leg_pgid_path()
    if path is None:
        return
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _record_matches_current(*, current: dict[str, object], expected: dict[str, object] | None) -> bool:
    if expected is None:
        return False
    keys = ("pid", "pgid", "start_time", "command_signature", "owner_token", "writer_pid")
    return all(current.get(key) == expected.get(key) for key in keys)


def _clear_active_leg_record(record: dict[str, object] | None = None) -> None:
    path = _active_leg_json_path()
    if path is None or not path.is_file():
        return
    try:
        current = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    if isinstance(current, dict) and _record_matches_current(current=current, expected=record):
        with contextlib.suppress(OSError):
            path.unlink(missing_ok=True)


def _recorded_identity_from_payload(payload: dict[str, object]) -> process_identity.RecordedProcessIdentity | None:
    try:
        return process_identity.RecordedProcessIdentity(
            pid=int(str(payload["pid"])),
            pgid=int(str(payload["pgid"])),
            start_time=str(payload["start_time"]),
            command_signature=str(payload["command_signature"]),
            expected_signature=str(payload.get("expected_signature", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _log_active_leg_refusal(*, implement_tmpdir: str, reason: str, payload: dict[str, object] | None = None) -> None:
    pid_raw = str(payload.get("pid", "")) if payload else ""
    pgid_raw = str(payload.get("pgid", "")) if payload else ""
    pid = int(pid_raw) if pid_raw.isdigit() else 0
    pgid = int(pgid_raw) if pgid_raw.isdigit() else 0
    process_identity.append_kill_log(
        path=_active_leg_kill_log_path(implement_tmpdir=implement_tmpdir),
        event=process_identity.KillLogEvent(
            event="refusal",
            signal="",
            pid=pid,
            pgid=pgid,
            command=str(payload.get("command_signature", "")) if payload else "",
            caller="implement kill-active-leg",
            reason=reason,
        ),
    )


def _kill_leg_process_group_targets(
    *,
    pgid: int,
    pid: int,
    process: subprocess.Popen[str] | None = None,
    log_path: Path | None = None,
    reason: str = "active-leg-cleanup",
) -> None:
    descendant_pids = _descendants(pid)
    process_identity.append_kill_log(
        path=log_path,
        event=process_identity.KillLogEvent(
            event="signal",
            signal="SIGTERM",
            pid=pid,
            pgid=pgid,
            command="",
            caller="implement leg live-handle cleanup",
            reason=reason,
            descendants=tuple(descendant_pids),
        ),
    )
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGTERM)
    for child in descendant_pids:
        with contextlib.suppress(OSError):
            os.kill(child, signal.SIGTERM)
    if process is not None and process.poll() is None:
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=2)
    else:
        time.sleep(2)
    process_identity.append_kill_log(
        path=log_path,
        event=process_identity.KillLogEvent(
            event="signal",
            signal="SIGKILL",
            pid=pid,
            pgid=pgid,
            command="",
            caller="implement leg live-handle cleanup",
            reason=reason,
            descendants=tuple(descendant_pids),
        ),
    )
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(pgid, signal.SIGKILL)
    kill_pids = list(dict.fromkeys([*descendant_pids, *_descendants(pid)]))
    for child in kill_pids:
        with contextlib.suppress(OSError):
            os.kill(child, signal.SIGKILL)
    if process is not None:
        with contextlib.suppress(subprocess.TimeoutExpired):
            process.wait(timeout=2)


def _kill_leg_process_group(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    pgid: int | None = None
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        pgid = os.getpgid(process.pid)
    if pgid is None:
        return
    _kill_leg_process_group_targets(
        pgid=pgid,
        pid=process.pid,
        process=process,
        log_path=_active_leg_kill_log_path(),
        reason="live-popen-timeout-cleanup",
    )


def kill_active_leg_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement kill-active-leg")
    parser.add_argument("--implement-tmpdir", required=True)
    parser.add_argument("--owner-token", default="")
    args = parser.parse_args(argv)
    _cleanup_legacy_active_leg_pgid(args.implement_tmpdir)
    if not args.owner_token:
        _log_active_leg_refusal(implement_tmpdir=args.implement_tmpdir, reason="missing-owner-token")
        return 0
    _kill_active_leg_json(implement_tmpdir=args.implement_tmpdir, owner_token=args.owner_token)
    return 0


def _kill_active_leg_json(*, implement_tmpdir: str, owner_token: str) -> None:
    json_path = Path(implement_tmpdir) / _ACTIVE_LEG_JSON_FILE
    if not json_path.is_file():
        return
    try:
        payload = json.loads(json_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        _log_active_leg_refusal(implement_tmpdir=implement_tmpdir, reason="malformed-active-leg-record")
        with contextlib.suppress(OSError):
            json_path.unlink(missing_ok=True)
        return
    if not isinstance(payload, dict):
        _log_active_leg_refusal(implement_tmpdir=implement_tmpdir, reason="malformed-active-leg-record")
        with contextlib.suppress(OSError):
            json_path.unlink(missing_ok=True)
        return
    if str(payload.get("owner_token", "")) != owner_token:
        return
    recorded = _recorded_identity_from_payload(payload)
    if recorded is None:
        _log_active_leg_refusal(
            implement_tmpdir=implement_tmpdir,
            reason="malformed-active-leg-record",
            payload=payload,
        )
        with contextlib.suppress(OSError):
            json_path.unlink(missing_ok=True)
        return
    validation = process_identity.terminate_validated_process_group(
        recorded=recorded,
        log_path=_active_leg_kill_log_path(implement_tmpdir=implement_tmpdir),
        caller="implement kill-active-leg",
        reason="owner-token-cleanup",
    )
    if not validation.ok:
        _log_active_leg_refusal(
            implement_tmpdir=implement_tmpdir,
            reason=validation.reason,
            payload=payload,
        )
        return
    with contextlib.suppress(OSError):
        json_path.unlink(missing_ok=True)


def _cleanup_legacy_active_leg_pgid(implement_tmpdir: str) -> None:
    path = _legacy_active_leg_pgid_path(implement_tmpdir=implement_tmpdir)
    if path is None or not path.is_file():
        return
    raw = ""
    with contextlib.suppress(OSError):
        raw = path.read_text(encoding="ascii", errors="replace").strip()
    _log_active_leg_refusal(
        implement_tmpdir=implement_tmpdir,
        reason="legacy-active-leg-pgid-refused",
        payload={"pid": raw, "pgid": raw, "command_signature": ""},
    )
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)


def _kill_active_leg() -> None:
    if _LEG_STATE.active is None:
        return
    active_record = _LEG_STATE.active_record
    _kill_leg_process_group(_LEG_STATE.active)
    _LEG_STATE.active = None
    _LEG_STATE.active_record = None
    _clear_active_leg_record(active_record)


def _leg_signal_handler(signum: int, _frame: object) -> None:  # lint-keyword-only: ok signal handler callback
    _kill_active_leg()
    raise SystemExit(128 + signum)


def _install_leg_cleanup_hooks() -> None:
    if _LEG_STATE.hooks_installed:
        return
    _LEG_STATE.hooks_installed = True
    _ = signal.signal(signal.SIGTERM, _leg_signal_handler)
    _ = signal.signal(signal.SIGINT, _leg_signal_handler)
    _ = atexit.register(_kill_active_leg)


def _drain_leg_pipes(process: subprocess.Popen[str], *, timeout_s: float = 2) -> tuple[str, str]:
    try:
        return process.communicate(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        return "", ""


def _finalize_leg_process(process: subprocess.Popen[str], *, wait_timeout_s: float = 2) -> None:
    for pipe in (process.stdout, process.stderr):
        if pipe is not None:
            with contextlib.suppress(OSError):
                pipe.close()
    with contextlib.suppress(subprocess.TimeoutExpired):
        process.wait(timeout=wait_timeout_s)


def _run_leg_with_timeout(
    *,
    argv: Sequence[str],
    deadline_ms: int,
    label: str,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str] | subprocess.TimeoutExpired:
    _install_leg_cleanup_hooks()
    timeout_s = max(deadline_ms, 1) / 1000
    full_cmd = [sys.executable, str(_current_cli_path()), *argv]
    # pylint: disable-next=consider-using-with
    process = subprocess.Popen(
        full_cmd,
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        start_new_session=True,
    )
    _LEG_STATE.active = process
    _LEG_STATE.active_record = _publish_active_leg_record(process.pid, argv=full_cmd, env=env)
    try:
        try:
            stdout, stderr = process.communicate(timeout=timeout_s)
            return subprocess.CompletedProcess(full_cmd, process.returncode or 0, stdout or "", stderr or "")
        except subprocess.TimeoutExpired as exc:
            _kill_leg_process_group(process)
            stdout, stderr = _drain_leg_pipes(process)
            return subprocess.TimeoutExpired(
                cmd=full_cmd,
                timeout=timeout_s,
                output=stdout or _timeout_stdout(exc),
                stderr=stderr or _timeout_stderr(exc) or f"{label} timed out",
            )
    finally:
        if _LEG_STATE.active is process:
            _LEG_STATE.active = None
        active_record = _LEG_STATE.active_record
        _LEG_STATE.active_record = None
        _finalize_leg_process(process)
        _clear_active_leg_record(active_record)


def _run_cli_capture(
    args: Sequence[str],
    *,
    cwd: Path | None = None,
    env: dict[str, str] | None = None,
    timeout: float | None = None,
) -> subprocess.CompletedProcess[str]:
    if timeout is not None:
        result = _run_leg_with_timeout(
            argv=args,
            cwd=cwd,
            env=env,
            deadline_ms=max(1, int(timeout * 1000)),
            label="cli-capture",
        )
        if isinstance(result, subprocess.TimeoutExpired):
            return subprocess.CompletedProcess(
                list(result.cmd) if isinstance(result.cmd, list) else [str(result.cmd)],
                124,
                _timeout_stdout(result),
                _timeout_stderr(result),
            )
        return result
    return subprocess.run(
        [sys.executable, str(_current_cli_path()), *args],
        cwd=str(cwd) if cwd else None,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
