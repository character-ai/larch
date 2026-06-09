from __future__ import annotations
# pyright: reportUnusedCallResult=false

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import TYPE_CHECKING

import finalize
import session_env

if TYPE_CHECKING:
    import pytest

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
