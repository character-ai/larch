"""Shared bg-wait marker helpers for /implement."""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path


def _clear_no_progress_sidecars(tmpdir: Path) -> None:
    for name in (
        "no-progress-turns.count",
        "no-progress-circuit-breaker-armed",
        "no-progress-stop-block-emitted",
        "no-progress-task-output-clamped",
    ):
        with contextlib.suppress(OSError):
            (tmpdir / name).unlink()
    with contextlib.suppress(OSError):
        for counter in tmpdir.glob("bg-poll-guard-task-output-read.*.count"):
            counter.unlink(missing_ok=True)


def _read_keepalive_clone_path(tmpdir: Path) -> str:
    keepalive = tmpdir / ".larch-keepalive"
    if not keepalive.is_file() or keepalive.is_symlink():
        return ""
    with contextlib.suppress(OSError):
        for line in keepalive.read_text(encoding="utf-8", errors="replace").splitlines():
            key, sep, value = line.partition("=")
            if sep and key == "CLONE_PATH":
                return value.strip()
    return ""


def _write_bg_wait_marker(*, tmpdir: Path, step: str, timeout_s: int) -> None:
    _clear_no_progress_sidecars(tmpdir)
    start = int(time.time())
    claude_pid = os.environ.get("LARCH_BG_POLL_GUARD_SESSION_PID", "") or str(os.getppid())
    text = (
        f"PID={os.getpid()}\n"
        f"CLAUDE_PID={claude_pid}\n"
        f"START_EPOCH={start}\n"
        f"STEP={step}\n"
        f"TIMEOUT_S={timeout_s}\n"
        f"CLONE_PATH={_read_keepalive_clone_path(tmpdir)}\n"
    )
    with contextlib.suppress(OSError):
        (tmpdir / ".bg-wait-active").write_text(text, encoding="utf-8")
# pyright: reportUnusedFunction=false, reportUnusedCallResult=false
