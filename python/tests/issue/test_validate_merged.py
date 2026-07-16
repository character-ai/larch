# pyright: reportUnusedCallResult=false
"""Focused contracts for the independent merge-validation state."""

from __future__ import annotations

import inspect
import json
from pathlib import Path

import pytest

from larch.issue import validate_merged
from larch.issue import learn_from_bugs


def _state() -> validate_merged.ValidateMergedState:
    return validate_merged.ValidateMergedState(
        schema_version=validate_merged.STATE_SCHEMA_VERSION,
        repo="o/r",
        last_successful_tip="a" * 40,
        completed_at="2026-07-16T12:00:00Z",
        merge_watermark="a" * 40,
        pending_merge_shas=("b" * 40,),
        unresolved_candidates=(
            {
                "merge_sha": "a" * 40,
                "file": "python/larch/example.py",
                "symbol": "example",
                "description": "bad default",
                "severity": "medium",
                "confidence": "high",
            },
        ),
    )


def test_state_round_trip_is_independent_and_compact(tmp_path: Path) -> None:
    path = tmp_path / "larch-logs/shared/validate-merged-state.json"
    validate_merged.write_state(path, _state())
    assert validate_merged.load_state(path, repo="o/r") == _state()
    assert "diff" not in path.read_text(encoding="utf-8")


def test_state_rejects_foreign_repo_and_duplicate_pending(tmp_path: Path) -> None:
    path = tmp_path / "state.json"
    validate_merged.write_state(path, _state())
    with pytest.raises(validate_merged.ValidateMergedError, match="foreign repository"):
        validate_merged.load_state(path, repo="other/repo")
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["pending_merge_shas"] *= 2
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(validate_merged.ValidateMergedError, match="duplicate"):
        validate_merged.load_state(path, repo="o/r")


def test_public_cli_uses_max_merges_not_issue_window() -> None:
    parser = validate_merged.prepare_main
    assert callable(parser)
    assert validate_merged.DEFAULT_MAX_MERGES == 20


def test_learn_from_bugs_publication_has_no_worktree_command() -> None:
    source = inspect.getsource(learn_from_bugs.run_state_publish)
    assert "worktree" not in source
