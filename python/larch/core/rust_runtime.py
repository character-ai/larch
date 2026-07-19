"""Typed consumers of commands owned by the installed Rust runtime."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from larch import io as larch_io
from larch.core.proc import Runner
from larch.core.repo_roots import larch_entrypoint


@dataclass(frozen=True)
class PhantomProbeOutput:
    """Validated advisory output from the Rust phantom-probe owner."""

    lines: tuple[str, ...]


@dataclass(frozen=True)
class PushOutput:
    """Validated result from the Rust-owned branch push command."""

    status: str
    branch: str = ""


def phantom_probe(runner: Runner, *, step: str, cwd: str | None = None) -> PhantomProbeOutput:
    """Invoke the Rust owner and fail closed when its KV envelope is absent."""
    result = runner.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "git", "phantom-probe", "--step", step],
        cwd=cwd,
    )
    lines = tuple(line for line in result.stdout.splitlines() if line)
    if result.returncode != 0 or not any(line.startswith("PHANTOM_STATUS=") for line in lines):
        return PhantomProbeOutput(
            lines=("PHANTOM_STATUS=unknown", "PHANTOM_REASON=phantom-probe-failed"),
        )
    return PhantomProbeOutput(lines=lines)


def push_branch(runner: Runner, *, cwd: str | None = None) -> PushOutput:
    """Invoke the Rust owner and require its success KV contract."""
    result = runner.run(
        [str(larch_entrypoint(Path(__file__).resolve().parents[3])), "push", "branch"],
        cwd=cwd,
    )
    values = larch_io.parse_kv(result.stdout, skip_empty_key=True)
    if result.returncode != 0:
        return PushOutput(status="failed", branch=values.get("BRANCH", ""))
    branch = values.get("BRANCH", "")
    if not branch:
        return PushOutput(status="failed")
    return PushOutput(status="pushed", branch=branch)
