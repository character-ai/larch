"""Frozen pre-#8792 review-loop identity command facade.

The shared Python process-identity primitives remain temporarily available to
other migration leaves. This fixture preserves only the three retired Step 5
entrypoints so their observable command contract can be compared with Rust.
"""

from __future__ import annotations

import argparse
import contextlib
import sys
from pathlib import Path

from larch.core import process_identity

IMPLEMENT_STEP5_LOOP_IDENTITY_FILE = ".step5-loop-identity.json"
IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE = ".step5-wrapper-detached"
IMPLEMENT_STEP5_KILL_LOG_FILE = "implement-step5-kill.log.jsonl"


def _validated_implement_tmpdir(raw: str) -> Path | None:
    if not raw:
        return None
    path = Path(raw)
    if not path.is_absolute() or path.is_symlink() or not path.is_dir():
        return None
    return path


def write_loop_identity(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix write-loop-identity")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    _ = parser.add_argument("--expected-signature", default="review-and-fix step5")
    args = parser.parse_args(argv)
    tmpdir = _validated_implement_tmpdir(args.implement_tmpdir)
    if tmpdir is None or not str(args.pid).isdigit():
        return 0
    identity = process_identity._read_stable_process_identity(
        pid=int(args.pid),
        expected_signature=args.expected_signature,
        require_pgid_match=True,
    )
    if identity is None:
        return 0
    process_identity.write_identity_record(
        path=tmpdir / IMPLEMENT_STEP5_LOOP_IDENTITY_FILE,
        recorded=identity,
    )
    return 0


def await_loop_identity(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix await-loop-identity")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    _ = parser.add_argument("--timeout-s", default="21600")
    _ = parser.add_argument("--reattach", action="store_true")
    args = parser.parse_args(argv)
    tmpdir = _validated_implement_tmpdir(args.implement_tmpdir)
    try:
        timeout_s = float(args.timeout_s)
    except (TypeError, ValueError):
        timeout_s = 0.0
    if tmpdir is None or not str(args.pid).isdigit() or timeout_s <= 0:
        return 1
    sidecar = tmpdir / IMPLEMENT_STEP5_LOOP_IDENTITY_FILE
    recorded = process_identity.read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 1
    detached = tmpdir / IMPLEMENT_STEP5_WRAPPER_DETACHED_FILE
    if not args.reattach and not process_identity._regular_nonsymlink(detached):
        return 1
    try:
        identity_mtime_ns = sidecar.stat().st_mtime_ns
    except OSError:
        identity_mtime_ns = 0
    if identity_mtime_ns <= 0:
        return 1
    return process_identity._await_loop_poll(
        recorded=recorded,
        tmpdir=tmpdir,
        identity_mtime_ns=identity_mtime_ns,
        timeout_s=timeout_s,
        require_step3_result_env=False,
    )


def teardown_loop_identity(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="cli.py review-and-fix teardown-loop-identity")
    _ = parser.add_argument("--implement-tmpdir", required=True)
    _ = parser.add_argument("--pid", required=True)
    args = parser.parse_args(argv)
    tmpdir = _validated_implement_tmpdir(args.implement_tmpdir)
    if tmpdir is None or not str(args.pid).isdigit():
        return 0
    sidecar = tmpdir / IMPLEMENT_STEP5_LOOP_IDENTITY_FILE
    recorded = process_identity.read_identity_record(path=sidecar)
    if recorded is None or recorded.pid != int(args.pid):
        return 0
    validation = process_identity.terminate_validated_process_group(
        recorded=recorded,
        log_path=tmpdir / IMPLEMENT_STEP5_KILL_LOG_FILE,
        caller="implement-step5-review",
        reason="step5-trap-cleanup",
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
