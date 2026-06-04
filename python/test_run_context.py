"""Tests for run_context.py."""

from __future__ import annotations

import pytest

import run_context


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
