"""Tests for the delegated agentic CI fixer CLI surface."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import ci_agentic_fix

if TYPE_CHECKING:
    import pytest


def test_missing_repo_root_fails_closed(capsys: pytest.CaptureFixture[str]) -> None:
    rc = ci_agentic_fix.main([
        "--pr", "1",
        "--repo", "o/r",
        "--repo-root", "relative",
        "--run-id", "42",
        "--output-dir", "/tmp",
        "--implement-tmpdir", "/tmp",
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=waterfall-failed" in out
    assert "DETAIL=missing-repo-root" in out


def test_valid_repo_root_rejects_missing_directory(tmp_path: Path) -> None:
    assert ci_agentic_fix._valid_repo_root(str(tmp_path / "missing")) is None  # pyright: ignore[reportPrivateUsage]
