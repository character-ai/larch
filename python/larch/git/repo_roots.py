"""Shared repository-root discovery helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path


def consumer_repo_root(cwd: Path | None = None) -> Path | None:
    """Return the consumer repo's git toplevel, or ``None`` outside a work tree.

    Larch may run from a plugin cache while plan-command paths remain
    repo-relative to the consumer repository. Validators need the consumer repo
    as their first root and the plugin root as their second root so scripts that
    exist in the consumer repo but not the cache pass the #4490 dual-root
    existence check.
    """
    start = cwd or Path.cwd()
    try:
        result = subprocess.run(
            ["git", "-C", str(start), "rev-parse", "--show-toplevel"],  # noqa: S607
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return None
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return None
    return Path(out).resolve()
