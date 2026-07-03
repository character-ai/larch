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


def test_fallback_does_not_upgrade_valid_model_rating() -> None:
    record = difficulty.build_record(
        rater="fallback",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "small doc edit"}
        ),
        fallback_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "recovery fallback"}
        ),
    )

    assert record.predicted_tier == difficulty.TRIVIAL
    assert record.applied_tier == difficulty.TRIVIAL
    assert record.override_source == "none"


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


def test_operator_override_beats_floors_and_audit_can_upgrade(tmp_path: Path) -> None:
    record = difficulty.build_record(
        rater="implement",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "small"}
        ),
        changed_paths=("hooks/pre-tool-use.sh",),
        override_tier="TRIVIAL",
    )
    out = tmp_path / "difficulty-rating.json"
    difficulty.write_record(out, record)

    resolved = difficulty.resolve_panel_tier(out, override="TRIVIAL", rng=1)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert resolved.panel_tier == difficulty.HARD
    assert resolved.audit_upgrade is True
    assert data["override_source"] == "operator"
    assert data["audit_upgrade"] == "true"


def test_tier_helpers_and_escalation_round_specific(tmp_path: Path) -> None:
    assert difficulty.tier_ceiling(difficulty.TRIVIAL) == 2
    assert difficulty.tier_ceiling(difficulty.MODERATE) == 2
    assert difficulty.tier_ceiling(difficulty.HARD) == 3
    assert difficulty.panel_shape_for_tier(difficulty.TRIVIAL) == "singles"
    assert difficulty.threshold_panel_for_tier(difficulty.MODERATE) == "hard"
    assert difficulty.maybe_audit_upgrade(difficulty.HARD, 1).evaluated is False

    out = tmp_path / "difficulty-rating.json"
    record = difficulty.build_record(
        rater="implement",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "workflow"}
        ),
    )
    difficulty.write_record(out, record)
    difficulty.append_escalation(out, 2, difficulty.MODERATE, difficulty.HARD, "high-severity")
    data = json.loads(out.read_text(encoding="utf-8"))

    assert data["applied_tier"] == difficulty.HARD
    assert data["escalations"][0]["round"] == 2
    assert difficulty.resolve_panel_tier(out, audit_enabled=False, round_num=2).escalated_round is True
    assert difficulty.resolve_panel_tier(out, audit_enabled=False, round_num=3).escalated_round is False
    assert "MODERATE->HARD" in difficulty.difficulty_line(data)


def test_write_record_merge_preserves_resolution_fields(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    existing = {
        "schema_version": 1,
        "rater": "implement",
        "rater_tool": "bootstrap",
        "rater_model": "unknown",
        "predicted_tier": "TRIVIAL",
        "confidence": "medium",
        "rationale": "old",
        "design_tier": None,
        "implement_tier": None,
        "applied_tier": "HARD",
        "override_source": "operator",
        "floors_applied": [],
        "audit_upgrade": "true",
        "escalations": [{"round": 2, "from_tier": "MODERATE", "to_tier": "HARD", "trigger": "bulk-skip"}],
        "panel_skipped": None,
        "panel_tier": "HARD",
        "round_cap": 3,
        "codex_model_role": "default",
        "audit_evaluated": True,
        "escalated_round": True,
    }
    _ = out.write_text(json.dumps(existing), encoding="utf-8")

    rc = difficulty.write_record_main([
        "--output", str(out),
        "--rater", "implement",
        "--fallback-tier", "MODERATE",
        "--fallback-rationale", "new",
    ])
    data = json.loads(out.read_text(encoding="utf-8"))

    assert rc == 0
    assert data["override_source"] == "operator"
    assert data["audit_upgrade"] == "true"
    assert data["panel_tier"] == "HARD"
    assert data["round_cap"] == 3
    assert data["escalations"] == existing["escalations"]
