"""Dependency-free repository-root contract for test helpers."""

from __future__ import annotations

from pathlib import Path

# python/tests/support/repo_contract.py -> parents[3] is the repository root.
ROOT = Path(__file__).resolve().parents[3]


def repo_root() -> Path:
    """Return the resolved repository root used by test helpers."""
    return ROOT
