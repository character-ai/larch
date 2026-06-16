# pyright: reportPrivateUsage=false
"""Tests for /design log publish flow port."""

from __future__ import annotations

import os
import stat
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import design_log_publish_flow

if TYPE_CHECKING:
    import pytest

RUN_ID = "ABCDEF01-2345-6789-ABCD-EF0123456789"
LOG_BRANCH = f"larch-logs/design-{RUN_ID}"


def _git(*argv: str, cwd: Path) -> None:
    _ = subprocess.run(["git", *argv], cwd=cwd, check=True, capture_output=True)


def _write_gh_stub(path: Path, *, pr_create_rc: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _ = path.write_text(
        "#!/usr/bin/env bash\n"
        'if [ "$1" = "pr" ] && [ "$2" = "create" ]; then\n'
        f"  if [ {pr_create_rc} -ne 0 ]; then echo 'gh: pr create failed' >&2; exit {pr_create_rc}; fi\n"
        "  echo 'https://github.com/o/r/pull/77'\n"
        "  exit 0\n"
        "fi\n"
        'if [ "$1" = "pr" ] && [ "$2" = "merge" ]; then exit 0; fi\n'
        "exit 0\n",
        encoding="utf-8",
    )
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


def _operator_repo_with_remote(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()
    _git("init", "-q", cwd=repo)
    _git("checkout", "-q", "-b", "main", cwd=repo)
    _git("config", "user.email", "t@example.com", cwd=repo)
    _git("config", "user.name", "t", cwd=repo)
    _ = (repo / "README.md").write_text("seed\n", encoding="utf-8")
    _git("add", "README.md", cwd=repo)
    _git("commit", "-q", "-m", "seed", cwd=repo)
    origin = tmp_path / "origin.git"
    _git("init", "-q", "--bare", str(origin), cwd=tmp_path)
    _git("remote", "add", "origin", str(origin), cwd=repo)
    _git("push", "-q", "-u", "origin", "main", cwd=repo)
    return repo


def _run_publish(repo: Path, design: Path, bin_dir: Path) -> subprocess.CompletedProcess[str]:
    real_cli = Path(__file__).with_name("cli.py")
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    # The real cli is used for run-log init/commit + redact; all git writes are
    # cwd-scoped to the disposable worktree, never the operator or plugin repo.
    env["CLAUDE_PLUGIN_ROOT"] = str(Path(real_cli).resolve().parents[1])
    return subprocess.run(
        [
            sys.executable,
            str(real_cli),
            "design",
            "log-publish",
            "--design-tmpdir",
            str(design),
            "--run-id",
            RUN_ID,
            "--issue",
            "33",
        ],
        cwd=repo,
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )


def test_log_publish_dry_run_success(tmp_path: Path) -> None:
    cli_py = Path(__file__).with_name("cli.py")
    design = tmp_path / "design"
    design.mkdir()
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)
    env = os.environ.copy()
    env["PATH"] = f"{bin_dir}:{env.get('PATH', '')}"
    result = subprocess.run(
        [sys.executable, str(cli_py), "design", "log-publish", "--design-tmpdir", str(design), "--run-id", "RUN1", "--issue", "12", "--dry-run"],
        capture_output=True,
        text=True,
        check=False,
        env=env,
    )
    assert result.returncode == 0
    assert "PUBLISH_OK=true" in result.stdout


def test_log_publish_commits_pushes_and_opens_pr(tmp_path: Path) -> None:
    # The design run tree is committed to a dedicated branch and PR'd; the
    # operator working tree stays clean (issue #4395), and ship is best-effort.
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=0)

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=true" in result.stdout, result.stderr
    assert "PR_NUMBER=77" in result.stdout
    assert "PR_URL=https://github.com/o/r/pull/77" in result.stdout
    # The operator working tree is never polluted, so the next /implement passes preflight.
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=False)
    assert status.stdout.strip() == "", status.stdout
    # The clean-success path deletes the local branch (it lives on the remote).
    branches = subprocess.run(["git", "branch", "--list", LOG_BRANCH], cwd=repo, capture_output=True, text=True, check=False)
    assert branches.stdout.strip() == ""
    # The pushed branch carries the redacted design run tree.
    origin = tmp_path / "origin.git"
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", LOG_BRANCH], cwd=origin, capture_output=True, text=True, check=False)
    assert f"larch-logs/design/{RUN_ID}/artifact.txt" in ls.stdout, ls.stdout
    assert f"larch-logs/design/{RUN_ID}/manifest.json" in ls.stdout, ls.stdout
    meta = (design / ".design-log-publish-metadata.env").read_text(encoding="utf-8")
    assert "DESIGN_LOG_PR_NUMBER=77" in meta


def test_log_publish_pr_failure_keeps_tree_clean_and_emits_recovery(tmp_path: Path) -> None:
    # If the PR cannot be opened, the operator tree still stays clean and the
    # pushed branch is surfaced as a recovery branch (PUBLISH_OK=false).
    repo = _operator_repo_with_remote(tmp_path)
    design = tmp_path / "design"
    design.mkdir()
    _ = (design / "artifact.txt").write_text("artifact", encoding="utf-8")
    bin_dir = tmp_path / "bin"
    _write_gh_stub(bin_dir / "gh", pr_create_rc=1)

    result = _run_publish(repo, design, bin_dir)
    assert result.returncode == 0, result.stderr
    assert "PUBLISH_OK=false" in result.stdout
    assert f"RECOVERY_BRANCH={LOG_BRANCH}" in result.stdout
    status = subprocess.run(["git", "status", "--porcelain"], cwd=repo, capture_output=True, text=True, check=False)
    assert status.stdout.strip() == "", status.stdout
    origin = tmp_path / "origin.git"
    ls = subprocess.run(["git", "ls-tree", "-r", "--name-only", LOG_BRANCH], cwd=origin, capture_output=True, text=True, check=False)
    assert f"larch-logs/design/{RUN_ID}/artifact.txt" in ls.stdout, ls.stdout


def test_spawn_detached_admin_merge_routes_to_ship_design_log(monkeypatch: pytest.MonkeyPatch) -> None:
    # Bug #4524: GitHub-native --auto can never satisfy the active "Code review"
    # ruleset's required-review gate for an unreviewed automated PR, so log PRs
    # never merge. The fix routes the log PR through the existing ship design-log
    # admin-merge waiter, launched detached so /design is not blocked on CI (#4404).
    captured_argv: list[str] = []
    captured_kwargs: dict[str, object] = {}

    def fake_popen(argv: list[str], **kwargs: object) -> object:
        captured_argv.extend(argv)
        captured_kwargs.update(kwargs)
        return object()

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", fake_popen)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge("/p/python/cli.py", "77", "o/r", "/repo")

    assert captured_argv == [
        sys.executable, "/p/python/cli.py", "ship", "design-log", "--pr-number", "77", "--repo", "o/r",
    ]
    assert "--auto" not in captured_argv
    assert captured_kwargs["start_new_session"] is True
    assert captured_kwargs["cwd"] == "/repo"
    assert captured_kwargs["stdin"] == subprocess.DEVNULL
    assert captured_kwargs["stdout"] == subprocess.DEVNULL
    assert captured_kwargs["stderr"] == subprocess.DEVNULL


def test_spawn_detached_admin_merge_omits_repo_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_argv: list[str] = []

    def fake_popen(argv: list[str], **_kwargs: object) -> object:
        captured_argv.extend(argv)
        return object()

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", fake_popen)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge("/p/python/cli.py", "77", "", "/repo")

    assert captured_argv == [sys.executable, "/p/python/cli.py", "ship", "design-log", "--pr-number", "77"]
    assert "--repo" not in captured_argv


def test_spawn_detached_admin_merge_swallows_launch_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    # Best-effort: a launch failure must not raise (the log PR stays open for a
    # manual/CI merge and the working tree is already clean).
    def boom(_argv: list[str], **_kwargs: object) -> object:
        raise OSError("no exec")

    monkeypatch.setattr(design_log_publish_flow.subprocess, "Popen", boom)  # type: ignore[arg-type]
    design_log_publish_flow._spawn_detached_admin_merge("/p/python/cli.py", "77", "o/r", "/repo")
