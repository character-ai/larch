"""Frozen pre-#8835 plan-review loop-identity command facade.

The shared Python process-identity primitives remain temporarily available to
other migration leaves. This fixture preserves only the three retired design
Step 3 entrypoints so their observable command contract can be compared with
Rust.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
import time
from pathlib import Path

from larch.core import process_identity

DESIGN_STEP3_MISSING_PID_GRACE_S = 5.0
DESIGN_STEP3_LOOP_IDENTITY_FILE = ".step3-loop-identity.json"
DESIGN_STEP3_WRAPPER_DETACHED_FILE = ".step3-wrapper-detached"
DESIGN_STEP3_KILL_LOG_FILE = "design-step3-kill.log.jsonl"
PROCESS_IDENTITY_CAPTURE_ATTEMPTS = 10
PROCESS_IDENTITY_CAPTURE_SLEEP_S = 0.05


def _validated_design_tmpdir(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        return None
    return path


def _regular_nonsymlink(path: Path) -> bool:
    return path.is_file() and not path.is_symlink()


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


def _read_stable_process_identity(
    *,
    pid: int,
    expected_signature: str,
    require_pgid_match: bool,
) -> process_identity.RecordedProcessIdentity | None:
    for attempt in range(PROCESS_IDENTITY_CAPTURE_ATTEMPTS):
        identity = process_identity.read_process_identity(
            pid=pid,
            expected_signature=expected_signature,
        )
        if identity is not None and (not require_pgid_match or identity.pgid == pid):
            return identity
        if attempt < PROCESS_IDENTITY_CAPTURE_ATTEMPTS - 1:
            time.sleep(PROCESS_IDENTITY_CAPTURE_SLEEP_S)
    return None


def write_loop_identity(argv: list[str]) -> int:
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
    process_identity.write_identity_record(
        path=tmpdir / DESIGN_STEP3_LOOP_IDENTITY_FILE,
        recorded=identity,
    )
    return 0


def _await_loop_poll(
    *,
    recorded: process_identity.RecordedProcessIdentity,
    tmpdir: Path,
    identity_mtime_ns: int,
    timeout_s: float,
) -> int:
    missing_pid_since: float | None = None
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        validation = process_identity.validate_process_identity(recorded=recorded)
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


def await_loop_identity(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review await-loop-identity")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    _ = parser.add_argument("--timeout-s", default="21600")
    _ = parser.add_argument("--reattach", action="store_true")
    args = parser.parse_args(argv)
    tmpdir = _validated_design_tmpdir(args.design_tmpdir)
    try:
        timeout_s = float(args.timeout_s)
    except (TypeError, ValueError):
        timeout_s = 0.0
    if tmpdir is None or not str(args.pid).isdigit() or timeout_s <= 0:
        return 1
    sidecar = tmpdir / DESIGN_STEP3_LOOP_IDENTITY_FILE
    recorded = process_identity.read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 1
    detached_marker = tmpdir / DESIGN_STEP3_WRAPPER_DETACHED_FILE
    if not args.reattach and not _regular_nonsymlink(detached_marker):
        return 1
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


def teardown_loop_identity(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py plan-review teardown-loop-identity")
    _ = parser.add_argument("--design-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    args = parser.parse_args(argv)
    tmpdir = _validated_design_tmpdir(args.design_tmpdir)
    if tmpdir is None or not str(args.pid).isdigit():
        return 0
    sidecar = tmpdir / DESIGN_STEP3_LOOP_IDENTITY_FILE
    recorded = process_identity.read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 0
    validation = process_identity.terminate_validated_process_group(
        recorded=recorded,
        log_path=tmpdir / DESIGN_STEP3_KILL_LOG_FILE,
        caller="design-step3-review",
        reason="step3-trap-cleanup",
    )
    if validation.ok:
        with contextlib.suppress(OSError):
            sidecar.unlink(missing_ok=True)
    return 0


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        return 2
    verb, rest = arguments[0], arguments[1:]
    if verb == "write-loop-identity":
        return write_loop_identity(rest)
    if verb == "await-loop-identity":
        return await_loop_identity(rest)
    if verb == "teardown-loop-identity":
        return teardown_loop_identity(rest)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
