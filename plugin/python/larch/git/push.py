"""Pre-push working-tree guard shared by the Python PR helpers.

``push rebase`` and ``push checkpoint-probe`` moved to the Rust runtime
(``crates/larch-cli/src/push_rebase.rs``, issue #7762); only the clean-worktree
guard consumed by ``larch.git.pr`` remains in Python.
"""

from __future__ import annotations

from larch.git import git
from larch.errors import ShipError
from larch.core.proc import Runner


def assert_clean_worktree(runner: Runner, *, cwd: str | None = None) -> None:
    """Fail closed when the working tree has uncommitted changes (#2434)."""
    result = git.status_porcelain(runner, cwd=cwd)
    if result.returncode != 0:
        msg = "git status --porcelain failed before push"
        raise ShipError(msg)
    if result.stdout.strip():
        msg = "uncommitted working-tree changes detected before push"
        raise ShipError(msg)
