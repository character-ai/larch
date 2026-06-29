"""Tests for shared repository-root discovery helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Sequence

from larch.git.repo_roots import consumer_repo_root

if TYPE_CHECKING:
    import pytest


def test_consumer_repo_root_returns_git_toplevel_from_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-q", str(repo)], check=True)

    assert consumer_repo_root(repo) == repo.resolve()


def test_consumer_repo_root_resolves_explicit_nested_cwd(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    nested = repo / "a" / "b"
    nested.mkdir(parents=True)
    _ = subprocess.run(["git", "init", "-q", str(repo)], check=True)

    assert consumer_repo_root(nested) == repo.resolve()


def test_consumer_repo_root_returns_none_outside_work_tree(tmp_path: Path) -> None:
    assert consumer_repo_root(tmp_path) is None


def test_consumer_repo_root_returns_none_when_git_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        _argv: Sequence[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check
        raise OSError("git missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert consumer_repo_root() is None


def test_consumer_repo_root_returns_none_on_empty_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: Sequence[str],
        *,
        capture_output: bool,
        text: bool,
        check: bool,
    ) -> subprocess.CompletedProcess[str]:
        del capture_output, text, check
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert consumer_repo_root() is None
