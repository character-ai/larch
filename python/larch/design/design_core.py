"""Core utilities and low-level helpers for /design lifecycle phases."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedFunction=false, reportUnusedCallResult=false
from __future__ import annotations

import contextlib
import fcntl
import io
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path
from collections.abc import Callable, Iterable, Mapping

from larch import io as larch_io
from larch.core import logging_util
from larch.core import redact
from larch.implement.bg_wait import _read_keepalive_clone_path
from larch.state.session_env import validate_design_tmpdir

_SUBPROCESS_RUN = subprocess.run

class _CoreUsageError(Exception):
    """User-facing argument or validation error for ported design helpers."""


def _validate_design_tmpdir_arg(candidate: str) -> Path:
    ok, message = validate_design_tmpdir(candidate)
    if not ok:
        raise _CoreUsageError(message)
    path = Path(candidate).resolve()
    if not path.is_dir():
        raise _CoreUsageError("design-tmpdir: path must name a directory")
    return path


def _capture_contract_stream_to_paths(
    callable_obj: Callable[..., int | tuple[int, list[str]]],
    stdout_path: str | Path,
    stderr_path: str | Path,
    *args: object,
    **kwargs: object,
) -> int:
    """Run ``callable_obj`` while capturing fd 1, fd 2, and fd 3 contracts.

    ``quiet_init`` routes machine stdout through fd 3. In-process callers use
    this helper so a core function can emit through ``logging_util.emit_kv``
    without inheriting the caller's stdout/stderr routing after return.
    """
    out_path = Path(stdout_path)
    err_path = Path(stderr_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    err_path.parent.mkdir(parents=True, exist_ok=True)
    sys.stdout.flush()
    sys.stderr.flush()
    os.write(1, b"")
    os.write(2, b"")
    had_contract_fd = False
    try:
        saved_contract = fcntl.fcntl(3, fcntl.F_DUPFD, 10)
        had_contract_fd = True
    except OSError:
        saved_contract = None
    had_quiet_fd = False
    try:
        saved_quiet = fcntl.fcntl(4, fcntl.F_DUPFD, 10)
        had_quiet_fd = True
    except OSError:
        saved_quiet = None
    saved_stdout = fcntl.fcntl(1, fcntl.F_DUPFD, 10)
    saved_stderr = fcntl.fcntl(2, fcntl.F_DUPFD, 10)
    out_fd = os.open(out_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    err_fd = os.open(err_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        os.dup2(out_fd, 1)
        os.dup2(err_fd, 2)
        os.dup2(out_fd, 3)
        try:
            with out_path.open("a", encoding="utf-8") as py_out, err_path.open("a", encoding="utf-8") as py_err, contextlib.redirect_stdout(py_out), contextlib.redirect_stderr(py_err):
                try:
                    rc = callable_obj(*args, **kwargs)
                except SystemExit as exc:
                    return int(exc.code) if isinstance(exc.code, int) else 1
                except BaseException:
                    traceback.print_exc()
                    return 1
            if isinstance(rc, tuple):
                rc = rc[0]
            return int(rc)
        finally:
            sys.stdout.flush()
            sys.stderr.flush()
            os.dup2(saved_stdout, 1)
            os.dup2(saved_stderr, 2)
            if had_contract_fd and saved_contract is not None:
                os.dup2(saved_contract, 3)
            else:
                with contextlib.suppress(OSError):
                    os.close(3)
            if had_quiet_fd and saved_quiet is not None:
                os.dup2(saved_quiet, 4)
            os.write(1, b"")
            os.write(2, b"")
    finally:
        with contextlib.suppress(OSError):
            os.close(out_fd)
        with contextlib.suppress(OSError):
            os.close(err_fd)
        with contextlib.suppress(OSError):
            os.close(saved_stdout)
        with contextlib.suppress(OSError):
            os.close(saved_stderr)
        if saved_contract is not None:
            with contextlib.suppress(OSError):
                os.close(saved_contract)
        if saved_quiet is not None:
            with contextlib.suppress(OSError):
                os.close(saved_quiet)


capture_contract_stream_to_paths = _capture_contract_stream_to_paths


def _append_execution_issue(*, design_tmpdir: Path, message: str) -> None:
    path = design_tmpdir / "execution-issues.md"
    with path.open("a", encoding="utf-8") as handle:
        handle.write(message if message.endswith("\n") else message + "\n")


_PROBE_CLAMP_COUNTER_BY_STEP = {
    "design-step3-review": "step-3-terminal",
    "design-step4-tail": "step-4",
    "design-step5c": "step-5c-terminal",
    "design-step-final-summary": "step-final-summary",
}


_TERMINAL_SENTINEL_BY_STEP = {
    "design-step3-review": "step-3-terminal",
    "design-step4-tail": "step-4",
    "design-step5c": "step-5c-terminal",
    "design-step-final-summary": "step-final-summary",
}


def _clear_probe_clamp_counter(*, design_tmpdir: Path, step: str) -> None:
    sentinel = _PROBE_CLAMP_COUNTER_BY_STEP.get(step)
    if sentinel:
        with contextlib.suppress(OSError):
            (design_tmpdir / f"bg-poll-guard-probe-denials.{sentinel}.count").unlink(missing_ok=True)
    with contextlib.suppress(OSError):
        for counter in design_tmpdir.glob("bg-poll-guard-task-output-read.*.count"):
            counter.unlink(missing_ok=True)


def _clear_no_progress_sidecars(*, design_tmpdir: Path) -> None:
    for name in (
        "no-progress-turns.count",
        "no-progress-circuit-breaker-armed",
        "no-progress-stop-block-emitted",
    ):
        with contextlib.suppress(OSError):
            (design_tmpdir / name).unlink(missing_ok=True)


def _clear_terminal_sentinel(*, design_tmpdir: Path, step: str) -> None:
    sentinel = _TERMINAL_SENTINEL_BY_STEP.get(step)
    if sentinel:
        with contextlib.suppress(OSError):
            (design_tmpdir / ".completed" / sentinel).unlink(missing_ok=True)


@contextlib.contextmanager
def _bg_wait_marker_context(*, design_tmpdir: str | Path, step: str, claude_pid: str = ""):
    tmpdir = Path(design_tmpdir)
    marker = tmpdir / ".bg-wait-active"
    tmp = tmpdir / f".bg-wait-active.tmp.{os.getpid()}"
    active = False
    _clear_terminal_sentinel(design_tmpdir=tmpdir, step=step)
    _clear_probe_clamp_counter(design_tmpdir=tmpdir, step=step)
    _clear_no_progress_sidecars(design_tmpdir=tmpdir)
    try:
        text = "\n".join(
            [
                f"PID={os.getpid()}",
                f"CLAUDE_PID={claude_pid or os.environ.get('CLAUDE_PID', '')}",
                f"START_EPOCH={int(time.time())}",
                f"STEP={step}",
                "TIMEOUT_S=21600",
                f"CLONE_PATH={_read_keepalive_clone_path(tmpdir)}",
                "",
            ]
        )
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(marker)
        active = True
    except OSError as exc:
        with contextlib.suppress(OSError):
            tmp.unlink()
        _append_execution_issue(design_tmpdir=tmpdir, message=f"Warning: bg-wait marker setup failed for {step}: {exc}")
    try:
        yield
    finally:
        if active:
            with contextlib.suppress(OSError, FileNotFoundError):
                marker.unlink()
        with contextlib.suppress(OSError, FileNotFoundError):
            tmp.unlink()


def _emit_core_kvs(rows: Iterable[tuple[str, str]]) -> None:
    for key, value in rows:
        logging_util.emit_kv(key=key, value=value)


def _core_quiet_mirrors_to_fd4() -> bool:
    pid = os.environ.get("LARCH_QUIET_PID", "")
    active = os.environ.get("LARCH_QUIET_ACTIVE", "").lower() in {"1", "true", "yes", "on"}
    return active and pid == str(os.getpid())


def _core_diagnostic(message: str) -> None:
    """Mirror bash larch_err for post-quiet_init *_core validation errors."""
    line = redact.redact_outbound(logging_util.sanitize_diagnostic_line(message)).rstrip("\n") + "\n"
    _ = sys.stderr.write(line)
    _ = sys.stderr.flush()
    if _core_quiet_mirrors_to_fd4():
        with contextlib.suppress(OSError):
            _ = os.write(4, line.encode("utf-8"))


def _core_print_exc() -> None:
    buf = io.StringIO()
    traceback.print_exc(file=buf)
    for line in buf.getvalue().splitlines():
        _core_diagnostic(line)


def _read_env_value(*, path: Path, key: str, default: str = "") -> str:
    return larch_io.read_kv(path=path, key=key, default=default, first_match=True, empty_value_means_default=True, reject_symlink=True, on_error_default=True, errors="replace")


def _read_env_value_last(*, path: Path, key: str, default: str = "") -> str:
    if path.is_symlink() or not path.is_file():
        return default
    prefix = f"{key}="
    value = default
    try:
        lines = larch_io.read_text(path, errors="replace").splitlines()
    except OSError:
        return default
    for raw in lines:
        if raw.startswith(prefix):
            candidate = raw[len(prefix) :]
            if candidate:
                value = candidate
    return value


def _read_env_values(*, path: Path, defaults: Mapping[str, str]) -> dict[str, str]:
    out = dict(defaults)
    if path.is_symlink() or not path.is_file():
        return out
    try:
        lines = larch_io.read_text(path, errors="replace").splitlines()
    except OSError:
        return out
    for line in lines:
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        if key in out and value:
            out[key] = value
    return out



def _cli_cmd(plugin_root: Path, *args: str) -> list[str]:
    return [sys.executable, str(plugin_root / "python" / "cli.py"), *args]


def _append_failure(*, plugin_root: Path, design_tmpdir: Path, site: str, tool: str, exit_code: int | str, category: str, output_file: Path) -> bool:
    result = subprocess.run(
        _cli_cmd(plugin_root, "run-log", "append-failure", "--log", str(design_tmpdir / "execution-issues.md"), "--site", site, "--tool", tool, "--exit-code", str(exit_code), "--category", category, "--output-file", str(output_file), "--redact"),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode == 0
