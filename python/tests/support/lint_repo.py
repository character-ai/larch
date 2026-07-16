"""Shared throwaway-git-repository fixture for lint baseline tests."""

from __future__ import annotations

import subprocess
from pathlib import Path

_GIT_INIT_STEPS = (
    ("init", "-q"),
    ("config", "user.email", "test@example.com"),
    ("config", "user.name", "test"),
    ("add", "-A"),
    ("commit", "-q", "-m", "fixture", "--allow-empty"),
)


def init_repo(root: Path) -> None:
    """Initialize a disposable git repository fixture under ``root``."""
    for step in _GIT_INIT_STEPS:
        _ = subprocess.run(  # lint-subprocess-via-runner: ok test fixture bootstraps a throwaway git repo
            ["git", *step], cwd=root, check=True  # noqa: S607 - git is a required test fixture dependency
        )
