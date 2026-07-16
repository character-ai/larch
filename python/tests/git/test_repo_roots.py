"""Tests for shared repository-root discovery helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Sequence

from larch.core.repo_roots import consumer_repo_root, plugin_root

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
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        raise OSError("git missing")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert consumer_repo_root() is None


def test_consumer_repo_root_returns_none_on_empty_stdout(monkeypatch: pytest.MonkeyPatch) -> None:
    def fake_run(
        argv: Sequence[str],
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(args=list(argv), returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    assert consumer_repo_root() is None


def test_consumer_repo_root_resolves_a_linked_worktree(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    worktree = tmp_path / "worktree"
    repo.mkdir()
    _ = subprocess.run(["git", "init", "-q", str(repo)], check=True)
    _ = subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.invalid"], check=True)
    _ = subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test User"], check=True)
    _ = subprocess.run(["git", "-C", str(repo), "commit", "--allow-empty", "-qm", "initial"], check=True)
    _ = subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", str(worktree)], check=True)

    assert consumer_repo_root(worktree) == worktree.resolve()


def test_plugin_root_prefers_environment_and_normalizes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fallback = tmp_path / "fallback"
    configured = tmp_path / "configured"
    fallback.mkdir()
    configured.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(configured / "."))

    assert plugin_root(fallback) == configured.resolve()


def test_plugin_root_uses_fallback_when_environment_is_empty(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    fallback = tmp_path / "fallback"
    fallback.mkdir()
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    assert plugin_root(fallback / ".") == fallback.resolve()
