"""Process identity checks for persisted pid/pgid signal targets."""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import signal
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from larch import io as larch_io
from larch.core import config, proc, redact

PS_LSTART_FIELD_COUNT = 5
COMMAND_LOG_LIMIT = 500
PROCESS_IDENTITY_CAPTURE_ATTEMPTS = 10
PROCESS_IDENTITY_CAPTURE_SLEEP_S = 0.05
DESIGN_STEP3_MISSING_PID_GRACE_S = 5.0


@dataclass(frozen=True)
class RecordedProcessIdentity:
    pid: int
    pgid: int
    start_time: str
    command_signature: str
    expected_signature: str = ""


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str
    current: RecordedProcessIdentity | None = None


@dataclass(frozen=True)
class KillTargetSnapshot:
    pid: int
    pgid: int
    descendants: tuple[int, ...]
    command: str


@dataclass(frozen=True)
class KillLogEvent:
    event: str
    signal: str
    pid: int
    pgid: int
    command: str
    caller: str
    reason: str
    descendants: tuple[int, ...] = ()
    tmpdir_needle: str = ""
    physical_needle: str = ""


def normalize_command_signature(value: str) -> str:
    return " ".join(value.replace("\r", " ").replace("\n", " ").split())


def bounded_command(value: str, *, limit: int = COMMAND_LOG_LIMIT) -> str:
    normalized = normalize_command_signature(value)
    if len(normalized) <= limit:
        return normalized
    return normalized[: max(0, limit - 1)] + "…"


def _parse_ps_identity(*, pid: int, pgid: int, stdout: str, expected_signature: str) -> RecordedProcessIdentity | None:
    for raw in stdout.splitlines():
        parts = raw.strip().split(maxsplit=PS_LSTART_FIELD_COUNT)
        if len(parts) < PS_LSTART_FIELD_COUNT:
            continue
        start_time = " ".join(parts[:PS_LSTART_FIELD_COUNT])
        command = parts[PS_LSTART_FIELD_COUNT] if len(parts) > PS_LSTART_FIELD_COUNT else ""
        return RecordedProcessIdentity(
            pid=pid,
            pgid=pgid,
            start_time=normalize_command_signature(start_time),
            command_signature=normalize_command_signature(command),
            expected_signature=normalize_command_signature(expected_signature),
        )
    return None


def read_process_identity(
    *,
    pid: int,
    runner: proc.Runner | None = None,
    expected_signature: str = "",
) -> RecordedProcessIdentity | None:
    if pid <= 0:
        return None
    pgid: int | None = None
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        pgid = os.getpgid(pid)
    if pgid is None:
        return None
    active_runner = runner or proc.ProcRunner()
    result = active_runner.run(["ps", "-p", str(pid), "-o", "lstart=", "-o", "command="])
    if result.returncode != 0:
        return None
    return _parse_ps_identity(pid=pid, pgid=pgid, stdout=result.stdout, expected_signature=expected_signature)


def _read_stable_process_identity(
    *,
    pid: int,
    runner: proc.Runner | None = None,
    expected_signature: str = "",
    require_pgid_match: bool = False,
) -> RecordedProcessIdentity | None:
    for attempt in range(PROCESS_IDENTITY_CAPTURE_ATTEMPTS):
        identity = read_process_identity(pid=pid, runner=runner, expected_signature=expected_signature)
        if identity is not None and (not require_pgid_match or identity.pgid == pid):
            return identity
        if attempt < PROCESS_IDENTITY_CAPTURE_ATTEMPTS - 1:
            time.sleep(PROCESS_IDENTITY_CAPTURE_SLEEP_S)
    return None


def validate_process_identity(
    *,
    recorded: RecordedProcessIdentity,
    runner: proc.Runner | None = None,
) -> ValidationResult:
    current = read_process_identity(pid=recorded.pid, runner=runner, expected_signature=recorded.expected_signature)
    if current is None:
        return ValidationResult(ok=False, reason="missing-pid")
    if current.pgid != recorded.pgid:
        return ValidationResult(ok=False, reason="pgid-mismatch", current=current)
    if normalize_command_signature(current.start_time) != normalize_command_signature(recorded.start_time):
        return ValidationResult(ok=False, reason="start-time-mismatch", current=current)
    recorded_command = normalize_command_signature(recorded.command_signature)
    current_command = normalize_command_signature(current.command_signature)
    if recorded_command and current_command != recorded_command:
        return ValidationResult(ok=False, reason="command-mismatch", current=current)
    expected = normalize_command_signature(recorded.expected_signature)
    if expected and expected not in current_command:
        return ValidationResult(ok=False, reason="expected-command-mismatch", current=current)
    return ValidationResult(ok=True, reason="ok", current=current)


def collect_descendants(*, pid: int, runner: proc.Runner | None = None) -> tuple[int, ...]:
    active_runner = runner or proc.ProcRunner()
    result = active_runner.run(["pgrep", "-P", str(pid)])
    if result.returncode != 0:
        return ()
    descendants: list[int] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if not raw.isdigit():
            continue
        child = int(raw)
        descendants.extend(collect_descendants(pid=child, runner=active_runner))
        descendants.append(child)
    return tuple(descendants)


def collect_process_group_members(*, pgid: int, runner: proc.Runner | None = None) -> tuple[int, ...]:
    active_runner = runner or proc.ProcRunner()
    result = active_runner.run(["pgrep", "-g", str(pgid)])
    if result.returncode != 0:
        return ()
    members: list[int] = []
    for line in result.stdout.splitlines():
        raw = line.strip()
        if raw.isdigit():
            members.append(int(raw))
    return tuple(dict.fromkeys(members))


def append_kill_log(*, path: Path | None, event: KillLogEvent) -> None:
    if path is None:
        return
    payload = asdict(event)
    for key, value in list(payload.items()):
        if isinstance(value, str):
            payload[key] = redact.redact_outbound(value)
    payload["command"] = bounded_command(str(payload.get("command", "")))
    payload["ts"] = time.time()
    with contextlib.suppress(OSError, TypeError):
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            _ = handle.write(json.dumps(payload, sort_keys=True) + "\n")


def _log_signal(
    *,
    log_path: Path | None,
    signal_name: str,
    snapshot: KillTargetSnapshot,
    caller: str,
    reason: str,
) -> None:
    append_kill_log(
        path=log_path,
        event=KillLogEvent(
            event="signal",
            signal=signal_name,
            pid=snapshot.pid,
            pgid=snapshot.pgid,
            command=snapshot.command,
            caller=caller,
            reason=reason,
            descendants=snapshot.descendants,
        ),
    )


def _validated_missing_leader_members(
    *,
    recorded: RecordedProcessIdentity,
    runner: proc.Runner,
) -> tuple[int, ...] | None:
    descendants = collect_process_group_members(pgid=recorded.pgid, runner=runner)
    if not descendants:
        return None
    validated_members: list[int] = []
    for child in descendants:
        child_identity = read_process_identity(
            pid=child,
            runner=runner,
            expected_signature=recorded.expected_signature,
        )
        if child_identity is None or child_identity.pgid != recorded.pgid:
            return None
        validated_members.append(child)
    return tuple(validated_members)


def terminate_validated_process_group(
    *,
    recorded: RecordedProcessIdentity,
    log_path: Path | None,
    caller: str,
    reason: str,
    runner: proc.Runner | None = None,
) -> ValidationResult:
    active_runner = runner or proc.ProcRunner()
    validation = validate_process_identity(recorded=recorded, runner=active_runner)
    if not validation.ok and validation.reason != "missing-pid":
        return validation
    current = validation.current or recorded
    if validation.ok:
        descendants = collect_descendants(pid=recorded.pid, runner=active_runner)
    else:
        descendants = _validated_missing_leader_members(recorded=recorded, runner=active_runner)
        if not descendants:
            return validation
    snapshot = KillTargetSnapshot(
        pid=recorded.pid,
        pgid=recorded.pgid,
        descendants=descendants,
        command=current.command_signature,
    )
    _log_signal(log_path=log_path, signal_name="SIGTERM", snapshot=snapshot, caller=caller, reason=reason)
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(recorded.pgid, signal.SIGTERM)
    for child in descendants:
        append_kill_log(
            path=log_path,
            event=KillLogEvent(
                event="signal",
                signal="SIGTERM",
                pid=child,
                pgid=recorded.pgid,
                command="",
                caller=caller,
                reason=reason,
                descendants=(),
            ),
        )
        with contextlib.suppress(OSError):
            os.kill(child, signal.SIGTERM)
    time.sleep(2)
    validation = validate_process_identity(recorded=recorded, runner=active_runner)
    if not validation.ok and validation.reason != "missing-pid":
        return validation
    kill_descendants = collect_descendants(pid=recorded.pid, runner=active_runner) if validation.ok else collect_process_group_members(
        pgid=recorded.pgid,
        runner=active_runner,
    )
    if not validation.ok and not kill_descendants:
        return ValidationResult(ok=True, reason="ok", current=current)
    snapshot = KillTargetSnapshot(
        pid=recorded.pid,
        pgid=recorded.pgid,
        descendants=kill_descendants,
        command=(validation.current or current).command_signature,
    )
    _log_signal(log_path=log_path, signal_name="SIGKILL", snapshot=snapshot, caller=caller, reason=reason)
    with contextlib.suppress(ProcessLookupError, PermissionError, OSError):
        os.killpg(recorded.pgid, signal.SIGKILL)
    for child in kill_descendants:
        append_kill_log(
            path=log_path,
            event=KillLogEvent(
                event="signal",
                signal="SIGKILL",
                pid=child,
                pgid=recorded.pgid,
                command="",
                caller=caller,
                reason=reason,
                descendants=(),
            ),
        )
        with contextlib.suppress(OSError):
            os.kill(child, signal.SIGKILL)
    if not validation.ok and validation.reason == "missing-pid":
        return ValidationResult(ok=True, reason="ok", current=current)
    return validation


def _identity_to_json(recorded: RecordedProcessIdentity, *, extra: dict[str, Any] | None = None) -> str:
    payload: dict[str, Any] = {
        "pid": recorded.pid,
        "pgid": recorded.pgid,
        "start_time": recorded.start_time,
        "command_signature": recorded.command_signature,
        "expected_signature": recorded.expected_signature,
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def write_identity_record(*, path: Path, recorded: RecordedProcessIdentity, extra: dict[str, Any] | None = None) -> None:
    larch_io.atomic_write(
        path=path,
        text=_identity_to_json(recorded, extra=extra),
        temp_name=f"{path.name}.tmp.{os.getpid()}",
        nofollow=True,
    )


def read_identity_record(*, path: Path) -> RecordedProcessIdentity | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    try:
        return RecordedProcessIdentity(
            pid=int(payload["pid"]),
            pgid=int(payload["pgid"]),
            start_time=str(payload["start_time"]),
            command_signature=str(payload["command_signature"]),
            expected_signature=str(payload.get("expected_signature", "")),
        )
    except (KeyError, TypeError, ValueError):
        return None


def _validated_design_tmpdir(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        return None
    return path


def _result_env_has_step3_status(*, tmpdir: Path, since_mtime_ns: int = 0) -> bool:
    result_env = tmpdir / ".step3-review-result.env"
    if result_env.is_symlink() or not result_env.is_file():
        return False
    try:
        if since_mtime_ns > 0 and result_env.stat().st_mtime_ns < since_mtime_ns:
            return False
        for line in result_env.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("STEP3_REVIEW_LOOP_STATUS=") and line.partition("=")[2]:
                return True
            if line.startswith("LOOP_STATUS=zero-findings-degraded-panel"):
                return True
    except OSError:
        return False
    return False


def write_loop_identity_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review write-loop-identity")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    _ = parser.add_argument("--expected-signature", default="plan-review run")
    args = parser.parse_args(argv)
    tmpdir = _validated_design_tmpdir(args.design_tmpdir)
    if tmpdir is None or not str(args.pid).isdigit():
        return 0
    identity = _read_stable_process_identity(
        pid=int(args.pid),
        expected_signature=args.expected_signature,
        require_pgid_match=True,
    )
    if identity is None:
        return 0
    write_identity_record(path=tmpdir / config.DESIGN_STEP3_LOOP_IDENTITY_FILE, recorded=identity)
    return 0


def _await_loop_poll(
    *,
    recorded: RecordedProcessIdentity,
    tmpdir: Path,
    identity_mtime_ns: int,
    timeout_s: float,
) -> int:
    missing_pid_since: float | None = None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        validation = validate_process_identity(recorded=recorded)
        if validation.ok:
            missing_pid_since = None
            time.sleep(0.2)
            continue
        if validation.reason == "missing-pid":
            if _result_env_has_step3_status(tmpdir=tmpdir, since_mtime_ns=identity_mtime_ns):
                return 0
            if missing_pid_since is None:
                missing_pid_since = time.monotonic()
            elif time.monotonic() - missing_pid_since >= DESIGN_STEP3_MISSING_PID_GRACE_S:
                return 1
            time.sleep(0.2)
            continue
        break
    return 1


def await_loop_identity_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review await-loop-identity")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    _ = parser.add_argument("--timeout-s", default="21600")
    args = parser.parse_args(argv)
    tmpdir = _validated_design_tmpdir(args.design_tmpdir)
    try:
        timeout_s = float(args.timeout_s)
    except (TypeError, ValueError):
        timeout_s = 0.0
    if tmpdir is None or not str(args.pid).isdigit() or timeout_s <= 0:
        return 1
    sidecar = tmpdir / config.DESIGN_STEP3_LOOP_IDENTITY_FILE
    recorded = read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 1
    detached_marker = tmpdir / config.DESIGN_STEP3_WRAPPER_DETACHED_FILE
    if not detached_marker.is_file() or detached_marker.is_symlink():
        return 1
    identity_mtime_ns = 0
    try:
        identity_mtime_ns = sidecar.stat().st_mtime_ns
    except OSError:
        identity_mtime_ns = 0
    if identity_mtime_ns <= 0:
        return 1
    return _await_loop_poll(
        recorded=recorded,
        tmpdir=tmpdir,
        identity_mtime_ns=identity_mtime_ns,
        timeout_s=timeout_s,
    )


def teardown_loop_identity_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review teardown-loop-identity")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    args = parser.parse_args(argv)
    tmpdir = _validated_design_tmpdir(args.design_tmpdir)
    if tmpdir is None or not str(args.pid).isdigit():
        return 0
    sidecar = tmpdir / config.DESIGN_STEP3_LOOP_IDENTITY_FILE
    recorded = read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 0
    validation = terminate_validated_process_group(
        recorded=recorded,
        log_path=tmpdir / config.DESIGN_STEP3_KILL_LOG_FILE,
        caller="design-step3-review",
        reason="step3-trap-cleanup",
    )
    if validation.ok:
        with contextlib.suppress(OSError):
            sidecar.unlink(missing_ok=True)
    return 0
