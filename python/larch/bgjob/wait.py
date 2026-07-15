"""Chunked foreground waiting for bgjob result envs."""

from __future__ import annotations

import contextlib
import signal
import time
from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.bgjob import model, registry
from larch.core import config, redact


class BgjobWaitTimeout(RuntimeError):
    """Raised when the hard SIGALRM deadline fires."""


@dataclass(frozen=True)
class WaitContext:
    tmpdir: Path
    step: str
    deadline: float
    max_wait_s: int
    poll_interval_s: float


def _alarm_handler(signum: int, frame: object) -> None:  # noqa: ARG001 - signal API
    raise BgjobWaitTimeout("bgjob wait hard deadline exceeded")


def _print_rows(rows: list[tuple[str, str]]) -> None:
    print(larch_io.format_kvs(rows), end="")


def _read_result(path: Path) -> dict[str, str] | None:
    if path.is_symlink() or not path.is_file():
        return None
    return larch_io.read_kvs(path, reject_symlink=True, on_error_default=True, reject_cr=True)


def _startup_in_progress(*, tmpdir: Path, step: str) -> bool:
    path = model.startup_env_path(tmpdir=tmpdir, step=step)
    if path.is_symlink() or not path.is_file():
        return False
    rows = larch_io.read_kvs(path, reject_symlink=True, on_error_default=True, reject_cr=True)
    try:
        age_s = time.time() - int(rows["START_EPOCH"])
    except (KeyError, ValueError):
        return False
    return rows.get("STEP") == step and 0 <= age_s <= config.BGJOB_STARTUP_GRACE_S


def _wait_for_startup(ctx: WaitContext) -> bool:
    while _startup_in_progress(tmpdir=ctx.tmpdir, step=ctx.step):
        if time.monotonic() >= ctx.deadline:
            _print_rows([(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_WAIT), ("ELAPSED_S", str(ctx.max_wait_s))])
            return True
        time.sleep(max(0.05, min(ctx.poll_interval_s, ctx.deadline - time.monotonic())))
    return False


def _report_missing_registry(*, result_path: Path, reg_path: Path, ctx: WaitContext) -> int:
    # The daemon writes the result env before unlinking its registry row. When
    # the registry vanishes between the wait's result read and its registry
    # read, the result is already on disk; emit DONE instead of a spurious DEAD.
    rows = _read_result(result_path)
    if rows is not None:
        _print_rows([(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DONE), *rows.items()])
        return 0
    if _wait_for_startup(ctx):
        return 0
    _print_rows(
        [
            (config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DEAD),
            ("BGJOB_DIAG", "missing-registry"),
            ("REGISTRY", str(reg_path)),
        ]
    )
    return 0


def _log_tail(path: Path) -> str:
    if path.is_symlink() or not path.is_file():
        return ""
    with contextlib.suppress(OSError):
        text = path.read_text(encoding="utf-8", errors="replace")
        return redact.redact_outbound(text[-config.BGJOB_LOG_TAIL_BYTES :]).replace("\n", "\\n")
    return ""


def wait_once(*, tmpdir: Path, step: str, max_wait_s: int, run_id: str | None = None, poll_interval_s: float = 1.0) -> int:
    if max_wait_s > config.BGJOB_WAIT_MAX_CHUNK_S:
        print(f"BGJOB_ERROR=max-wait-too-large MAX={config.BGJOB_WAIT_MAX_CHUNK_S}")
        return 2
    result_path = model.result_env_path(tmpdir=tmpdir, step=step)
    deadline = time.monotonic() + max(0, max_wait_s)
    ctx = WaitContext(
        tmpdir=tmpdir,
        step=step,
        deadline=deadline,
        max_wait_s=max_wait_s,
        poll_interval_s=poll_interval_s,
    )
    old_handler = signal.signal(signal.SIGALRM, _alarm_handler)
    _ = signal.alarm(max_wait_s + config.BGJOB_WAIT_HARD_DEADLINE_GRACE_S)
    try:
        while True:
            rows = _read_result(result_path)
            if rows is not None:
                out_rows = [(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DONE), *rows.items()]
                _print_rows(out_rows)
                return 0
            reg_path, entry = registry.read_for(tmpdir=tmpdir, step=step, run_id=run_id)
            if entry is None:
                return _report_missing_registry(
                    result_path=result_path,
                    reg_path=reg_path,
                    ctx=ctx,
                )
            daemon_live = registry.daemon_liveness(entry)
            if not daemon_live.live:
                # Re-check: daemon may have written result just before exiting.
                rows = _read_result(result_path)
                if rows is not None:
                    _print_rows([(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DONE), *rows.items()])
                else:
                    tail = _log_tail(entry.stderr_log)
                    _print_rows(
                        [
                            (config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_DEAD),
                            ("BGJOB_DIAG", daemon_live.reason),
                            ("STDERR_TAIL", tail),
                        ]
                    )
                return 0
            if time.monotonic() >= deadline:
                _print_rows([(config.BGJOB_STATUS_KEY, config.BGJOB_STATUS_WAIT), ("ELAPSED_S", str(max_wait_s))])
                return 0
            child_live = registry.child_liveness(entry)
            if not child_live.live:
                time.sleep(max(0.05, min(poll_interval_s, deadline - time.monotonic())))
                continue
            time.sleep(max(0.05, min(poll_interval_s, deadline - time.monotonic())))
    except BgjobWaitTimeout:
        print("BGJOB_ERROR=hard-deadline")
        return 2
    finally:
        _ = signal.alarm(0)
        _ = signal.signal(signal.SIGALRM, old_handler)
