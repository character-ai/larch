"""Tests for run_context.py."""

from __future__ import annotations

import pytest
from pathlib import Path

from larch.core import run_context


def _ctx() -> run_context.RunContext:
    return run_context.RunContext(
        branch="feature/x",
        issue="42",
        repo="owner/repo",
        run_id="run-1",
        tmpdir="/tmp/x",
        merge=True,
        draft=False,
        forked=False,
        manifest_path="/tmp/x/manifest.json",
        tool_label="cursor",
        no_admin_fallback=False,
        repo_unavailable=False,
    )


def test_with_returns_new_instance() -> None:
    original = _ctx()
    updated = original.with_(branch="feature/y")
    assert updated.branch == "feature/y"
    assert original.branch == "feature/x"


def test_with_rejects_unknown_fields() -> None:
    with pytest.raises(TypeError, match="unknown"):
        _ = _ctx().with_(not_a_field=True)


def test_from_env_defaults_merge_disabled() -> None:
    ctx = run_context.RunContext.from_env(env={})
    assert ctx.merge is False


def test_alias_properties_track_canonical_fields() -> None:
    ctx = _ctx().with_(branch="feature/z", forked=True)
    assert ctx.branch_name == "feature/z"
    assert ctx.forked_target is True


def test_with_translates_legacy_aliases() -> None:
    ctx = _ctx().with_(branch_name="feature/alias", forked_target=True)
    assert ctx.branch == "feature/alias"
    assert ctx.branch_name == "feature/alias"
    assert ctx.forked is True
    assert ctx.forked_target is True


def test_from_env_hydrates_ci_fix_rebase_pending_from_state(tmp_path: Path) -> None:
    state = tmp_path / "state.env"
    _ = state.write_text("CI_FIX_REBASE_PENDING=true\n", encoding="utf-8")
    ctx = run_context.RunContext.from_env(env={"SHIP_PR_STATE_FILE": str(state)})
    assert ctx.ci_fix_rebase_pending is True
