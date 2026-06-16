"""Shared helpers for python/lint_*.py file-scanning linters."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

GIT = shutil.which("git") or "git"


def parse_root_args(
    argv: list[str],
    *,
    prog: str,
    description: str | None,
) -> argparse.Namespace | None:
    """Parse the shared ``--root`` argument for a lint entrypoint.

    Returns None when argparse exits non-zero so callers can surface a usage
    exit code; re-raises on the ``--help`` exit-0 path.
    """
    parser = argparse.ArgumentParser(prog=prog, description=description)
    _ = parser.add_argument("--root", default=str(Path(__file__).resolve().parents[1]))
    try:
        return parser.parse_args(argv)
    except SystemExit as exc:
        if exc.code == 0:
            raise
        return None


def git_rooted(root: Path) -> bool:
    """True when ``root`` is inside a git work tree."""
    return subprocess.run(
        [GIT, "-C", str(root), "rev-parse", "--is-inside-work-tree"],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    ).returncode == 0
