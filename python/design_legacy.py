"""Compatibility subprocess helpers for design lifecycle CLI ports."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from collections.abc import Sequence


_REPO_ROOT = Path(__file__).resolve().parents[1]


def repo_root() -> Path:
    return _REPO_ROOT


def _script_root_for(relpath: str) -> Path:
    env_root = os.environ.get("CLAUDE_PLUGIN_ROOT", "")
    if env_root:
        candidate_root = Path(env_root)
        candidate = candidate_root / relpath
        if candidate.exists() and ("/tmp/" in str(candidate_root) or "/var/folders/" in str(candidate_root)):  # noqa: S108
            return candidate_root
    return _REPO_ROOT


def run_script(*, relpath: str, argv: Sequence[str]) -> int:
    root = _script_root_for(relpath)
    script = root / relpath
    env: dict[str, str] = os.environ.copy()
    env["CLAUDE_PLUGIN_ROOT"] = str(root)
    try:
        completed = subprocess.run([str(script), *argv], env=env, check=False)
    except FileNotFoundError:
        print(f"ERROR: legacy script not found: {relpath}", file=sys.stderr)
        return 127
    return int(completed.returncode)
