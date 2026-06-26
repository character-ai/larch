"""Phantom dirty-tree probes for /implement checkpoint flows."""

from __future__ import annotations

import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
import larch_io

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


def _newline_fold(text: str) -> str:
    return " ".join(text.split())


def _parse_kv_output(text: str) -> dict[str, str]:
    return larch_io.parse_kv(text)


def _baseline_dirty_probe( *,
    runner: Runner,
    baseline_file: str,
    cwd: str | None,
) -> tuple[str, str, str]:
    """Run dirty-tree baseline detection."""
    result = runner.run(
        [
            "python3",
            str(_REPO_ROOT / "python" / "cli.py"),
            "dirty-tree",
            "baseline",
            "--baseline",
            baseline_file,
        ],
        cwd=cwd,
    )
    if result.returncode != 0:
        return "unknown", "check-mid-run-dirty-tree-failed", ""
    output = result.stdout
    if not output.strip():
        return "unknown", "unparseable-check-output", ""

    fields = _parse_kv_output(output)
    status = fields.get("STATUS", "")
    reason = fields.get("REASON", "")
    new_untracked = fields.get("NEW_UNTRACKED_PATHS_FILE", "")

    if status == "clean":
        return "clean", "", ""
    if status == "unknown":
        return "unknown", reason or "unknown", ""
    if status == "dirty":
        return "dirty", reason or "working-tree-dirty", new_untracked
    return "unknown", "unparseable-check-output", ""


def check_phantom_dirty(
    runner: Runner,
    *,
    step: str,
    baseline_file: str | None = None,
    phantom_paths_dir: str | None = None,
    cwd: str | None = None,
) -> PhantomDirtyResult:
    """Baseline phantom probe for ``cli.py git check-phantom-dirty``."""
    implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    paths_dir = phantom_paths_dir or implement_tmpdir
    if not paths_dir:
        return PhantomDirtyResult(status="unknown", reason="phantom-paths-dir-required")
    baseline = baseline_file or (f"{implement_tmpdir}/untracked-baseline.z" if implement_tmpdir else "")
    if not baseline:
        return PhantomDirtyResult(status="unknown", reason="baseline-required")
    if not _STEP_TOKEN_RE.fullmatch(step):
        return PhantomDirtyResult(status="unknown", reason="bad-step")
    status, reason, new_untracked_file = _baseline_dirty_probe(runner=runner, baseline_file=baseline, cwd=cwd)
    if status == "clean":
        return PhantomDirtyResult(status="clean")
    if status == "unknown":
        return PhantomDirtyResult(status="unknown", reason=reason)
    if new_untracked_file and Path(new_untracked_file).is_file() and Path(new_untracked_file).stat().st_size > 0:
        phantom_dir = Path(paths_dir)
        try:
            phantom_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return PhantomDirtyResult(status="unknown", reason="phantom-paths-dir-create-failed")
        paths_file = phantom_dir / f"phantom-paths-{step}.z"
        try:
            _ = shutil.copy2(new_untracked_file, paths_file)
        except OSError:
            return PhantomDirtyResult(status="unknown", reason="phantom-paths-write-failed")
        try:
            count = paths_file.read_bytes().count(b"\0")
        except OSError:
            return PhantomDirtyResult(status="unknown", reason="phantom-count-failed")
        return PhantomDirtyResult(
            status="phantom",
            count=count,
            paths_file=str(paths_file),
        )
    return PhantomDirtyResult(status="tracked-only")


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
            "python3",
            str(_REPO_ROOT / "python" / "cli.py"),
            "run-log",
            "append-entry",
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
    return _newline_fold(tail) or f"run-log append-entry failed (exit {append.returncode})"


def probe_with_warn(
    runner: Runner,
    *,
    step: str,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomProbeResult:
    """Probe and append execution-issue warnings on dirty/inconclusive results."""
    if not os.environ.get("IMPLEMENT_TMPDIR"):
        return PhantomProbeResult(
            dirty=PhantomDirtyResult(status="unknown", reason="IMPLEMENT_TMPDIR-unset"),
        )
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
