"""Tests for errors.py hierarchy."""

from __future__ import annotations

import errors


def test_subclass_relationships() -> None:
    assert issubclass(errors.TransientNetworkError, errors.ShipError)
    assert issubclass(errors.NeedsUserInput, errors.ShipError)
    assert issubclass(errors.Stalled, errors.ShipError)
    assert issubclass(errors.PrePushConflictHandoff, errors.Stalled)
    assert issubclass(errors.PrePushConflictHandoff, errors.ShipError)


def test_messages_preserved() -> None:
    err = errors.TransientNetworkError("network blip")
    assert str(err) == "network blip"


def test_pre_push_conflict_handoff_fields_and_csv() -> None:
    err = errors.PrePushConflictHandoff(
        conflict_files=("vendor/a.txt", "src/b.txt"),
        resume_phase="ship-pr-rrr-phase14",
        caller_kind="ship_pr_pre_push",
    )
    assert err.conflict_files == ("vendor/a.txt", "src/b.txt")
    assert err.resume_phase == "ship-pr-rrr-phase14"
    assert err.caller_kind == "ship_pr_pre_push"
    assert err.conflict_csv == "vendor/a.txt,src/b.txt"
