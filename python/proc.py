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
) -> CommandResult:
    """Run a subprocess with timeout and captured stdout/stderr."""
    argv_tuple = tuple(argv)
    start = time.monotonic()
    if timeout is not None:
        proc = subprocess.Popen(
            argv_tuple,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            errors="replace",
            cwd=cwd,
            env=None if env is None else dict(env),
        )
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
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
                stdout=stdout,
                stderr=stderr,
                duration=duration,
            )
    else:
        completed = subprocess.run(
            argv_tuple,
            capture_output=True,
            text=True,
            errors="replace",
            cwd=cwd,
            env=None if env is None else dict(env),
            check=False,
        )
        duration = time.monotonic() - start
        result = CommandResult(
            argv=argv_tuple,
            returncode=completed.returncode,
            stdout=completed.stdout,
            stderr=completed.stderr,
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
