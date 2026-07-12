"""Focused normalization coverage for reconciled manual merges."""

# pyright: reportUnusedCallResult=false

from __future__ import annotations

import argparse
from pathlib import Path

import pytest

from larch.state import stall_recovery


@pytest.mark.parametrize(
    ("merge_result", "expected"),
    [
        ("merged", "merged"),
        ("admin_merged", "merged"),
        ("already_merged", "force-merged-externally"),
    ],
)
def test_proven_merge_overrides_forked_target(
    tmp_path: Path,
    merge_result: str,
    expected: str,
) -> None:
    (tmp_path / "ship-pr-state.sh").write_text(
        f"PHASE=done\nMERGE_RESULT={merge_result}\nFORKED_TARGET=true\nSTALL_TRACKING=false\nEXIT_CODE=0\n",
        encoding="utf-8",
    )

    values = stall_recovery.normalized_outcome_values(
        argparse.Namespace(
            implement_tmpdir=str(tmp_path), in_memory_stall_tracking="false"
        ),
    )

    assert values["IMPLEMENT_NORMALIZED_OUTCOME"] == expected
    assert values["IMPLEMENT_FORKED_TARGET"] == "true"


def test_merge_with_bail_overlay_stays_bailed_until_cleared(tmp_path: Path) -> None:
    state = tmp_path / "ship-pr-state.sh"
    state.write_text(
        "PHASE=done\nMERGE_RESULT=merged\nSTALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=true\nEXIT_CODE=0\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        implement_tmpdir=str(tmp_path), in_memory_stall_tracking="false"
    )

    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "bailed-needs-user-input"
    )
    state.write_text(
        "PHASE=done\nMERGE_RESULT=merged\nSTALL_TRACKING=false\nBAIL_NEEDS_USER_INPUT=false\nEXIT_CODE=0\n",
        encoding="utf-8",
    )
    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "merged"
    )


def test_merge_stays_stalled_until_disk_and_explicit_memory_stall_are_cleared(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=done\nMERGE_RESULT=merged\nSTALL_TRACKING=true\nEXIT_CODE=4\n",
        encoding="utf-8",
    )
    args = argparse.Namespace(
        implement_tmpdir=str(tmp_path), in_memory_stall_tracking="true"
    )

    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "stalled"
    )

    (tmp_path / "ship-pr-state.sh").write_text(
        "PHASE=done\nMERGE_RESULT=merged\nSTALL_TRACKING=false\nEXIT_CODE=0\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("STALL_TRACKING", "true")
    args.in_memory_stall_tracking = ""
    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "merged"
    )
    args.in_memory_stall_tracking = "true"
    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "stalled"
    )
    args.in_memory_stall_tracking = "false"
    assert (
        stall_recovery.normalized_outcome_values(args)["IMPLEMENT_NORMALIZED_OUTCOME"]
        == "merged"
    )
