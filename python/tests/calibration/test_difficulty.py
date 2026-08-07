# pyright: reportUnknownLambdaType=false, reportUnknownArgumentType=false
from __future__ import annotations

import json
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path

import pytest

from larch.calibration import difficulty
from larch.core.proc import CommandResult
from larch.design import plan_grammar
from larch.errors import ShipError
from larch.issue import issue_mutation


def test_validate_rating_low_confidence_bumps_and_sanitizes() -> None:
    rating = difficulty.validate_rating_object(
        {"predicted_tier": "trivial", "confidence": "low", "rationale": "line\nwith\tcontrols"}
    )

    assert rating.predicted_tier == difficulty.TRIVIAL
    assert rating.adjusted_tier == difficulty.MODERATE
    assert rating.rationale == "line with controls"


def test_public_difficulty_results_are_frozen() -> None:
    result = difficulty.FloorResult(tier=difficulty.TRIVIAL, matches=())

    assert is_dataclass(result)
    with pytest.raises(FrozenInstanceError):
        result.tier = difficulty.HARD  # type: ignore[misc]


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


def test_plan_difficulty_prefers_trailing_tier_over_embedded_tier() -> None:
    text = "body\ndifficulty: TRIVIAL\n\nreview_status: complete\ndifficulty: HARD\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == "HARD"


def test_plan_difficulty_falls_back_to_embedded_tier_when_trailer_has_none() -> None:
    text = "## Plan\nbody\ndifficulty: MODERATE\n\n## Acceptance\nok\n\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == "MODERATE"


def test_plan_difficulty_uses_last_embedded_tier_without_trailing_tier() -> None:
    text = "difficulty: TRIVIAL\nbody\ndifficulty: HARD\n\n## Acceptance\nok\n\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == "HARD"


def test_plan_difficulty_rejects_invalid_adjacent_trailing_tier() -> None:
    text = "difficulty: MODERATE\nbody\n\ndifficulty: EASY\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == ""


def test_plan_difficulty_rejects_invalid_adjacent_trailing_tier_with_legacy_confidence() -> None:
    text = "difficulty: MODERATE\nbody\n\ndifficulty: EASY\nconfidence: high\ndiff_lines: 9\n"

    assert difficulty.plan_difficulty(text) == ""


def test_plan_difficulty_rejects_invalid_stranded_tier_without_recognized_trailer() -> None:
    text = "difficulty: HARD\nbody\n\ndifficulty: EASY\nconfidence: high\n"

    assert difficulty.plan_difficulty(text) == ""


def test_plan_difficulty_accepts_valid_stranded_tier_without_recognized_trailer() -> None:
    text = "difficulty: HARD\nbody\n\ndifficulty: MODERATE\nconfidence: high\n"

    assert difficulty.plan_difficulty(text) == "MODERATE"


def test_trailing_plan_difficulty_is_strict_trailing_only() -> None:
    text = "difficulty: MODERATE\nbody\n\nreview_status: complete\ndiff_lines: 9\n"

    assert difficulty.trailing_plan_difficulty(text) == ""


def test_trailing_plan_metadata_lines_remains_contiguous_final_trailer_only() -> None:
    text = "body\ndiff_added: 8\nnot trailer\ndifficulty: MODERATE\ndiff_lines: 9\n"

    assert difficulty.trailing_plan_metadata_lines(text) == ("difficulty: MODERATE", "diff_lines: 9")


def test_trailing_plan_metadata_lines_accepts_oversize_override() -> None:
    text = "body\nreview_status: complete\nrounds_completed: 2\ndifficulty: MODERATE\noversize_override: operator\ndiff_lines: 9\n"

    assert difficulty.trailing_plan_metadata_lines(text) == (
        "review_status: complete",
        "rounds_completed: 2",
        "difficulty: MODERATE",
        "oversize_override: operator",
        "diff_lines: 9",
    )


def test_registry_driven_final_trailers_through_difficulty_lookup_and_rewrite() -> None:
    values = {
        "review_status": "complete",
        "rounds_completed": 2,
        "difficulty": "MODERATE",
        "diff_added": 3,
        "diff_deleted": 1,
        "mechanical_churn": False,
        "oversize_override": "operator",
        "diff_lines": 11,
    }
    lines = plan_grammar.compose_trailer_lines(values)  # type: ignore[arg-type]
    assert tuple(match.key for match in map(plan_grammar.match_trailer_line, lines) if match) == plan_grammar.TRAILER_KEYS
    text = "body\n" + "\n".join(lines) + "\n"
    trailers = plan_grammar.parse_final_trailers(text, require_diff_lines=True)
    assert trailers.lines == lines
    assert difficulty.plan_difficulty(text) == "MODERATE"
    assert difficulty.trailing_plan_metadata_lines(text) == lines
    rewritten = difficulty.rewrite_plan_difficulty(text, "HARD")
    assert difficulty.plan_difficulty(rewritten) == "HARD"
    assert "difficulty: HARD" in rewritten
    assert rewritten.rstrip().endswith("diff_lines: 11")


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


def test_resolve_panel_tier_recomputes_on_new_override_after_persisted_override(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    record = difficulty.build_record(
        rater="implement",
        implement_rating=difficulty.validate_rating_object(
            {"predicted_tier": "TRIVIAL", "confidence": "high", "rationale": "bootstrap"}
        ),
        override_tier="TRIVIAL",
    )
    difficulty.write_record(out, record)

    resolved = difficulty.resolve_panel_tier(out, override="HARD", rng=1)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert resolved.panel_tier == difficulty.HARD
    assert resolved.codex_model_role == difficulty.codex_review_model_role(difficulty.HARD)
    assert data["panel_tier"] == difficulty.HARD
    assert data["codex_model_role"] == difficulty.codex_review_model_role(difficulty.HARD)


def test_tier_helpers_and_escalation_round_specific(tmp_path: Path) -> None:
    assert difficulty.tier_ceiling(difficulty.TRIVIAL) == 2
    assert difficulty.tier_ceiling(difficulty.MODERATE) == 2
    assert difficulty.tier_ceiling(difficulty.HARD) == 2
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
    assert data["round_cap"] == 2
    assert data["escalations"][0]["round"] == 2
    assert difficulty.resolve_panel_tier(out, audit_enabled=False, round_num=2).escalated_round is True
    assert difficulty.resolve_panel_tier(out, audit_enabled=False, round_num=3).escalated_round is False
    assert "MODERATE->HARD" in difficulty.difficulty_line(data)


def test_codex_review_model_role_for_archetype_always_review() -> None:
    assert difficulty.codex_review_model_role_for_archetype("design.plan_review_panel", "pragmatic", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("design.plan_review_panel", "requirements", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("design.plan_review_panel", "arch", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("design.plan_review_panel", "innovation", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("review.panel", "correctness", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("review.panel", "edge-cases", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("review.panel", "testing", difficulty.HARD) == "review"
    assert difficulty.codex_review_model_role_for_archetype("review.panel", "correctness", difficulty.MODERATE) == "review"
    assert difficulty.codex_review_model_role_for_archetype("review.panel", "correctness", difficulty.TRIVIAL) == "review"
    assert difficulty.codex_review_model_role(difficulty.HARD) == "review"


def test_write_record_merge_preserves_resolution_fields(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
    assert data["round_cap"] == 2
    assert data["escalations"] == existing["escalations"]

    monkeypatch.setattr(
        difficulty.proc,
        "run",
        lambda *_args, **_kwargs: CommandResult(
            ("git",), 0, "hooks/pre-tool-use.sh\n", "", 0.01
        ),
    )
    assert difficulty.write_record_main([
        "--output", str(out),
        "--refresh-existing",
        "--refresh-repo-root", str(tmp_path),
    ]) == 0
    refreshed = json.loads(out.read_text(encoding="utf-8"))
    assert refreshed["floors_applied"][0]["path"] == "hooks/pre-tool-use.sh"
    assert refreshed["floors_applied"][0]["floor"] == "MODERATE"
    assert refreshed["panel_tier"] == "HARD"
    assert refreshed["round_cap"] == 2
    assert refreshed["escalations"] == existing["escalations"]


def test_refresh_existing_record_preserves_bytes_when_git_diff_fails(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    out = tmp_path / "difficulty-rating.json"
    record = difficulty.build_record(
        rater="implement",
        implement_rating=difficulty.validate_rating_object({
            "predicted_tier": "MODERATE",
            "confidence": "medium",
            "rationale": "existing scope",
        }),
        changed_paths=("old.py",),
    )
    difficulty.write_record(out, record)
    before = out.read_bytes()
    monkeypatch.setattr(
        difficulty.proc,
        "run",
        lambda *_args, **_kwargs: CommandResult(("git",), 1, "", "failed", 0.01),
    )

    rc = difficulty.write_record_main([
        "--output", str(out),
        "--refresh-existing",
        "--refresh-repo-root", str(tmp_path),
    ])

    assert rc == 1
    assert out.read_bytes() == before


def test_resolve_panel_tier_clamps_stale_hard_round_cap(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    existing = {
        "schema_version": 1,
        "rater": "implement",
        "rater_tool": "bootstrap",
        "rater_model": "unknown",
        "predicted_tier": "HARD",
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

    resolution = difficulty.resolve_panel_tier(out, audit_enabled=False)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert resolution.round_cap == 2
    assert data["round_cap"] == 3


def test_write_record_merge_recomputes_unresolved_bootstrap_tiers(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    existing = difficulty.build_record(
        rater="implement",
        rater_tool="bootstrap",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "bootstrap"}
        ),
    )
    difficulty.write_record(out, existing)

    rc = difficulty.write_record_main([
        "--output",
        str(out),
        "--rater",
        "fallback",
        "--fallback-tier",
        "HARD",
        "--fallback-rationale",
        "new",
    ])
    data = json.loads(out.read_text(encoding="utf-8"))

    assert rc == 0
    assert data["applied_tier"] == difficulty.HARD
    assert data["panel_tier"] == difficulty.HARD
    assert data["override_source"] == "none"


def test_resolve_panel_tier_audits_existing_unresolved_record(tmp_path: Path) -> None:
    out = tmp_path / "difficulty-rating.json"
    existing = difficulty.build_record(
        rater="design",
        rater_tool="claude",
        rater_model="unknown",
        design_rating=difficulty.validate_rating_object(
            {"predicted_tier": "MODERATE", "confidence": "medium", "rationale": "bootstrap"}
        ),
    )
    difficulty.write_record(out, existing)

    resolved = difficulty.resolve_panel_tier(out, rng=1)
    data = json.loads(out.read_text(encoding="utf-8"))

    assert resolved.audit_evaluated is True
    assert resolved.panel_tier == difficulty.HARD
    assert data["audit_evaluated"] is True
    assert data["panel_tier"] == difficulty.HARD


def test_resolve_step2_effective_difficulty_override_precedes_prior(tmp_path: Path) -> None:
    _ = (tmp_path / "run-flags.sh").write_text("DIFFICULTY_OVERRIDE= moderate \n", encoding="utf-8")
    _ = (tmp_path / "difficulty-prior.env").write_text("DESIGN_DIFFICULTY=HARD\n", encoding="utf-8")

    assert difficulty.resolve_step2_effective_difficulty(tmp_path) == difficulty.MODERATE


def test_resolve_step2_effective_difficulty_invalid_inputs_fail_closed(tmp_path: Path) -> None:
    _ = (tmp_path / "run-flags.sh").write_text("DIFFICULTY_OVERRIDE=unknown\n", encoding="utf-8")
    _ = (tmp_path / "difficulty-prior.env").write_text("DESIGN_DIFFICULTY=also-unknown\n", encoding="utf-8")

    assert difficulty.resolve_step2_effective_difficulty(tmp_path) == ""


def test_sync_labels_uses_freshness_checked_label_mutation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    label_updates: list[frozenset[str]] = []

    def fake_snapshot(_runner: object, *, repository: str, issue: str, **_kwargs: object) -> issue_mutation.IssueSnapshot:
        return issue_mutation.IssueSnapshot(
            repository=repository,
            issue=issue,
            title="title",
            body="",
            labels=frozenset({"difficulty:trivial", "keep"}),
            state="OPEN",
            updated_at="2026-07-19T18:00:00Z",
        )

    def fake_update(_runner: object, *, labels: frozenset[str], **_kwargs: object) -> None:
        label_updates.append(labels)

    def fake_proc_run(argv: list[str] | tuple[str, ...], **_kwargs: object) -> CommandResult:
        return CommandResult(tuple(argv), 0, "", "", 0.01)

    monkeypatch.setattr(difficulty.issue_mutation, "read_snapshot", fake_snapshot)
    monkeypatch.setattr(difficulty.issue_mutation, "update_labels", fake_update)
    monkeypatch.setattr(difficulty.proc, "run", fake_proc_run)

    rc = difficulty.sync_labels_main(["--issue", "9", "--tier", "HARD", "--repo", "o/r"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "STATUS=ok" in out
    assert "LABEL=difficulty:hard" in out
    assert label_updates == [frozenset({"difficulty:hard", "keep"})]


def test_sync_labels_add_failure_returns_error(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    def fake_snapshot(_runner: object, *, repository: str, issue: str, **_kwargs: object) -> issue_mutation.IssueSnapshot:
        return issue_mutation.IssueSnapshot(
            repository=repository,
            issue=issue,
            title="title",
            body="",
            labels=frozenset(),
            state="OPEN",
            updated_at="2026-07-19T18:00:00Z",
        )

    def fake_update(*_args: object, **_kwargs: object) -> None:
        raise ShipError("label add failed")

    monkeypatch.setattr(difficulty.gh, "resolve_repo", lambda _runner: "o/r")
    monkeypatch.setattr(difficulty.issue_mutation, "read_snapshot", fake_snapshot)
    monkeypatch.setattr(difficulty.issue_mutation, "update_labels", fake_update)
    monkeypatch.setattr(
        difficulty.proc,
        "run",
        lambda argv, **_k: CommandResult(tuple(argv), 0, "", "", 0.01),
    )

    rc = difficulty.sync_labels_main(["--issue", "9", "--tier", "MODERATE"])
    assert rc == 1
    out = capsys.readouterr().out
    assert "STATUS=error" in out
    assert "ERROR=label-add-failed" in out
