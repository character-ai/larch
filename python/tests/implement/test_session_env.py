from __future__ import annotations
# pyright: reportUnusedCallResult=false, reportUnknownVariableType=false
import json
from dataclasses import FrozenInstanceError
from pathlib import Path
import pytest

from larch.core import config
from larch.state import finalize
from larch.state import session_env

from test_support import make_design_tmpdir, seed_run_params, write_design_source_env

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
