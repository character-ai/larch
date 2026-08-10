from __future__ import annotations
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false
import json
import os
import shutil
import subprocess
import sys
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from larch.core import config
from larch.state import finalize
from larch.state import session_env

from test_support import CLI, make_design_tmpdir, seed_run_params, write_design_source_env

TOOL_ENV_KEYS = ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_AVAILABLE", "CURSOR_AVAILABLE", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND")


def clean_env(extra: dict[str, str] | None = None) -> dict[str, str]:
    merged = os.environ.copy()
    for key in TOOL_ENV_KEYS:
        merged.pop(key, None)
    if extra:
        merged.update(extra)
    return merged


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = clean_env()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "session", *args],
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


def test_local_cleanup_rejects_main_branch() -> None:
    result = run_cli("local-cleanup", "--branch", "main")
    assert result.returncode == 1
    assert "must not be 'main'" in result.stderr


def test_cache_sessions_root_resolution(monkeypatch: pytest.MonkeyPatch) -> None:
    # `session cleanup-tmpdir` moved to the Rust owner in issue #8057; the shared
    # root derivation still backs the Python session writers that remain.
    monkeypatch.setenv("XDG_CACHE_HOME", "relative-cache")
    monkeypatch.setenv("HOME", "")
    assert session_env.cleanup_cache_sessions_root() == Path("relative-cache/larch/sessions")
    assert finalize.cache_sessions_root().is_absolute()


def test_reap_pid_residuals_refuses_symlinked_ancestors(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    home = tmp_path / "home"
    redirect = tmp_path / "redirect"
    home.mkdir()
    redirect.mkdir()
    monkeypatch.setenv("HOME", str(home))
    cache_root = home / ".cache"
    cache_root.mkdir()
    (redirect / "sessions").mkdir()
    target = redirect / "sessions" / "current-design-env-123.sh"
    target.write_text("sentinel\n", encoding="utf-8")
    (cache_root / "larch").symlink_to(redirect)

    with pytest.raises(OSError, match="symlinked"):
        session_env.reap_pid_residuals("123")

    assert target.is_file()


def test_reap_pid_residuals_removes_leaf_design_symlink_and_residuals(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    sessions = home / ".cache" / "larch" / "sessions"
    home.mkdir()
    sessions.mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))

    link_target = tmp_path / "design-target-123.sh"
    link_target.write_text("sentinel\n", encoding="utf-8")
    link = sessions / "current-design-env-123.sh"
    link.symlink_to(link_target)
    run_path = sessions / "design-run-123.sh"
    run_path.write_text("run\n", encoding="utf-8")
    parsed_path = sessions / "step0-parsed-123.env"
    parsed_path.write_text("parsed\n", encoding="utf-8")

    session_env.reap_pid_residuals("123")

    assert not link.exists()
    assert link_target.is_file()
    assert not run_path.exists()
    assert not parsed_path.exists()


def _git(args: list[str], *, cwd: Path, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=False)
    if check and completed.returncode != 0:
        msg = f"git {' '.join(args)} failed: {completed.stderr}"
        raise RuntimeError(msg)
    return completed


def _config_git_identity(repo: Path) -> None:
    _git(["config", "user.email", "ci@test"], cwd=repo)
    _git(["config", "user.name", "Test CI"], cwd=repo)


def _commit_path(repo: Path, rel: str, content: str, subject: str) -> None:
    path = repo / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content + "\n", encoding="utf-8")
    _git(["add", "--", rel], cwd=repo)
    _git(["commit", "-q", "-m", subject], cwd=repo)


def _setup_remote_repo(tmp_path: Path, label: str) -> Path:
    remote = tmp_path / f"{label}-origin.git"
    seed = tmp_path / f"{label}-seed"
    repo = tmp_path / f"{label}-repo"
    _git(["init", "-q", "--bare", str(remote)], cwd=tmp_path)
    seed.mkdir()
    _git(["init", "-q"], cwd=seed)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=seed)
    _config_git_identity(seed)
    _commit_path(seed, "README.md", "initial", "init")
    _git(["remote", "add", "origin", str(remote)], cwd=seed)
    _git(["push", "-q", "-u", "origin", "main"], cwd=seed)
    _git(["symbolic-ref", "HEAD", "refs/heads/main"], cwd=remote)
    _git(["clone", "-q", str(remote), str(repo)], cwd=tmp_path)
    _git(["checkout", "-q", "main"], cwd=repo)
    _config_git_identity(repo)
    _git(["branch", "feature"], cwd=repo)
    return repo


def _run_local_cleanup(repo: Path, *, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
    merged["LARCH_QUIET_DISABLE"] = "1"
    if env:
        merged.update(env)
    return subprocess.run(
        [sys.executable, str(CLI), "session", "local-cleanup", "--branch", "feature"],
        cwd=repo,
        text=True,
        capture_output=True,
        env=merged,
        check=False,
    )


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for local-cleanup integration tests")
def test_local_cleanup_preserves_ahead_commits_and_reports_divergence(tmp_path: Path) -> None:
    prefix = config.FLUSH_COMMIT_SUBJECT_PREFIX

    flush_repo = _setup_remote_repo(tmp_path, "flush-orphan")
    _commit_path(
        flush_repo,
        "larch-logs/implement/prior-run/session-transcript.jsonl",
        '{"type":"message","text":"prior"}',
        f"{prefix}implement run prior-run",
    )
    flush_origin = _git(["rev-parse", "origin/main"], cwd=flush_repo).stdout.strip()
    flush_result = _run_local_cleanup(flush_repo)
    assert "CLEANUP_SUCCESS=true" in flush_result.stdout
    assert "BRANCH_DELETED=true" in flush_result.stdout
    assert "Dropping" not in flush_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=flush_repo).stdout.strip() != flush_origin
    assert (flush_repo / "larch-logs/implement/prior-run/session-transcript.jsonl").is_file()

    non_flush_repo = _setup_remote_repo(tmp_path, "non-flush-ahead")
    _commit_path(non_flush_repo, "operator-note.txt", "keep me", "operator local note")
    non_flush_origin = _git(["rev-parse", "origin/main"], cwd=non_flush_repo).stdout.strip()
    non_flush_result = _run_local_cleanup(non_flush_repo)
    assert "CLEANUP_SUCCESS=true" in non_flush_result.stdout
    assert "Dropping" not in non_flush_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=non_flush_repo).stdout.strip() != non_flush_origin
    assert (non_flush_repo / "operator-note.txt").is_file()

    squash_repo = _setup_remote_repo(tmp_path, "squash-gap")
    remote_url = _git(["remote", "get-url", "origin"], cwd=squash_repo).stdout.strip()
    _commit_path(
        squash_repo,
        "larch-logs/implement/squash-gap/session-transcript.jsonl",
        '{"type":"message","text":"flush-only"}',
        f"{prefix}implement run squash-gap",
    )
    pusher = tmp_path / "squash-gap-pusher"
    _git(["clone", "-q", remote_url, str(pusher)], cwd=tmp_path)
    _config_git_identity(pusher)
    _commit_path(pusher, "landed-from-pr.txt", "squash simulation", "feat: simulate post-merge remote advance")
    _git(["push", "-q", "origin", "main"], cwd=pusher)
    local_head = _git(["rev-parse", "HEAD"], cwd=squash_repo).stdout.strip()
    squash_result = _run_local_cleanup(squash_repo)
    assert "CLEANUP_SUCCESS=false" in squash_result.stdout
    assert "BRANCH_DELETED=false" in squash_result.stdout
    assert "Dropping" not in squash_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=squash_repo).stdout.strip() == local_head


@pytest.mark.skipif(shutil.which("git") is None, reason="git required for local-cleanup integration tests")
def test_local_cleanup_reports_branch_delete_failure(tmp_path: Path) -> None:
    repo = _setup_remote_repo(tmp_path, "branch-delete-failure")
    worktree = tmp_path / "feature-worktree"
    _git(["worktree", "add", "-q", str(worktree), "feature"], cwd=repo)

    result = _run_local_cleanup(repo)

    assert "CLEANUP_SUCCESS=false" in result.stdout
    assert "BRANCH_DELETED=false" in result.stdout
    assert "Failed to delete local branch feature" in result.stderr
    assert _git(["branch", "--show-current"], cwd=worktree).stdout.strip() == "feature"


def test_check_live_mutation_auth_test_deny_blocks_session_auth(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Test-deny blocks session-backed auth but not operator-invoked."""
    monkeypatch.setenv(config.LIVE_MUTATION_TEST_DENY_KEY, "true")
    sessions_root = tmp_path / ".cache" / "larch" / "sessions"
    session_dir = sessions_root / "claude-implement-test"
    session_dir.mkdir(parents=True)
    ctx = session_dir / "session-env.sh"
    ctx.write_text(f"{config.LIVE_MUTATION_AUTH_KEY}=true\nLARCH_RUN_ID=run-1\n", encoding="utf-8")
    authorized, reason = session_env.check_live_mutation_auth(
        context_file=ctx,
        operator_mode=False,
        run_id="run-1",
        trusted_root=session_dir,
    )
    assert not authorized
    assert reason == "test-denied"


def test_check_live_mutation_auth_operator_bypasses_test_deny(monkeypatch: pytest.MonkeyPatch) -> None:
    """Operator mode bypasses test-deny."""
    monkeypatch.setenv(config.LIVE_MUTATION_TEST_DENY_KEY, "true")
    authorized, reason = session_env.check_live_mutation_auth(context_file=None, operator_mode=True)
    assert authorized
    assert reason == config.LIVE_MUTATION_OPERATOR_MODE


def test_check_live_mutation_auth_operator(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    authorized, reason = session_env.check_live_mutation_auth(context_file=None, operator_mode=True)
    assert authorized
    assert reason == config.LIVE_MUTATION_OPERATOR_MODE


def test_check_live_mutation_auth_session_valid(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    sessions_root = tmp_path / ".cache" / "larch" / "sessions"
    session_dir = sessions_root / "claude-implement-test"
    session_dir.mkdir(parents=True)
    ctx = session_dir / "session-env.sh"
    ctx.write_text(f"{config.LIVE_MUTATION_AUTH_KEY}=true\nLARCH_RUN_ID=run-1\n", encoding="utf-8")
    authorized, reason = session_env.check_live_mutation_auth(
        context_file=ctx,
        operator_mode=False,
        run_id="run-1",
        trusted_root=session_dir,
    )
    assert authorized
    assert reason == config.LIVE_MUTATION_SESSION_MODE


def test_check_live_mutation_auth_rejects_context_outside_trusted_root(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    trusted_root = tmp_path / "claude-implement-trusted"
    outside_root = tmp_path / "claude-implement-outside"
    trusted_root.mkdir()
    outside_root.mkdir()
    ctx = outside_root / "session-env.sh"
    _ = ctx.write_text(f"{config.LIVE_MUTATION_AUTH_KEY}=true\nLARCH_RUN_ID=run-1\n", encoding="utf-8")
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)

    authorized, reason = session_env.check_live_mutation_auth(
        context_file=ctx,
        operator_mode=False,
        run_id="run-1",
        trusted_root=trusted_root,
    )

    assert authorized is False
    assert reason == config.LIVE_MUTATION_REFUSAL_REASON


def test_check_live_mutation_auth_no_context(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    authorized, reason = session_env.check_live_mutation_auth(context_file=None, operator_mode=False)
    assert not authorized
    assert reason == config.LIVE_MUTATION_REFUSAL_REASON


def test_check_live_mutation_auth_symlink_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    sessions_root = tmp_path / ".cache" / "larch" / "sessions"
    sessions_root.mkdir(parents=True)
    real_file = tmp_path / "real.sh"
    real_file.write_text(f"{config.LIVE_MUTATION_AUTH_KEY}=true\n", encoding="utf-8")
    symlink = sessions_root / "session-env.sh"
    symlink.symlink_to(real_file)
    authorized, _ = session_env.check_live_mutation_auth(context_file=symlink, operator_mode=False)
    assert not authorized


def test_check_live_mutation_auth_missing_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.LIVE_MUTATION_TEST_DENY_KEY, raising=False)
    sessions_root = tmp_path / ".cache" / "larch" / "sessions"
    sessions_root.mkdir(parents=True)
    ctx = sessions_root / "session-env.sh"
    ctx.write_text("LARCH_RUN_ID=run-1\n", encoding="utf-8")
    authorized, _ = session_env.check_live_mutation_auth(context_file=ctx, operator_mode=False)
    assert not authorized


def test_design_source_helper_matches_writer_key_contract(tmp_path: Path) -> None:
    """Fixture helper stays on WRITE_DESIGN_ENV_KEYS and omits implement-only aliases."""
    design = make_design_tmpdir(tmp_path)
    text = (design / "source-env.sh").read_text(encoding="utf-8")
    assert "LARCH_CLAUDE_PLUGIN_ROOT" not in text
    assert "CODEX_PRESENT" not in text
    assert "CURSOR_PRESENT" not in text
    assert "export CLAUDE_PLUGIN_ROOT=" in text
    assert "export REPO_ROOT=" in text
    params = seed_run_params(design)
    assert json.loads(params.read_text(encoding="utf-8"))["schema_version"] == 3
    refreshed = write_design_source_env(design, overrides={"REPO": "owner/name"})
    assert "export REPO=owner/name\n" in refreshed.read_text(encoding="utf-8")


def test_write_id_direct_writes_then_preserves(tmp_path: Path) -> None:
    out = tmp_path / "session-id"
    first = session_env.write_id(output=out)
    assert isinstance(first, session_env.WriteIdResult)
    assert first.wrote is True
    assert first.session_id
    assert out.read_text(encoding="utf-8").strip() == first.session_id
    out.write_text("keep\n", encoding="utf-8")
    second = session_env.write_id(output=out)
    assert second.wrote is False
    assert second.session_id == "keep"
    assert out.read_text(encoding="utf-8") == "keep\n"
    with pytest.raises(FrozenInstanceError):
        second.wrote = True  # pyright: ignore[reportAttributeAccessIssue]  # assign to frozen field to assert FrozenInstanceError


def test_write_id_direct_rejects_disallowed_root() -> None:
    with pytest.raises(OSError, match="allowed session root"):
        session_env.write_id(output=Path("/etc/larch-not-allowed/session-id"))
