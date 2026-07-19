"""Tests for shared repository-root discovery helpers."""

from __future__ import annotations

import subprocess
from pathlib import Path
from typing import TYPE_CHECKING
from collections.abc import Mapping, Sequence

from larch.core.proc import CommandResult
from larch.core.repo_roots import (
    consumer_repo_root,
    larch_entrypoint,
    plugin_root,
    repo_root_from_probe,
    repo_root_probe,
    RepoRootProbeOptions,
)

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


def test_larch_entrypoint_uses_verified_bootstrap_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    plugin = tmp_path / "plugin"
    plugin.mkdir()
    monkeypatch.setenv("CLAUDE_PLUGIN_ROOT", str(plugin))

    assert larch_entrypoint() == plugin / "scripts" / "larch.sh"


def test_repo_root_probe_preserves_runner_diagnostics_and_paths(tmp_path: Path) -> None:
    captured: list[tuple[list[str], str | None, float | None, bool]] = []

    class FakeRunner:
        def run(
            self,
            argv: Sequence[str],
            *,
            timeout: float | None = None,
            cwd: str | None = None,
            env: Mapping[str, str] | None = None,
            check: bool = False,
            stdout: int | None = None,
            stderr: int | None = None,
        ) -> CommandResult:
            del env, stdout, stderr
            captured.append((list(argv), cwd, timeout, check))
            return CommandResult(tuple(argv), 19, "", "not a repository", 0.0)

    result = repo_root_probe(
        runner=FakeRunner(),
        options=RepoRootProbeOptions(
            git_cwd=tmp_path / "git-cwd",
            runner_cwd=tmp_path / "runner-cwd",
            git_bin="/usr/bin/git",
            timeout=2.0,
            check=True,
        ),
    )

    assert result.returncode == 19
    assert result.stderr == "not a repository"
    assert repo_root_from_probe(result) is None
    assert captured == [(
        ["/usr/bin/git", "-C", str(tmp_path / "git-cwd"), "rev-parse", "--show-toplevel"],
        str(tmp_path / "runner-cwd"),
        2.0,
        True,
    )]
