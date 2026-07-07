"""Tests for ship state write and patch helpers."""

from __future__ import annotations

import pytest

from larch.implement import ship_state
from test_support import make_run_context


def _ctx(*, tmpdir: str, state_file: str):
    return make_run_context(
        tmpdir=tmpdir,
        state_file=state_file,
        branch="feat",
        repo="o/r",
        issue="1",
        run_id="run-1",
        merge=True,
        draft=False,
        forked=False,
        manifest_path=f"{tmpdir}/manifest.txt",
        tool_label="codex",
        no_admin_fallback=False,
        repo_unavailable=False,
    ).with_(pr_number=7, pr_url="https://example.test/pr/7")


def test_write_ship_state_preserves_emergency_repair_fields(tmp_path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    ship_state._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmpdir=str(tmp_path), state_file=str(state_file)),
        phase="emergency-repair",
        extra_fields={
            "ORIGINAL_BRANCH_FORBIDDEN": "true",
            "MAIN_REPAIR_RUN_ID": "44",
            "MAIN_REPAIR_HEAD": "abc123",
            "EMERGENCY_REPAIR_BRANCH": "repair/feat",
            "EMERGENCY_REPAIR_PR_NUMBER": "8",
            "MAIN_HEALTH_HEAD_SHA": "abc123",
        },
    )

    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=emergency-repair\n" in state
    assert "ORIGINAL_BRANCH_FORBIDDEN=true\n" in state
    assert "MAIN_REPAIR_RUN_ID=44\n" in state
    assert "MAIN_REPAIR_HEAD=abc123\n" in state
    assert "EMERGENCY_REPAIR_BRANCH=repair/feat\n" in state
    assert "EMERGENCY_REPAIR_PR_NUMBER=8\n" in state
    assert "MAIN_HEALTH_HEAD_SHA=abc123\n" in state


def test_patch_ship_state_rejects_unknown_key(tmp_path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=emergency-repair\nBRANCH_NAME=feat\n", encoding="utf-8")

    with pytest.raises(ship_state.ShipError, match="invalid ship state patch field"):
        ship_state._patch_ship_state_keys(  # pyright: ignore[reportPrivateUsage]
            state_file=state_file,
            patch={"UNKNOWN": "1"},
        )
