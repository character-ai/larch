"""Core utilities and low-level helpers for /design lifecycle phases."""
# pyright: reportUnknownMemberType=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportPrivateUsage=false, reportUnusedFunction=false, reportUnusedCallResult=false
from __future__ import annotations

import contextlib
import fcntl
import io
import os
import subprocess
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable, Iterable, Mapping

from larch import io as larch_io
from larch.core import config, logging_util, proc
from larch.core import redact
from larch.state.session_env import validate_design_tmpdir

_SUBPROCESS_RUN = subprocess.run


DESIGN_BGJOB_STEP3_REVIEW = "design-step3-review"
DESIGN_BGJOB_STEP4_TAIL = "design-step4-tail"
DESIGN_BGJOB_STEP5C = "design-step5c"
DESIGN_BGJOB_STEP_FINAL_SUMMARY = "design-step-final-summary"


def design_bgjob_result_env_path(*, design_tmpdir: Path, step: str) -> Path:
    return design_tmpdir / config.BGJOB_TMP_SUBDIR / f"{step}{config.BGJOB_RESULT_ENV_SUFFIX}"


def design_recreate_merge_env(*, path: Path, design_tmpdir: Path) -> None:
    root = design_tmpdir.resolve()
    target = path.resolve(strict=False)
    try:
        _ = target.relative_to(root)
    except ValueError as exc:
        msg = f"merge env escapes DESIGN_TMPDIR: {path}"
        raise OSError(msg) from exc
    if path.is_symlink():
        msg = f"refusing to replace symlink merge env: {path}"
        raise OSError(msg)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        msg = f"merge env parent is not a regular directory: {path.parent}"
        raise OSError(msg)
    larch_io.atomic_write(path=path, text="", nofollow=True, mode=0o600)


def design_write_merge_env(*, path: Path, design_tmpdir: Path, rows: Iterable[tuple[str, object]]) -> None:
    root = design_tmpdir.resolve()
    target = path.resolve(strict=False)
    try:
        _ = target.relative_to(root)
    except ValueError as exc:
        msg = f"merge env escapes DESIGN_TMPDIR: {path}"
        raise OSError(msg) from exc
    safe_rows: list[tuple[str, str]] = []
    for key, value in rows:
        if not key or "\n" in key or "\r" in key:
            msg = f"invalid merge env key: {key!r}"
            raise ValueError(msg)
        text = str(value)
        if "\n" in text or "\r" in text:
            msg = f"merge env value contains newline: {key}"
            raise ValueError(msg)
        safe_rows.append((key, text))
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.parent.is_symlink() or not path.parent.is_dir():
        msg = f"merge env parent is not a regular directory: {path.parent}"
        raise OSError(msg)
    larch_io.atomic_write(path=path, text=larch_io.format_kvs(safe_rows), nofollow=True, mode=0o600)


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
    return larch_io.read_kv(
        path=path,
        key=key,
        default=default,
        duplicate_policy="last-non-empty",
        reject_symlink=True,
        on_error_default=True,
        errors="replace",
    )


def _read_env_values(*, path: Path, defaults: Mapping[str, str]) -> dict[str, str]:
    return larch_io.read_kvs(
        path,
        default=defaults,
        duplicate_policy="last-non-empty",
        allowed_keys=defaults,
        reject_symlink=True,
        on_error_default=True,
        errors="replace",
    )



def _cli_cmd(plugin_root: Path, *args: str) -> list[str]:
    return [sys.executable, str(plugin_root / "python" / "cli.py"), *args]


@dataclass(frozen=True)
class FailureLogRequest:
    """One structured request to record a design execution failure."""

    plugin_root: Path
    design_tmpdir: Path
    site: str
    tool: str
    exit_code: int | str
    category: str
    output_file: Path


def append_failure(
    *,
    request: FailureLogRequest,
    env: Mapping[str, str] | None = None,
    runner: Callable[..., proc.CommandResult] = proc.run,
) -> bool:
    """Append one failure record through the canonical run-log command."""
    result = runner(
        _cli_cmd(request.plugin_root, "run-log", "append-failure", "--log", str(request.design_tmpdir / "execution-issues.md"), "--site", request.site, "--tool", request.tool, "--exit-code", str(request.exit_code), "--category", request.category, "--output-file", str(request.output_file), "--redact"),
        env={**os.environ, **env} if env is not None else None,
    )
    return result.returncode == 0


def _append_failure(*, plugin_root: Path, design_tmpdir: Path, site: str, tool: str, exit_code: int | str, category: str, output_file: Path) -> bool:
    """Compatibility wrapper for established design failure-log call sites."""
    return append_failure(
        request=FailureLogRequest(
            plugin_root=plugin_root,
            design_tmpdir=design_tmpdir,
            site=site,
            tool=tool,
            exit_code=exit_code,
            category=category,
            output_file=output_file,
        )
    )
