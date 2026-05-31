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
    try:
        completed = subprocess.run(
            argv_tuple,
            capture_output=True,
            text=True,
            timeout=timeout,
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
    except subprocess.TimeoutExpired as exc:
        duration = time.monotonic() - start
        result = CommandResult(
            argv=argv_tuple,
            returncode=config.PROC_TIMEOUT_EXIT_CODE,
            stdout=(exc.stdout or "") if isinstance(exc.stdout, str) else "",
            stderr=(exc.stderr or "") if isinstance(exc.stderr, str) else "",
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
