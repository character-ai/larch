"""Tests for outcomes.py."""

from __future__ import annotations

import pytest

from larch import outcomes


def test_outcome_membership() -> None:
    assert outcomes.Outcome.OK.value == "OK"
    assert outcomes.Outcome.TRANSIENT in outcomes.Outcome


def test_step_result_immutable_and_equal() -> None:
    left = outcomes.StepResult(outcomes.Outcome.OK, detail="done")
    right = outcomes.StepResult(outcomes.Outcome.OK, detail="done")
    assert left == right
    with pytest.raises(AttributeError):
        left.detail = "mutate"  # type: ignore[misc]
