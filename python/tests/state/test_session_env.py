from __future__ import annotations
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from larch.core import config
from larch.state import finalize
from larch.core import proc
from larch.state import session_env
from larch.agents import agents

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


def record_write_env(
    monkeypatch: pytest.MonkeyPatch,
    *,
    returncode: int = 0,
    stderr: str = "",
) -> list[session_env.WriteEnvParams]:
    """Capture the parameters setup hands the Rust-owned session-env writer."""
    recorded: list[session_env.WriteEnvParams] = []

    def fake_run_write_env(params: session_env.WriteEnvParams) -> proc.CommandResult:
        recorded.append(params)
        return proc.CommandResult(("larch", "session", "write-env"), returncode, "", stderr, 0.0)

    monkeypatch.setattr(session_env, "run_write_env", fake_run_write_env)
    return recorded


def test_repo_from_gh_or_git_falls_back_when_gh_missing() -> None:
    class MissingGhRunner:
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
        ) -> proc.CommandResult:
            del timeout, cwd, env, check, stdout, stderr
            if argv and argv[0] == "gh":
                raise FileNotFoundError("gh")
            if list(argv[:3]) == ["git", "remote", "get-url"]:
                return proc.CommandResult(tuple(argv), 0, "git@github.com:owner/repo.git\n", "", 0.0)
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)

    assert session_env._repo_from_gh_or_git(MissingGhRunner()) == "owner/repo"  # pyright: ignore[reportPrivateUsage]


def test_setup_uses_caller_env_repo_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    caller = tmp_path / "caller.env"
    caller.write_text("REPO=caller/repo\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    recorded = record_write_env(monkeypatch)

    result = session_env.setup(
        prefix="pytest-",
        skip_preflight=True,
        skip_branch_check=True,
        write_session_env=str(tmp_path / "session-env.sh"),
        caller_env=str(caller),
    )

    assert result.exit_code == 0
    assert result.session_env_written is True
    assert [params.repo for params in recorded] == ["caller/repo"]


def test_setup_repo_fallback_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    recorded = record_write_env(monkeypatch)

    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        if argv and argv[0] == "gh":
            raise FileNotFoundError("gh")
        if list(argv[:3]) == ["git", "remote", "get-url"]:
            return proc.CommandResult(tuple(argv), 0, "git@github.com:git-owner/repo.git\n", "", 0.0)
        return proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(session_env.proc, "run", fake_run)
    rc = session_env.setup_main(
        [
            "--prefix",
            "pytest-",
            "--skip-preflight",
            "--skip-branch-check",
            "--write-session-env",
            str(tmp_path / "session-env.sh"),
        ],
    )

    assert rc == 0
    assert [params.repo for params in recorded] == ["git-owner/repo"]


def test_setup_runs_admission_preflight_without_skip(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "session-env.sh"
    calls: list[tuple[str, ...]] = []
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))

    def fake_run(argv: Sequence[str], **_kwargs: object) -> proc.CommandResult:
        calls.append(tuple(argv))
        if len(argv) >= 3 and argv[-2:] == ["admission", "preflight"]:
            return proc.CommandResult(tuple(argv), 0, "PREFLIGHT=ok\n", "", 0.0)
        if argv and "check-stale-plugin.sh" in argv[0]:
            return proc.CommandResult(tuple(argv), 0, "", "", 0.0)
        if argv and argv[0] == "gh":
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)
        if list(argv[:3]) == ["git", "remote", "get-url"]:
            return proc.CommandResult(tuple(argv), 0, "git@github.com:owner/repo.git\n", "", 0.0)
        if argv and argv[0] in {"codex", "cursor"}:
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)
        return proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(session_env.proc, "run", fake_run)
    rc = session_env.setup_main(
        [
            "--prefix",
            "pytest-",
            "--skip-branch-check",
            "--write-session-env",
            str(out),
        ],
    )
    assert rc == 0
    assert any("admission" in call and "preflight" in call for call in calls)


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


def test_setup_writes_session_id_and_keepalive(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    result = run_cli(
        "setup",
        "--prefix",
        "claude-implement",
        "--skip-preflight",
        "--skip-repo-check",
    )
    assert result.returncode == 0, result.stderr
    session_tmpdir = ""
    session_id = ""
    for line in result.stdout.splitlines():
        if line.startswith("SESSION_TMPDIR="):
            session_tmpdir = line.split("=", 1)[1]
        elif line.startswith("SESSION_ID="):
            session_id = line.split("=", 1)[1]
    assert session_tmpdir.startswith(str(cache / "larch" / "sessions" / "claude-implement-"))
    assert session_id
    assert "LARCH_RENDER_CACHE_DIR=" in result.stdout
    tmpdir = Path(session_tmpdir)
    session_id_file = (tmpdir / "session-id").read_text(encoding="utf-8").strip()
    assert session_id_file == session_id
    sentinel = (tmpdir / ".larch-keepalive").read_text(encoding="utf-8")
    assert "# larch session identity (hook routing)" in sentinel
    assert f"CLONE_PATH={Path.cwd()}" in sentinel
    assert f"SESSION_ID={session_id}" in sentinel
    assert not any(line.startswith(("PID=", "PPID=", "PREFIX=", "CREATED=", "NOTE=")) for line in sentinel.splitlines())


def test_ignore_placeholder_run_dirs_drops_only_run_n() -> None:
    names = ["run-1", "run-22", "run-abc", "shared", "run", "0199F1E2-2238-403D-89F3-AAAAAAAAAAAA"]
    assert session_env._ignore_placeholder_run_dirs(_="/x", names=names) == {"run-1", "run-22"}  # pyright: ignore[reportPrivateUsage]


def test_setup_carry_forward_drops_placeholder_run_dirs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # A fresh session must not inherit a previous session's non-unique run-1 dir
    # (issue #4397), but real UUID run dirs and shared/ are carried for resume.
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))
    prev = tmp_path / "prev"
    uuid_dir = "0199F1E2-2238-403D-89F3-F37CA6989999"
    for rel in (f"implement/{uuid_dir}", "implement/run-1", "shared"):
        (prev / "larch-logs" / rel).mkdir(parents=True)
    _ = (prev / "larch-logs" / "implement" / uuid_dir / "manifest.json").write_text("{}", encoding="utf-8")
    _ = (prev / "larch-logs" / "implement" / "run-1" / "manifest.json").write_text("{}", encoding="utf-8")
    _ = (prev / "larch-logs" / "shared" / "state.json").write_text("{}", encoding="utf-8")
    caller_env = tmp_path / "caller.env"
    _ = caller_env.write_text(f"PREV_IMPLEMENT_TMPDIR={prev}\n", encoding="utf-8")
    result = run_cli(
        "setup",
        "--prefix",
        "claude-implement",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(caller_env),
    )
    assert result.returncode == 0, result.stderr
    session_tmpdir = ""
    for line in result.stdout.splitlines():
        if line.startswith("SESSION_TMPDIR="):
            session_tmpdir = line.split("=", 1)[1]
    assert session_tmpdir
    carried = Path(session_tmpdir) / "larch-logs"
    assert (carried / "implement" / uuid_dir / "manifest.json").is_file()
    assert (carried / "shared" / "state.json").is_file()
    assert not (carried / "implement" / "run-1").exists()


def test_setup_presence_defaults_with_check_reviewers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    for key in TOOL_ENV_KEYS:
        monkeypatch.delenv(key, raising=False)

    def fake_check_reviewers(**_kwargs: object) -> agents.CheckReviewersResult:
        return agents.CheckReviewersResult(
            codex_binary_found=True,
            cursor_binary_found=True,
            codex_present=True,
            cursor_present=True,
        )

    monkeypatch.setattr(agents, "check_reviewers", fake_check_reviewers)

    def probe(caller_text: str, prefix: str) -> tuple[session_env.SessionSetupResult, list[session_env.WriteEnvParams]]:
        caller = tmp_path / f"{prefix}.env"
        caller.write_text(caller_text, encoding="utf-8")
        recorded = record_write_env(monkeypatch)
        result = session_env.setup(
            prefix=prefix,
            skip_preflight=True,
            skip_repo_check=True,
            check_reviewers=True,
            caller_env=str(caller),
            write_session_env=str(tmp_path / f"{prefix}-session-env.sh"),
        )
        assert result.exit_code == 0
        return result, recorded

    # Probed presence reaches stdout; only the binary-found rows reach the writer.
    result1, recorded1 = probe("", "test-presence-1")
    emitted1 = {e.key: e.value for e in result1.stdout_emissions if e.kind == "kv"}
    for key in ("CODEX_PRESENT", "CURSOR_PRESENT", "CODEX_BINARY_FOUND", "CURSOR_BINARY_FOUND"):
        assert emitted1[key] == "true"
    assert "CODEX_AVAILABLE" not in emitted1
    assert (recorded1[0].codex_binary_found, recorded1[0].cursor_binary_found) == ("true", "true")

    # A caller-supplied presence value never suppresses the live probe.
    result2, recorded2 = probe("CODEX_PRESENT=false\nCURSOR_PRESENT=true\n", "test-presence-2")
    emitted2 = {e.key: e.value for e in result2.stdout_emissions if e.kind == "kv"}
    assert emitted2["CODEX_PRESENT"] == "true"
    assert emitted2["CURSOR_PRESENT"] == "true"
    assert recorded2[0].codex_binary_found == "true"

    # A bounded dynamic-archetypes value carries; an out-of-range one is dropped.
    _result3, recorded3 = probe("LARCH_DYNAMIC_ARCHETYPES_MAX=1\n", "test-presence-3")
    assert recorded3[0].dynamic_archetypes == "1"
    result4, recorded4 = probe("LARCH_DYNAMIC_ARCHETYPES_MAX=9\n", "test-presence-4")
    assert recorded4[0].dynamic_archetypes == ""
    assert any("LARCH_DYNAMIC_ARCHETYPES_MAX" in line for line in result4.stderr_diagnostics)


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


def test_setup_direct_returns_emission_envelope(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    result = session_env.setup(prefix="pytest", skip_preflight=True, skip_repo_check=True)
    assert isinstance(result, session_env.SessionSetupResult)
    assert result.exit_code == 0
    assert result.repo_checked is False
    assert result.session_tmpdir.is_dir()
    assert result.session_id
    assert result.render_cache_dir == result.session_tmpdir / "render-cache"
    kv_keys = [e.key for e in result.stdout_emissions if e.kind == "kv"]
    assert kv_keys[:3] == ["SESSION_TMPDIR", "SESSION_ID", "LARCH_RENDER_CACHE_DIR"]
    assert "REPO" not in kv_keys
    assert "CLAUDE_BINARY_FOUND" in kv_keys
    with pytest.raises(FrozenInstanceError):
        result.exit_code = 1  # pyright: ignore[reportAttributeAccessIssue]  # assign to frozen field to assert FrozenInstanceError


def test_setup_direct_writes_session_env_and_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)
    caller = tmp_path / "caller.env"
    caller.write_text("REPO=owner/repo\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    out = tmp_path / "session-env.sh"
    recorded = record_write_env(monkeypatch)

    result = session_env.setup(prefix="pytest", skip_preflight=True, write_session_env=str(out), caller_env=str(caller))

    assert result.exit_code == 0
    assert result.repo_checked is True
    assert result.repo == "owner/repo"
    assert result.session_env_written is True
    assert [(params.output, params.repo, params.repo_unavailable) for params in recorded] == [
        (str(out), "owner/repo", "false")
    ]
    kv_keys = [e.key for e in result.stdout_emissions if e.kind == "kv"]
    assert "REPO" in kv_keys
    assert "REPO_UNAVAILABLE" in kv_keys


def test_setup_direct_reports_a_failed_writer_dispatch(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    _ = record_write_env(monkeypatch, returncode=1, stderr="ERROR=output parent is not a writable directory: /nope\n")

    result = session_env.setup(
        prefix="pytest",
        skip_preflight=True,
        skip_repo_check=True,
        write_session_env=str(tmp_path / "session-env.sh"),
    )

    assert result.exit_code == 1
    assert result.session_env_written is False
    assert result.stderr_diagnostics[-1] == "ERROR=output parent is not a writable directory: /nope"


def test_setup_emits_and_persists_repo_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("CLAUDE_PROJECT_DIR", raising=False)
    monkeypatch.delenv("REPO_ROOT", raising=False)
    recorded = record_write_env(monkeypatch)

    result = session_env.setup(
        prefix="pytest",
        skip_preflight=True,
        skip_repo_check=True,
        write_session_env=str(tmp_path / "session-env.sh"),
    )

    assert result.exit_code == 0
    kv = {e.key: e.value for e in result.stdout_emissions if e.kind == "kv"}
    assert kv["REPO_ROOT"] == str(Path.cwd())
    assert [params.repo_root for params in recorded] == [str(Path.cwd())]


def test_setup_repo_root_prefers_caller_env_then_project_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/env/project")
    caller = tmp_path / "caller.env"
    caller.write_text("REPO_ROOT=/caller/root\n", encoding="utf-8")
    with_caller = session_env.setup(prefix="pytest", skip_preflight=True, skip_repo_check=True, caller_env=str(caller))
    kv = {e.key: e.value for e in with_caller.stdout_emissions if e.kind == "kv"}
    assert kv["REPO_ROOT"] == "/caller/root"
    without_caller = session_env.setup(prefix="pytest", skip_preflight=True, skip_repo_check=True)
    kv2 = {e.key: e.value for e in without_caller.stdout_emissions if e.kind == "kv"}
    assert kv2["REPO_ROOT"] == "/env/project"


def test_setup_repo_root_rejects_relative_caller_value(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "/env/project")
    caller = tmp_path / "caller.env"
    caller.write_text("REPO_ROOT=relative/root\n", encoding="utf-8")
    result = session_env.setup(prefix="pytest", skip_preflight=True, skip_repo_check=True, caller_env=str(caller))
    kv = {e.key: e.value for e in result.stdout_emissions if e.kind == "kv"}
    assert kv["REPO_ROOT"] == "/env/project"


def test_setup_repo_root_skips_invalid_env_values(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Relative or newline-bearing env roots fall through instead of entering the stdout grammar (#7935)."""
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("CLAUDE_PROJECT_DIR", "relative/project")
    monkeypatch.setenv("REPO_ROOT", "/forged\nCODEX_PRESENT=true")
    result = session_env.setup(prefix="pytest", skip_preflight=True, skip_repo_check=True)
    kv = {e.key: e.value for e in result.stdout_emissions if e.kind == "kv"}
    assert kv["REPO_ROOT"] == str(Path.cwd())
