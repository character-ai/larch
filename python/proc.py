"""Injectable subprocess seam for ship-pr Python."""

from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from typing import Protocol
from collections.abc import Mapping, Sequence

import config


@dataclass(frozen=True)
class CommandResult:
    argv: tuple[str, ...]
    returncode: int
    stdout: str
    stderr: str
    duration: float


class Runner(Protocol):
    def run(
        self,
        argv: Sequence[str],
        *,
        timeout: float | None = None,
        cwd: str | None = None,
        env: Mapping[str, str] | None = None,
        check: bool = False,
        stdout: int | None = None,
        stderr: int | None = None,
    ) -> CommandResult:
        ...


def _decode_output(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def run(
    argv: Sequence[str],
    *,
    timeout: float | None = None,
    cwd: str | None = None,
    env: Mapping[str, str] | None = None,
    check: bool = False,
    stdout: int | None = None,
    stderr: int | None = None,
) -> CommandResult:
    """Run a subprocess with timeout and captured stdout/stderr."""
    argv_tuple = tuple(argv)
    start = time.monotonic()
    stream_stdout = stdout if stdout is not None else subprocess.PIPE
    stream_stderr = stderr if stderr is not None else subprocess.PIPE
    popen_text = stream_stdout is subprocess.PIPE and stream_stderr is subprocess.PIPE
    if timeout is not None:
        with subprocess.Popen(
            argv_tuple,
            stdout=stream_stdout,
            stderr=stream_stderr,
            text=popen_text,
            errors="replace",
            cwd=cwd,
            env=None if env is None else dict(env),
        ) as proc:
            try:
                out_data, err_data = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired as exc:
                proc.kill()
                rest_out, rest_err = proc.communicate()
                duration = time.monotonic() - start
                result = CommandResult(
                    argv=argv_tuple,
                    returncode=config.PROC_TIMEOUT_EXIT_CODE,
                    stdout=_decode_output(exc.stdout) + _decode_output(rest_out),
                    stderr=_decode_output(exc.stderr) + _decode_output(rest_err),
                    duration=duration,
                )
            else:
                duration = time.monotonic() - start
                result = CommandResult(
                    argv=argv_tuple,
                    returncode=proc.returncode,
                    stdout=_decode_output(out_data),
                    stderr=_decode_output(err_data),
                    duration=duration,
                )
    else:
        if stream_stdout is subprocess.PIPE and stream_stderr is subprocess.PIPE:
            completed = subprocess.run(
                argv_tuple,
                capture_output=True,
                text=True,
                errors="replace",
                cwd=cwd,
                env=None if env is None else dict(env),
                check=False,
            )
        else:
            completed = subprocess.run(
                argv_tuple,
                stdout=stream_stdout,
                stderr=stream_stderr,
                text=popen_text,
                errors="replace",
                cwd=cwd,
                env=None if env is None else dict(env),
                check=False,
            )
        duration = time.monotonic() - start
        result = CommandResult(
            argv=argv_tuple,
            returncode=completed.returncode,
            stdout=_decode_output(completed.stdout),
            stderr=_decode_output(completed.stderr),
            duration=duration,
        )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(
            result.returncode,
            list(argv_tuple),
            output=result.stdout,
            stderr=result.stderr,
        )
    return result
