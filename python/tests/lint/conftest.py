"""Shared fixtures for lint-rule tests."""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

import pytest


LintMain = Callable[[list[str]], int]
LintRun = Callable[[Path, pytest.CaptureFixture[str]], tuple[int, str]]


def run(
    main: LintMain, root: Path, capsys: pytest.CaptureFixture[str]
) -> tuple[int, str]:
    """Run a lint entrypoint for ``root`` and return its stderr diagnostics."""
    return main(["--root", str(root)]), capsys.readouterr().err


def write_skill(root: Path, rel: str, body: str) -> None:
    """Write a skill fixture relative to its temporary repository root."""
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(body, encoding="utf-8")


def lint_runner(main: LintMain) -> LintRun:
    """Bind a lint entrypoint while preserving the standard test-call shape."""
    def invoke(root: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
        return run(main, root, capsys)

    return invoke


def _write_project(root: Path, *, files: dict[str, str]) -> None:
    """Write Python source fixtures below a temporary repository's python root."""
    for relpath, source in files.items():
        path = root / "python" / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        _ = path.write_text(source, encoding="utf-8")


# Keep the public import surface compatible with Pyright's private-use check.
write_project = _write_project
