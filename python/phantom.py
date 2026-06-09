"""Phantom dirty-tree probes for /implement checkpoint flows."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

from proc import Runner


@dataclass(frozen=True)
class PhantomDirtyResult:
    status: str
    reason: str = ""
    count: int = 0
    paths_file: str = ""


@dataclass(frozen=True)
class PhantomProbeResult:
    dirty: PhantomDirtyResult
    append_warn_error: str = ""


_REPO_ROOT = Path(__file__).resolve().parents[1]
_STEP_TOKEN_RE = re.compile(r"^[A-Za-z0-9_.-]+$")


def _parse_kv(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def _newline_fold(text: str) -> str:
    return " ".join(text.split())


def check_phantom_dirty(
    runner: Runner,
    *,
    step: str,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomDirtyResult:
    """Wrapper over check-phantom-dirty.sh (lib-phantom-probe.sh parity)."""
    implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not implement_tmpdir:
        return PhantomDirtyResult(status="unknown", reason="IMPLEMENT_TMPDIR-unset")
    if not _STEP_TOKEN_RE.fullmatch(step):
        return PhantomDirtyResult(status="unknown", reason="bad-step")
    baseline = baseline_file or f"{implement_tmpdir}/untracked-baseline.z"
    env = {**os.environ, "LARCH_QUIET_DISABLE": "1"}
    result = runner.run(
        [
            str(_REPO_ROOT / "scripts" / "check-phantom-dirty.sh"),
            "--baseline",
            baseline,
            "--step",
            step,
            "--phantom-paths-dir",
            implement_tmpdir,
        ],
        cwd=cwd,
        env=env,
    )
    kv = _parse_kv(result.stdout)
    status = kv.get("STATUS", "unknown")
    reason = kv.get("REASON", "")
    count_text = kv.get("PHANTOM_COUNT", "0")
    count = int(count_text) if count_text.isdigit() else 0
    return PhantomDirtyResult(
        status=status,
        reason=reason,
        count=count,
        paths_file=kv.get("PHANTOM_PATHS_FILE", ""),
    )


def _append_execution_warn(
    runner: Runner,
    *,
    entry: str,
    cwd: str | None,
) -> str:
    implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not implement_tmpdir:
        return "IMPLEMENT_TMPDIR-unset"
    log_file = f"{implement_tmpdir}/execution-issues.md"
    append = runner.run(
        [
            str(_REPO_ROOT / "scripts" / "append-execution-issue.sh"),
            "--log",
            log_file,
            "--category",
            "Warnings",
            "--entry",
            entry,
        ],
        cwd=cwd,
        env={**os.environ, "LARCH_QUIET_DISABLE": "1"},
    )
    if append.returncode == 0:
        return ""
    combined = append.stdout + append.stderr
    err_line = next((line[6:] for line in combined.splitlines() if line.startswith("ERROR=")), "")
    if err_line:
        return _newline_fold(err_line)
    tail = "\n".join(combined.splitlines()[-5:])
    return _newline_fold(tail) or f"append-execution-issue.sh failed (exit {append.returncode})"


def probe_with_warn(
    runner: Runner,
    *,
    step: str,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomProbeResult:
    """Probe and append execution-issue warnings on dirty/inconclusive results."""
    dirty = check_phantom_dirty(runner, step=step, baseline_file=baseline_file, cwd=cwd)
    append_error = ""
    implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if dirty.status == "phantom":
        entry = (
            f"- **Step {step} — phantom untracked files:** "
            f"{dirty.count} file(s) appeared since session baseline "
            f"(inspect {implement_tmpdir}/phantom-paths-{step}.z locally)"
        )
        append_error = _append_execution_warn(runner, entry=entry, cwd=cwd)
        if append_error:
            _ = _append_execution_warn(
                runner,
                entry=f"- **Step {step} — phantom warning append failed: {append_error}**",
                cwd=cwd,
            )
    elif dirty.status == "unknown":
        reason = dirty.reason or "unknown"
        entry = (
            f"- **Step {step} — phantom detection inconclusive:** "
            f"STATUS=unknown REASON={reason}"
        )
        append_error = _append_execution_warn(runner, entry=entry, cwd=cwd)
        if append_error:
            _ = _append_execution_warn(
                runner,
                entry=f"- **Step {step} — phantom warning append failed: {append_error}**",
                cwd=cwd,
            )
    return PhantomProbeResult(dirty=dirty, append_warn_error=append_error)
