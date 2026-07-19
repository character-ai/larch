"""Typed consumers of commands owned by the installed Rust runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from larch.core.proc import Runner
from larch.core.repo_roots import larch_binary


@dataclass(frozen=True)
class PhantomProbeOutput:
    """Validated advisory output from the Rust phantom-probe owner."""

    lines: tuple[str, ...]


def phantom_probe(runner: Runner, *, step: str, cwd: str | None = None) -> PhantomProbeOutput:
    """Invoke the Rust owner and fail closed when its KV envelope is absent."""
    result = runner.run(
        [str(larch_binary(Path(__file__).resolve().parents[3])), "git", "phantom-probe", "--step", step],
        cwd=cwd,
    )
    lines = tuple(line for line in result.stdout.splitlines() if line)
    if result.returncode != 0 or not any(line.startswith("PHANTOM_STATUS=") for line in lines):
        return PhantomProbeOutput(
            lines=("PHANTOM_STATUS=unknown", "PHANTOM_REASON=phantom-probe-failed"),
        )
    return PhantomProbeOutput(lines=lines)
