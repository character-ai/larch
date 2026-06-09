from __future__ import annotations
# pyright: reportUnusedCallResult=false

import json
import os
import shutil
import subprocess
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
import pytest

import config
import finalize
import logging_util
import proc
import session_env

CLI = Path(__file__).with_name("cli.py")


def run_cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    merged = os.environ.copy()
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


def test_read_key_defaults_and_embedded_equals(tmp_path: Path) -> None:
    session = tmp_path / "session-env.sh"
    session.write_text("TOKEN=a=b=c\nEMPTY=\nTOKEN_EXTRA=wrong\n", encoding="utf-8")
    got = run_cli("read-key", "--file", str(session), "--key", "TOKEN")
    assert got.returncode == 0
    assert got.stdout == "a=b=c\n"
    empty = run_cli("read-key", "--file", str(session), "--key", "EMPTY", "--default", "fallback")
    assert empty.stdout == "fallback\n"
    missing = run_cli("read-key", "--file", str(tmp_path / "missing"), "--key", "TOKEN", "--default", "fallback")
    assert missing.returncode == 0
    assert missing.stdout == "fallback\n"
    forgotten = run_cli("read-key", "--key", "TOKEN", "--default", "fallback")
    assert forgotten.returncode == 1


def test_write_env_writer_guard_and_plugin_root_only(tmp_path: Path) -> None:
    out = tmp_path / "session-env.sh"
    ok = run_cli(
        "write-env",
        "--output",
        str(out),
        "--repo",
        "owner/repo",
        "--repo-unavailable",
        "false",
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--run-id",
        "RUN_1",
        env={"CLAUDE_PLUGIN_ROOT": "/tmp/larch-plugin"},
    )
    assert ok.returncode == 0, ok.stderr
    text = out.read_text(encoding="utf-8")
    assert "REPO=owner/repo\n" in text
    assert "CODEX_AVAILABLE=true\n" in text
    assert "LARCH_RUN_ID=RUN_1\n" in text
    assert (tmp_path / "plugin-root.env").read_text(encoding="utf-8") == "CLAUDE_PLUGIN_ROOT=/tmp/larch-plugin\nexport CLAUDE_PLUGIN_ROOT\n"
    bad = run_cli("write-env", "--output", "/etc/larch-session-env", "--repo-unavailable", "false")
    assert bad.returncode == 1
    null = run_cli("write-env", "--output", "/dev/null", "--repo-unavailable", "false")
    assert null.returncode == 0
    plugin = tmp_path / "plugin-root.env"
    only = run_cli("write-env", "--plugin-root-only", "--output", str(plugin), "--value", "/tmp/plugin-root")
    assert only.returncode == 0
    assert "CLAUDE_PLUGIN_ROOT=/tmp/plugin-root" in plugin.read_text(encoding="utf-8")


def test_write_design_env_source_safe_and_home_symlink(tmp_path: Path) -> None:
    home = tmp_path / "home"
    home.mkdir()
    xdg = tmp_path / "xdg"
    design = tmp_path / "design dir"
    design.mkdir()
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(home), "XDG_CACHE_HOME": str(xdg), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    result = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--codex-present",
        "true",
        "--claude-pid",
        "12345",
        env=env,
    )
    assert result.returncode == 0, result.stderr
    source = subprocess.run(["bash", "-c", f"source {out}; printf '%s|%s|%s' \"$DESIGN_TMPDIR\" \"$CODEX_AVAILABLE\" \"$CLAUDE_PLUGIN_ROOT\""], text=True, capture_output=True, check=False)
    assert source.stdout == f"{design}|true|/tmp/plugin"
    link = home / ".cache" / "larch" / "sessions" / "current-design-env-12345.sh"
    assert link.is_symlink()
    assert link.readlink() == out


def test_write_run_params_and_read_classification(tmp_path: Path) -> None:
    out = tmp_path / "run-params.json"
    result = run_cli(
        "write-run-params",
        "--classification",
        "SIMPLE",
        "--output",
        str(out),
        "--reason",
        "small",
        "--partition-requested",
        "true",
    )
    assert result.returncode == 0
    assert f"RUN_PARAMS_WRITTEN={out}" in result.stdout
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["schema_version"] == 3
    assert data["design_classification"] == "SIMPLE"
    assert data["partition_requested"] is True
    read = run_cli("read-classification", str(out))
    assert read.stdout == "SIMPLE\n"
    invalid = run_cli("write-run-params", "--classification", "MEDIUM", "--output", str(out))
    assert invalid.returncode == 2
    missing_parent = run_cli("write-run-params", "--classification", "HARD", "--output", str(tmp_path / "nope" / "x.json"))
    assert missing_parent.returncode == 1


def test_persist_run_flags_write_id_and_entry_gate(tmp_path: Path) -> None:
    flags = run_cli("persist-run-flags", "--implement-tmpdir", str(tmp_path), "--no-issues", "false", "--emergency-requested", "true")
    assert flags.returncode == 0
    assert flags.stdout == "RUN_FLAGS_PERSISTED=true\n"
    assert "EMERGENCY_REQUESTED=true\n" in (tmp_path / "run-flags.sh").read_text(encoding="utf-8")
    missing = run_cli("persist-run-flags", "--implement-tmpdir", str(tmp_path))
    assert missing.returncode == 2
    sid = tmp_path / "session-id"
    first = run_cli("write-id", "--output", str(sid))
    assert first.returncode == 0
    original = sid.read_text(encoding="utf-8")
    sid.write_text("keep\n", encoding="utf-8")
    second = run_cli("write-id", "--output", str(sid))
    assert second.returncode == 0
    assert sid.read_text(encoding="utf-8") == "keep\n"
    gate = run_cli("entry-gate", "--mode", "implement", "--current-branch", "feature", "--is-main", "false", "--is-user-branch", "true", "--user-prefix", "user")
    assert gate.returncode == 0
    assert "ENTRY_GATE=continue" in gate.stdout
    assert original


def test_restore_finalize_state_raw_rhs_and_20_keys(tmp_path: Path) -> None:
    (tmp_path / "ship-pr-state.sh").write_text(
        "BRANCH_NAME=feature\nPR_TITLE=Implement $(echo x)=y\nSTALL_TRACKING=false\nBAIL_REASON=needs=user\nRUN_ID=RUN1\n",
        encoding="utf-8",
    )
    (tmp_path / "finalize-state.sh").write_text("STALL_TRACKING=true\nSTALL_STEP=18a\n", encoding="utf-8")
    result = run_cli("restore-finalize-state", "--implement-tmpdir", str(tmp_path))
    assert result.returncode == 0
    lines = (tmp_path / "finalize-state.sh").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 20
    assert "PR_TITLE=Implement $(echo x)=y" in lines
    assert "STALL_TRACKING=true" in lines
    assert "STALL_STEP=18a" in lines
    assert (tmp_path / "final-bail-reason.txt").read_text(encoding="utf-8") == "needs=user"


def test_write_design_env_refresh_preserves_prior_bools(tmp_path: Path) -> None:
    out = tmp_path / "source-env.sh"
    env = {"HOME": str(tmp_path / "home"), "XDG_CACHE_HOME": str(tmp_path / "xdg"), "CLAUDE_PLUGIN_ROOT": "/tmp/plugin"}
    design = tmp_path / "design"
    design.mkdir()
    first = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--codex-present",
        "true",
        "--cursor-present",
        "false",
        "--claude-pid",
        "42",
        env=env,
    )
    assert first.returncode == 0, first.stderr
    second = run_cli(
        "write-design-env",
        "--output",
        str(out),
        "--design-tmpdir",
        str(design),
        "--session-id",
        "sid-1",
        "--claude-pid",
        "42",
        env=env,
    )
    assert second.returncode == 0, second.stderr
    text = out.read_text(encoding="utf-8")
    assert "CODEX_PRESENT=true\n" in text
    assert "CURSOR_PRESENT=false\n" in text


def test_write_env_rejects_invalid_run_id(tmp_path: Path) -> None:
    out = tmp_path / "session-env.sh"
    bad = run_cli(
        "write-env",
        "--output",
        str(out),
        "--repo-unavailable",
        "false",
        "--run-id",
        "bad id",
        env={"CLAUDE_PLUGIN_ROOT": "/tmp/larch-plugin"},
    )
    assert bad.returncode == 1


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
            if argv and "github-remote-repo.sh" in argv[0]:
                return proc.CommandResult(tuple(argv), 0, "owner/repo\n", "", 0.0)
            return proc.CommandResult(tuple(argv), 1, "", "", 0.0)

    assert session_env._repo_from_gh_or_git(MissingGhRunner()) == "owner/repo"  # pyright: ignore[reportPrivateUsage]


def test_setup_uses_caller_env_repo_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    caller = tmp_path / "caller.env"
    caller.write_text("REPO=caller/repo\nREPO_UNAVAILABLE=false\n", encoding="utf-8")
    out = tmp_path / "session-env.sh"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    result = run_cli(
        "setup",
        "--prefix",
        "pytest-",
        "--skip-preflight",
        "--skip-branch-check",
        "--write-session-env",
        str(out),
        "--caller-env",
        str(caller),
    )
    assert result.returncode == 0, result.stderr
    assert "REPO=caller/repo" in out.read_text(encoding="utf-8")


def test_setup_repo_fallback_without_gh(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out = tmp_path / "session-env.sh"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.delenv("CLAUDE_PLUGIN_ROOT", raising=False)

    def fake_run(argv: list[str], **_kwargs: object) -> proc.CommandResult:
        if argv and argv[0] == "gh":
            raise FileNotFoundError("gh")
        if argv and "github-remote-repo.sh" in argv[0]:
            return proc.CommandResult(tuple(argv), 0, "git-owner/repo\n", "", 0.0)
        return proc.CommandResult(tuple(argv), 0, "", "", 0.0)

    monkeypatch.setattr(session_env.proc, "run", fake_run)
    rc = session_env.setup_main(
        [
            "--prefix",
            "pytest-",
            "--skip-preflight",
            "--skip-branch-check",
            "--write-session-env",
            str(out),
        ],
    )
    assert rc == 0
    assert "REPO=git-owner/repo" in out.read_text(encoding="utf-8")


def test_read_classification_missing_and_invalid_paths(tmp_path: Path) -> None:
    missing = run_cli("read-classification", str(tmp_path / "missing.json"))
    assert missing.stdout == "HARD\n"
    assert "run-params not readable" in missing.stderr
    bad = tmp_path / "bad.json"
    bad.write_text('{"workflow_path":"SIMPLE"}\n', encoding="utf-8")
    invalid = run_cli("read-classification", str(bad))
    assert invalid.stdout == "HARD\n"
    assert "design_classification missing or invalid" in invalid.stderr


def test_local_cleanup_rejects_main_branch() -> None:
    result = run_cli("local-cleanup", "--branch", "main")
    assert result.returncode == 1
    assert "must not be 'main'" in result.stderr


def test_cleanup_tmpdir_allowlist_and_cache_roots(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("XDG_CACHE_HOME", "relative-cache")
    monkeypatch.setenv("HOME", "")
    assert session_env.cleanup_cache_sessions_root() == Path("relative-cache/larch/sessions")
    assert finalize.cache_sessions_root().is_absolute()
    target = tmp_path / "cleanup-me"
    target.mkdir()
    result = run_cli("cleanup-tmpdir", "--dir", str(target), env={"TMPDIR": str(tmp_path)})
    assert result.returncode == 0
    assert not target.exists()
    assert (tmp_path / "larch-cleanup-audit.log").is_file()
    bad = run_cli("cleanup-tmpdir", "--dir", "/etc/not-larch")
    assert bad.returncode == 1


def test_read_key_emits_on_fd3_under_quiet_mode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(config.ENV_LARCH_QUIET_DISABLE, raising=False)
    monkeypatch.setenv(config.ENV_IMPLEMENT_TMPDIR, str(tmp_path))
    logging_util.reset_quiet_state()
    session = tmp_path / "session-env.sh"
    session.write_text("TOKEN=secret-value\n", encoding="utf-8")
    read_fd, write_fd = os.pipe()
    saved_stdout = os.dup(1)
    try:
        os.dup2(write_fd, 1)
        os.close(write_fd)
        rc = session_env.read_key_main(["--file", str(session), "--key", "TOKEN"])
        os.dup2(saved_stdout, 1)
        contract = os.read(read_fd, 4096).decode()
    finally:
        os.close(read_fd)
        os.close(saved_stdout)
    assert rc == 0
    assert contract == "secret-value\n"


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


def test_setup_presence_defaults_with_check_reviewers(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    (stub_bin / "codex").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (stub_bin / "cursor").write_text("#!/usr/bin/env bash\nexit 0\n", encoding="utf-8")
    (stub_bin / "codex").chmod(0o755)
    (stub_bin / "cursor").chmod(0o755)
    cache = tmp_path / "cache"
    monkeypatch.setenv("XDG_CACHE_HOME", str(cache))

    env1 = tmp_path / "env1.txt"
    env1.write_text("", encoding="utf-8")
    out1 = tmp_path / "session-env1.txt"
    result1 = run_cli(
        "setup",
        "--prefix",
        "test-presence-1",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env1),
        "--check-reviewers",
        "--write-session-env",
        str(out1),
        env={"PATH": f"{stub_bin}:{os.environ.get('PATH', '')}"},
    )
    assert result1.returncode == 0, result1.stderr
    for key in ("CODEX_PRESENT=true", "CURSOR_PRESENT=true", "CODEX_AVAILABLE=true", "CURSOR_AVAILABLE=true"):
        assert key in result1.stdout
    text1 = out1.read_text(encoding="utf-8")
    assert "CODEX_PRESENT=true\n" in text1
    assert "CURSOR_PRESENT=true\n" in text1
    assert "CODEX_AVAILABLE=true\n" in text1
    assert "CURSOR_AVAILABLE=true\n" in text1

    env2 = tmp_path / "env2.txt"
    env2.write_text("CODEX_PRESENT=false\nCURSOR_PRESENT=true\n", encoding="utf-8")
    out2 = tmp_path / "session-env2.txt"
    result2 = run_cli(
        "setup",
        "--prefix",
        "test-presence-2",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env2),
        "--check-reviewers",
        "--write-session-env",
        str(out2),
        env={"PATH": f"{stub_bin}:{os.environ.get('PATH', '')}"},
    )
    assert result2.returncode == 0, result2.stderr
    assert "CODEX_PRESENT=false" in result2.stdout
    assert "CURSOR_PRESENT=true" in result2.stdout
    text2 = out2.read_text(encoding="utf-8")
    assert "CODEX_PRESENT=false\n" in text2
    assert "CURSOR_PRESENT=true\n" in text2

    env3 = tmp_path / "env3.txt"
    env3.write_text(
        "CODEX_PRESENT=true\nCURSOR_PRESENT=false\nLARCH_DYNAMIC_ARCHETYPES_MAX=3\n",
        encoding="utf-8",
    )
    out3 = tmp_path / "session-env3.txt"
    result3 = run_cli(
        "setup",
        "--prefix",
        "test-presence-3",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env3),
        "--check-reviewers",
        "--write-session-env",
        str(out3),
        env={"PATH": f"{stub_bin}:{os.environ.get('PATH', '')}"},
    )
    assert result3.returncode == 0, result3.stderr
    assert "LARCH_DYNAMIC_ARCHETYPES_MAX=3\n" in out3.read_text(encoding="utf-8")

    env4 = tmp_path / "env4.txt"
    env4.write_text(
        "CODEX_PRESENT=true\nCURSOR_PRESENT=false\nLARCH_DYNAMIC_ARCHETYPES_MAX=9\n",
        encoding="utf-8",
    )
    out4 = tmp_path / "session-env4.txt"
    result4 = run_cli(
        "setup",
        "--prefix",
        "test-presence-4",
        "--skip-preflight",
        "--skip-repo-check",
        "--caller-env",
        str(env4),
        "--check-reviewers",
        "--write-session-env",
        str(out4),
        env={"PATH": f"{stub_bin}:{os.environ.get('PATH', '')}"},
    )
    assert result4.returncode == 0, result4.stderr
    assert "LARCH_DYNAMIC_ARCHETYPES_MAX=" not in out4.read_text(encoding="utf-8")
    assert "ignoring invalid LARCH_DYNAMIC_ARCHETYPES_MAX" in result4.stderr


def test_entry_gate_accepts_explicit_empty_current_branch() -> None:
    gate = run_cli(
        "entry-gate",
        "--mode",
        "implement",
        "--current-branch",
        "",
        "--is-main",
        "true",
        "--is-user-branch",
        "false",
        "--user-prefix",
        "sergey",
    )
    assert gate.returncode == 0
    assert "ENTRY_GATE=strict" in gate.stdout
    assert "SKIP_BRANCH_CHECK=false" in gate.stdout
    design = run_cli(
        "entry-gate",
        "--mode",
        "design",
        "--current-branch",
        "",
        "--is-main",
        "true",
        "--is-user-branch",
        "false",
        "--user-prefix",
        "sergey",
        "--branch-info-supplied",
        "true",
    )
    assert design.returncode == 0
    assert "ENTRY_GATE=continue" in design.stdout


def test_write_run_params_rejects_empty_boolean_flags(tmp_path: Path) -> None:
    out = tmp_path / "run-params.json"
    invalid = run_cli(
        "write-run-params",
        "--classification",
        "SIMPLE",
        "--output",
        str(out),
        "--partition-requested",
        "",
    )
    assert invalid.returncode == 2
    assert "requires a value" in invalid.stderr


def test_cleanup_tmpdir_fails_when_removal_blocked(tmp_path: Path) -> None:
    target = tmp_path / "cleanup-me"
    target.mkdir()
    (target / "keep").write_text("x", encoding="utf-8")
    if os.name != "nt":
        target.chmod(0o555)
        try:
            result = run_cli("cleanup-tmpdir", "--dir", str(target), env={"TMPDIR": str(tmp_path)})
            assert result.returncode == 1
            assert target.exists()
            assert "cleanup-tmpdir failed" in result.stderr
        finally:
            target.chmod(0o755)


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
def test_local_cleanup_flush_orphan_non_flush_and_squash_gap(tmp_path: Path) -> None:
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
    assert "Dropping 1 prior-run larch-log flush commit(s)" in flush_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=flush_repo).stdout.strip() == flush_origin

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
    expected = _git(["rev-parse", "HEAD"], cwd=pusher).stdout.strip()
    squash_result = _run_local_cleanup(squash_repo)
    assert "CLEANUP_SUCCESS=true" in squash_result.stdout
    assert "BRANCH_DELETED=true" in squash_result.stdout
    assert "Dropping 1 prior-run larch-log flush commit(s)" in squash_result.stderr
    assert _git(["rev-parse", "HEAD"], cwd=squash_repo).stdout.strip() == expected
