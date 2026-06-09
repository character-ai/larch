"""Phantom dirty-tree probes for /implement checkpoint flows."""

from __future__ import annotations

import os
import tempfile
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


def _parse_kv(text: str) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in text.splitlines():
        if "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key] = value
    return parsed


def check_phantom_dirty(
    runner: Runner,
    *,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomDirtyResult:
    """Side-effect-free wrapper over the retained check-mid-run-dirty-tree.sh probe."""
    paths_fd, paths_path = tempfile.mkstemp(prefix="phantom-paths.", suffix=".txt")
    os.close(paths_fd)
    env = dict(os.environ)
    if baseline_file:
        env["NEW_UNTRACKED_PATHS_FILE"] = baseline_file
    result = runner.run(
        [str(_REPO_ROOT / "scripts" / "check-mid-run-dirty-tree.sh"), "--paths-file", paths_path],
        cwd=cwd,
        env=env,
    )
    kv = _parse_kv(result.stdout)
    status = kv.get("STATUS", "error" if result.returncode else "clean")
    reason = kv.get("REASON", "")
    count_text = kv.get("PHANTOM_COUNT", "0")
    count = int(count_text) if count_text.isdigit() else 0
    return PhantomDirtyResult(
        status=status,
        reason=reason,
        count=count,
        paths_file=kv.get("PHANTOM_PATHS_FILE", paths_path),
    )


def probe_with_warn(
    runner: Runner,
    *,
    step_prefix: str,
    short_name: str,
    baseline_file: str | None = None,
    cwd: str | None = None,
) -> PhantomProbeResult:
    """Probe and append the existing execution-issue warning on dirty results."""
    dirty = check_phantom_dirty(runner, baseline_file=baseline_file, cwd=cwd)
    append_error = ""
    if dirty.status not in {"clean", "ok"} and dirty.count > 0:
        append = runner.run(
            [
                str(_REPO_ROOT / "scripts" / "append-execution-issue.sh"),
                "--site",
                f"{step_prefix}-{short_name}",
                "--reason",
                dirty.reason or dirty.status,
            ],
            cwd=cwd,
        )
        if append.returncode != 0:
            append_error = (append.stdout + append.stderr).replace("\n", " ").strip() or f"append-execution-issue.sh failed (exit {append.returncode})"
    return PhantomProbeResult(dirty=dirty, append_warn_error=append_error)
