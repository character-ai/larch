# pyright: reportUnusedFunction=false, reportUnusedCallResult=false, reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false, reportPrivateUsage=false
"""Subprocess leg execution and process-group management."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from larch.core import proc
from larch.implement.dispatch_helpers import _current_cli_path

# Deadline constants used by commit-route composites (defined here as they
# drive leg-timeout sizing and the public outer-timeout constants).
_ACTIVE_LEG_PGID_FILE = ".active-leg-pgid"
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


def _descendants(pid: int) -> list[int]:
    result = proc.run(["pgrep", "-P", str(pid)])
    children: list[int] = []
    if result.returncode != 0:
        return children
    for line in result.stdout.splitlines():
        if line.strip().isdigit():
            child = int(line.strip())
            children.extend(_descendants(child))
            children.append(child)
    return children


def _active_leg_pgid_path() -> Path | None:
    tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not tmpdir:
        return None
    return Path(tmpdir) / _ACTIVE_LEG_PGID_FILE


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


def _kill_leg_process_group_targets(
    *,
    pgid: int,
    pid: int,
    process: subprocess.Popen[str] | None = None,
) -> None:
    descendant_pids = _descendants(pid)
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
    _kill_leg_process_group_targets(pgid=pgid, pid=process.pid, process=process)


def kill_active_leg_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cli.py implement kill-active-leg")
    parser.add_argument("--implement-tmpdir", required=True)
    args = parser.parse_args(argv)
    path = Path(args.implement_tmpdir) / _ACTIVE_LEG_PGID_FILE
    if not path.is_file():
        return 0
    raw = path.read_text(encoding="ascii").strip()
    with contextlib.suppress(OSError):
        path.unlink(missing_ok=True)
    if not raw.isdigit():
        return 0
    pgid = int(raw)
    # Leg subprocesses use start_new_session=True, so the published pgid is the session-leader pid.
    _kill_leg_process_group_targets(pgid=pgid, pid=pgid)
    return 0


def _kill_active_leg() -> None:
    if _LEG_STATE.active is None:
        return
    _kill_leg_process_group(_LEG_STATE.active)
    _LEG_STATE.active = None


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
    _publish_active_leg_pgid(process.pid)
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
        _finalize_leg_process(process)
        _clear_active_leg_pgid()


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
