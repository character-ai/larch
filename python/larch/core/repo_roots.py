"""Shared repository and installed-plugin root discovery helpers."""

from __future__ import annotations

import os
from collections.abc import Callable
from pathlib import Path

from larch.core import config, proc
from larch.core.proc import CommandResult, Runner


def consumer_repo_root(
    cwd: Path | str | None = None,
    *,
    runner: Runner | None = None,
    run: Callable[[list[str]], CommandResult] | None = None,
    git_bin: str = "git",
) -> Path | None:
    """Return the consumer repo's git toplevel, or ``None`` outside a work tree."""
    start = Path(cwd) if cwd is not None else Path.cwd()
    argv = [git_bin, "-C", str(start), "rev-parse", "--show-toplevel"]
    try:
        if run is not None:
            result = run(argv)
        elif runner is None:
            result = proc.run(argv)
        else:
            result = runner.run(argv, cwd=str(start))
    except OSError:
        return None
    out = result.stdout.strip()
    if result.returncode != 0 or not out:
        return None
    return Path(out).resolve()


def plugin_root(fallback: Path | str | None = None, *, use_env: bool = True) -> Path:
    """Return the configured plugin root, falling back to a caller-owned path."""
    configured = os.environ.get(config.ENV_CLAUDE_PLUGIN_ROOT, "") if use_env else ""
    default = Path(__file__).resolve().parents[3]
    return Path(configured or fallback or default).resolve()
