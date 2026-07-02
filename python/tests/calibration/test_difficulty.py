from __future__ import annotations

import json
from pathlib import Path

import pytest

from larch.calibration import difficulty


def test_validate_rating_low_confidence_bumps_and_sanitizes() -> None:
    rating = difficulty.validate_rating_object(
        {"predicted_tier": "trivial", "confidence": "low", "rationale": "line\nwith\tcontrols"}
    )

    assert rating.predicted_tier == difficulty.TRIVIAL
    assert rating.adjusted_tier == difficulty.MODERATE
    assert rating.rationale == "line with controls"


@pytest.mark.parametrize("tier", ["", "EASY", "harder"])
def test_validate_rating_rejects_invalid_tiers(tier: str) -> None:
    with pytest.raises(ValueError, match="predicted_tier"):
        _ = difficulty.validate_rating_object({"predicted_tier": tier, "confidence": "medium", "rationale": "x"})


def test_floors_raise_only() -> None:
    floors = (difficulty.DifficultyFloor(glob="hooks/**", floor=difficulty.MODERATE, reason="hook"),)
    result = difficulty.match_floors(("hooks/pre-tool-use.sh",), floors=floors)
    record = difficulty.build_record(
        rater="implement",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "small hook edit"}
        ),
        changed_paths=("hooks/pre-tool-use.sh",),
    )

    assert result.tier == difficulty.MODERATE
    assert record.predicted_tier == difficulty.TRIVIAL
    assert record.applied_tier == difficulty.MODERATE
    assert record.override_source == "floor"


def test_write_record_json_shape(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    record = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="sonnet",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "plan changes workflow"}
        ),
    )

    difficulty.write_record(out, record)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data["schema_version"] == 1
    assert data["design_tier"] == "MODERATE"
    assert data["applied_tier"] == "MODERATE"
    assert data["override_source"] == "none"


def test_plan_difficulty_and_label() -> None:
    text = "body\nreview_status: complete\nrounds_completed: 2\ndifficulty: HARD\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == "HARD"
    assert difficulty.label_for_tier("HARD") == "difficulty:hard"
