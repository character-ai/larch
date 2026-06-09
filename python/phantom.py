"""Phantom dirty-tree probes for /implement checkpoint flows."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import git
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


def _nul_paths(text: str) -> list[str]:
    if not text:
        return []
    return sorted({part for part in text.split("\0") if part})


def _read_nul_paths(path: Path) -> frozenset[str]:
    try:
        data = path.read_bytes()
    except OSError:
        return frozenset()
    if not data:
        return frozenset()
    return frozenset(part.decode() for part in data.split(b"\0") if part)


def _baseline_dirty_probe(
    runner: Runner,
    baseline_file: str,
    *,
    cwd: str | None,
) -> tuple[str, str, list[str]]:
    """Port check-mid-run-dirty-tree.sh --mode baseline (subset for phantom mapping)."""
    status_result = git.status_porcelain(runner, cwd=cwd)
    if status_result.returncode != 0:
        return "unknown", "git-status-failed", []

    unstaged = runner.run(["git", "diff", "--name-only", "-z"], cwd=cwd)
    if unstaged.returncode != 0:
        return "unknown", "git-diff-failed", []
    staged = runner.run(["git", "diff", "--name-only", "--cached", "-z"], cwd=cwd)
    if staged.returncode != 0:
        return "unknown", "git-diff-cached-failed", []

    tracked = _nul_paths(unstaged.stdout) + [p for p in _nul_paths(staged.stdout) if p not in _nul_paths(unstaged.stdout)]
    tracked = sorted(set(tracked))

    untracked_result = runner.run(
        ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        cwd=cwd,
    )
    if untracked_result.returncode != 0:
        return "unknown", "git-ls-files-failed", []
    current_untracked = _nul_paths(untracked_result.stdout)

    baseline_path = Path(baseline_file)
    if baseline_path.is_file():
        baseline_set = _read_nul_paths(baseline_path)
        new_untracked = [path for path in current_untracked if path not in baseline_set]
    else:
        new_untracked = []
        if current_untracked:
            return "unknown", "baseline-missing-untracked-ambiguous", []

    if tracked or new_untracked:
        return "dirty", "working-tree-dirty", new_untracked
    return "clean", "", []


def check_phantom_dirty(
    runner: Runner,
    *,
    step: str,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomDirtyResult:
    """Baseline phantom probe (check-phantom-dirty.sh parity without shell delegation)."""
    implement_tmpdir = os.environ.get("IMPLEMENT_TMPDIR", "")
    if not implement_tmpdir:
        return PhantomDirtyResult(status="unknown", reason="IMPLEMENT_TMPDIR-unset")
    if not _STEP_TOKEN_RE.fullmatch(step):
        return PhantomDirtyResult(status="unknown", reason="bad-step")
    baseline = baseline_file or f"{implement_tmpdir}/untracked-baseline.z"
    status, reason, new_untracked = _baseline_dirty_probe(runner, baseline, cwd=cwd)
    if status == "clean":
        return PhantomDirtyResult(status="clean")
    if status == "unknown":
        return PhantomDirtyResult(status="unknown", reason=reason)
    if new_untracked:
        phantom_dir = Path(implement_tmpdir)
        try:
            phantom_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return PhantomDirtyResult(status="unknown", reason="phantom-paths-dir-create-failed")
        paths_file = phantom_dir / f"phantom-paths-{step}.z"
        payload = "\0".join(new_untracked).encode() + b"\0"
        try:
            paths_file.write_bytes(payload)
        except OSError:
            return PhantomDirtyResult(status="unknown", reason="phantom-paths-write-failed")
        return PhantomDirtyResult(
            status="phantom",
            count=len(new_untracked),
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
