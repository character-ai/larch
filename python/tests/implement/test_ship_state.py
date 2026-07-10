"""Tests for ship state write and patch helpers."""

from __future__ import annotations

from pathlib import Path

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


def test_write_ship_state_preserves_emergency_repair_fields(tmp_path: Path) -> None:
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


def test_write_ship_state_clears_terminal_and_stall_fields_when_non_stalled(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text(
        "PHASE=stalled\nSTALL_TRACKING=true\nSTALL_STEP=pr-create-guideline-outcome-refresh\n"
        "EXIT_CODE=4\nBAIL_REASON=stalled\nBAIL_NEEDS_USER_INPUT=false\n"
        "FAILED_RUN_ID=run-old\nBAIL_FAILURE_DETAIL_LOG=detail.log\n",
        encoding="utf-8",
    )

    ship_state._write_ship_state(  # pyright: ignore[reportPrivateUsage]
        _ctx(tmpdir=str(tmp_path), state_file=str(state_file)).with_(stall_tracking=False, stall_step=""),
        phase="assessments",
    )

    state = state_file.read_text(encoding="utf-8")
    assert "PHASE=assessments\n" in state
    assert "STALL_TRACKING=false\n" in state
    assert "STALL_STEP=\n" in state
    assert "EXIT_CODE=" not in state
    assert "BAIL_REASON=" not in state
    assert "BAIL_NEEDS_USER_INPUT=" not in state
    assert "FAILED_RUN_ID=" not in state
    assert "BAIL_FAILURE_DETAIL_LOG=" not in state


def test_patch_ship_state_rejects_unknown_key(tmp_path: Path) -> None:
    state_file = tmp_path / "ship-pr-state.sh"
    _ = state_file.write_text("PHASE=emergency-repair\nBRANCH_NAME=feat\n", encoding="utf-8")

    with pytest.raises(ship_state.ShipError, match="invalid ship state patch field"):
        ship_state._patch_ship_state_keys(  # pyright: ignore[reportPrivateUsage]
            state_file=state_file,
            patch={"UNKNOWN": "1"},
        )


def test_progress_note_uses_run_aware_breadcrumb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """ship_state._progress_note writes breadcrumbs via append_breadcrumb_for_run."""
    from larch.implement import ship_state as ss
    from larch.report import progress_file

    monkeypatch.setenv("LARCH_RUN_ID", "ship-run-88")
    breadcrumb_calls: list[tuple[str, str, str, str]] = []

    def fake_append(repo: object, run_id: str, skill: str, step: str, text: str) -> bool:
        breadcrumb_calls.append((run_id, skill, step, text))
        return True

    monkeypatch.setattr(ss.progress_file, "append_breadcrumb_for_run", fake_append)  # type: ignore[attr-defined]
    monkeypatch.chdir(tmp_path)

    ss._progress_note(step="9", text="test note")  # pyright: ignore[reportPrivateUsage]

    assert len(breadcrumb_calls) == 1
    assert breadcrumb_calls[0][0] == "ship-run-88"
    assert breadcrumb_calls[0][3] == "test note"
