# pyright: reportUnknownVariableType=false, reportUnknownMemberType=false, reportUnknownArgumentType=false, reportUnusedCallResult=false, reportOptionalSubscript=false, reportOptionalMemberAccess=false, reportPossiblyUnboundVariable=false, reportUnnecessaryComparison=false, reportUnknownLambdaType=false, reportArgumentType=false
"""Tests for forked repo helper utilities."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from larch.core import forked_repo
from larch.core import proc
import pytest

CLI = Path(__file__).resolve().parent / "cli.py"


def _result(argv: list[str], returncode: int = 0, stdout: str = "", stderr: str = "") -> proc.CommandResult:
    return proc.CommandResult(tuple(argv), returncode, stdout, stderr, 0.0)


def test_normalize_github_url_shapes() -> None:
    assert forked_repo.normalize_github_url("git@github.com:Owner/Repo.git") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("https://github.com/Owner/Repo") == ("github.com", "owner/repo")
    assert forked_repo.normalize_github_url("not-a-url") is None


def test_parse_args_requires_owner_repo() -> None:
    try:
        forked_repo.parse_args(["--upstream", "bad", "--fork", "o/r"])
    except forked_repo.SetupError:
        pass
    else:  # pragma: no cover
        raise AssertionError("expected SetupError")


def test_restore_remote_state_reports_git_config_failure(monkeypatch: Any, capsys: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        if argv[:4] == ["git", "config", "--add", "remote.origin.url"]:
            return _result(argv, returncode=1, stderr="config failed")
        return _result(argv)

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    assert forked_repo.restore_remote_state(snapshot) is False
    assert "RECOVERY_REPORT rollback_failed=true reason=git-config-restore-failed" in capsys.readouterr().err


def test_rollback_remotes_if_active_restores_snapshot(monkeypatch: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    ctx = forked_repo.SetupContext(snapshot=snapshot, remote_phase_active=True)
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    forked_repo.rollback_remotes_if_active(ctx)
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_setup_in_verify_failure_rolls_back(monkeypatch: Any, capsys: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    ctx = forked_repo.SetupContext(
        upstream="acme/project",
        fork="me/project",
        snapshot=snapshot,
        remote_phase_active=True,
    )
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv, stdout="origin\n")

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    monkeypatch.setenv("LARCH_FORKED_REPO_INJECT_FAILURE", "in-verify")
    try:
        forked_repo.phase_verify(ctx)
    except forked_repo.SetupError:
        forked_repo.rollback_remotes_if_active(ctx)
    else:  # pragma: no cover
        raise AssertionError("expected SetupError")
    err = capsys.readouterr().err
    assert "remote rewrite failed; attempting rollback" in err
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_setup_submodule_failure_rolls_back_via_setup_main(monkeypatch: Any, capsys: Any) -> None:
    snapshot = forked_repo.RemoteSnapshot([("remote.origin.url", "https://github.com/acme/project.git")])
    calls: list[list[str]] = []

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        calls.append(argv)
        return _result(argv)

    def fake_remotes(ctx: forked_repo.SetupContext) -> None:
        ctx.snapshot = snapshot
        ctx.remote_phase_active = True

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    monkeypatch.setattr(forked_repo, "phase_preflight", lambda _ctx: None)
    monkeypatch.setattr(forked_repo, "phase_github", lambda _ctx: None)
    monkeypatch.setattr(forked_repo, "phase_remotes", fake_remotes)
    monkeypatch.setattr(forked_repo, "phase_submodules", lambda _ctx: forked_repo.die("submodule failed"))
    assert forked_repo.setup_main(["--upstream", "acme/project", "--fork", "me/project"]) == 1
    err = capsys.readouterr().err
    assert "remote rewrite failed; attempting rollback" in err
    assert any(call[:4] == ["git", "config", "--add", "remote.origin.url"] for call in calls)


def test_classify_remote_state_origin_upstream_only(monkeypatch: Any) -> None:
    calls: dict[tuple[str, ...], str] = {
        ("git", "remote"): "origin\n",
        ("git", "config", "--get-all", "remote.origin.url"): "https://github.com/acme/project.git\n",
        ("git", "config", "--get-all", "remote.origin.pushurl"): "",
    }

    def fake_run(argv: list[str], **_: object) -> proc.CommandResult:
        key = tuple(argv)
        if key == ("git", "remote"):
            return _result(argv, stdout=calls[key])
        if key[:3] == ("git", "config", "--get-all"):
            return _result(argv, stdout=calls.get(key, ""))
        return _result(argv)

    monkeypatch.setattr(forked_repo.proc, "run", fake_run)
    state = forked_repo.classify_remote_state(upstream="acme/project", fork="me/project", expected_host="github.com")
    assert state == "state-origin-upstream-only"


def _git(args: list[str], *, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(["git", *args], cwd=cwd, text=True, capture_output=True, check=False)


def _config_git_identity(repo: Path) -> None:
    _git(["config", "user.name", "Larch Test"], cwd=repo)
    _git(["config", "user.email", "larch-test@example.invalid"], cwd=repo)


def _commit_file(repo: Path, name: str, content: str) -> None:
    (repo / name).write_text(f"{content}\n", encoding="utf-8")
    _git(["add", name], cwd=repo)
    _git(["commit", "-m", f"commit {name}"], cwd=repo)


def _make_gh_stub(bin_dir: Path) -> None:
    bin_dir.mkdir(parents=True, exist_ok=True)
    (bin_dir / "gh").write_text(
        """#!/usr/bin/env bash
set -euo pipefail
mode="${GH_STUB_MODE:-ok}"
if [[ "$1" == "auth" && "${2:-}" == "status" ]]; then
  exit 0
fi
if [[ "$1" == "repo" && "${2:-}" == "view" ]]; then
  cat <<'JSON'
{"nameWithOwner":"me/project","parent":{"nameWithOwner":"acme/project"},"defaultBranchRef":{"name":"main"}}
JSON
  exit 0
fi
echo "unexpected gh invocation: $*" >&2
exit 2
""",
        encoding="utf-8",
    )
    (bin_dir / "gh").chmod(0o755)


def _new_fixture(tmp_path: Path, name: str) -> tuple[Path, Path, Path, Path, Path]:
    base = tmp_path / name
    upstream = base / "upstream.git"
    fork = base / "fork.git"
    work = base / "work"
    gh_bin = base / "bin"
    base.mkdir()
    _git(["init", "--bare", str(upstream)], cwd=base)
    _git(["init", "--bare", str(fork)], cwd=base)
    seed = base / "seed"
    _git(["init", str(seed)], cwd=base)
    _config_git_identity(seed)
    _git(["checkout", "-b", "main"], cwd=seed)
    _commit_file(seed, "README.md", "base")
    _git(["remote", "add", "upstream", str(upstream)], cwd=seed)
    _git(["push", "upstream", "main"], cwd=seed)
    _git(["remote", "add", "fork", str(fork)], cwd=seed)
    _git(["push", "fork", "main"], cwd=seed)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=upstream)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=fork)
    clone = subprocess.run(
        ["git", "clone", "-b", "main", str(upstream), str(work)],
        cwd=base,
        text=True,
        capture_output=True,
        check=False,
    )
    if clone.returncode != 0:
        subprocess.run(["git", "clone", str(upstream), str(work)], cwd=base, check=True)
    _config_git_identity(work)
    _git(["config", f"url.{upstream}.insteadOf", "https://github.com/acme/project.git"], cwd=work)
    _git(["config", "--add", f"url.{upstream}.insteadOf", "git@github.com:acme/project.git"], cwd=work)
    _git(["config", f"url.{fork}.insteadOf", "https://github.com/me/project.git"], cwd=work)
    _git(["config", "--add", f"url.{fork}.insteadOf", "git@github.com:me/project.git"], cwd=work)
    _git(["remote", "set-url", "origin", "https://github.com/acme/project.git"], cwd=work)
    _make_gh_stub(gh_bin)
    return base, upstream, fork, work, gh_bin


def _run_setup(work: Path, gh_bin: Path, upstream: Path, fork: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{gh_bin}:{env.get('PATH', '')}",
            "LARCH_QUIET_DISABLE": "1",
            "LARCH_FORKED_REPO_ALLOW_URL_OVERRIDE": "1",
            "LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_HTTPS": str(upstream),
            "LARCH_FORKED_REPO_URL_OVERRIDE_UPSTREAM_SSH": str(upstream),
            "LARCH_FORKED_REPO_URL_OVERRIDE_FORK_HTTPS": str(fork),
            "LARCH_FORKED_REPO_URL_OVERRIDE_FORK_SSH": str(fork),
        },
    )
    return subprocess.run(
        [sys.executable, str(CLI), "forked-repo", "setup", "--upstream", "acme/project", "--fork", "me/project", *extra],
        cwd=work,
        text=True,
        capture_output=True,
        env=env,
        check=False,
    )


def _assert_configured(work: Path, fork: Path) -> None:
    origin_url = _git(["config", "--get", "remote.origin.url"], cwd=work).stdout.strip()
    assert origin_url in {str(fork), "https://github.com/me/project.git", "git@github.com:me/project.git"}
    assert _git(["config", "--get", "remote.upstream.url"], cwd=work).stdout.strip() == "https://github.com/acme/project.git"
    assert (
        _git(["config", "--get", "remote.upstream.pushurl"], cwd=work).stdout.strip()
        == "larch-disabled://upstream-push-disabled"
    )
    assert _git(["config", "--get", "branch.main.remote"], cwd=work).stdout.strip() == "origin"
    assert _git(["config", "--get", "branch.main.merge"], cwd=work).stdout.strip() == "refs/heads/main"


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for forked-repo integration tests")
def test_setup_happy_remote_rewrite(tmp_path: Path) -> None:
    _base, upstream, fork, work, gh_bin = _new_fixture(tmp_path, "origin-only")
    result = _run_setup(work, gh_bin, upstream, fork)
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined
    assert "SETUP_FORKED_REPO_RESULT=ok" in combined
    _assert_configured(work, fork)


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for forked-repo integration tests")
def test_setup_push_disabled(tmp_path: Path) -> None:
    _base, upstream, fork, work, gh_bin = _new_fixture(tmp_path, "push-disabled")
    result = _run_setup(work, gh_bin, upstream, fork)
    assert result.returncode == 0, result.stderr
    push = _git(["push", "upstream", "main"], cwd=work)
    assert push.returncode != 0
    assert "larch-disabled" in push.stderr


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for forked-repo integration tests")
def test_setup_mirror_guard_requires_confirmation(tmp_path: Path) -> None:
    base, upstream, fork, work, gh_bin = _new_fixture(tmp_path, "mirror-no-confirm")
    edit = base / "upstream-edit"
    subprocess.run(["git", "clone", str(upstream), str(edit)], check=True)
    _config_git_identity(edit)
    _git(["checkout", "main"], cwd=edit)
    _commit_file(edit, "upstream.txt", "new upstream")
    _git(["push", "origin", "main"], cwd=edit)
    result = _run_setup(work, gh_bin, upstream, fork)
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode != 0, combined
    assert "rerun with --mirror-confirmed" in combined


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for forked-repo integration tests")
def test_setup_mirror_confirmed_syncs(tmp_path: Path) -> None:
    base, upstream, fork, work, gh_bin = _new_fixture(tmp_path, "mirror-confirmed")
    edit = base / "upstream-edit"
    subprocess.run(["git", "clone", str(upstream), str(edit)], check=True)
    _config_git_identity(edit)
    _git(["checkout", "main"], cwd=edit)
    _commit_file(edit, "upstream.txt", "new upstream")
    _git(["push", "origin", "main"], cwd=edit)
    sha = _git(["rev-parse", "HEAD"], cwd=edit).stdout.strip()
    _git(["push", "origin", f"{sha}:refs/changes/1"], cwd=edit)
    result = _run_setup(work, gh_bin, upstream, fork, "--mirror-confirmed")
    combined = f"{result.stdout}\n{result.stderr}"
    assert result.returncode == 0, combined
    assert "SETUP_FORKED_REPO_RESULT=mirror_synced" in combined
    assert _git(["rev-parse", "refs/heads/main"], cwd=upstream).stdout.strip() == _git(
        ["rev-parse", "refs/heads/main"], cwd=fork
    ).stdout.strip()
    assert _git(["show-ref", "--verify", "--quiet", "refs/changes/1"], cwd=fork).returncode != 0
