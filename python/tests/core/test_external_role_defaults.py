from __future__ import annotations

from pathlib import Path

from larch.core import config
from larch.core import external_defaults
import pytest


def test_all_registry_roles_are_pinned_independently() -> None:
    expected = {
        "implement.step2_coder": ("waterfall", ("codex", "cursor", "claude")),
        "implement.lint_fix_coder": ("waterfall", ("claude", "codex", "cursor")),
        "implement.ci_recovery_fixer": ("waterfall", ("codex", "cursor", "claude")),
        "implement.rebase_conflict_fixer": ("waterfall", ("claude", "codex", "cursor")),
        "review.fix_coder": ("waterfall", ("codex", "cursor", "claude")),
        "review.dynamic_archetype_scout": ("waterfall", ("cursor", "claude")),
        "design.plan_archetype_scout": ("waterfall", ("cursor", "claude")),
        "design.plan_revision": ("waterfall", ("codex", "cursor", "claude")),
        "design.brainstorm_framing": ("waterfall", ("cursor", "codex", "claude")),
        "design.brainstorm_scope": ("waterfall", ("codex", "cursor", "claude")),
    }
    for role_id, (kind, order) in expected.items():
        role = external_defaults.role_default(role_id)
        assert role.kind == kind
        assert external_defaults.tool_order(role_id) == order
    assert "design.brainstorm_pragmatic" not in config.ROLE_DEFAULTS


def test_first_available_drafter_override_and_soft_fail() -> None:
    role = external_defaults.role_default("design.plan_drafter")
    assert role.kind == "first_available"
    assert external_defaults.resolve_vendor("design.plan_drafter", env={}, codex_present=True).vendor == "codex"
    assert external_defaults.resolve_vendor("design.plan_drafter", env={}, codex_present=False).vendor == "claude"
    assert external_defaults.resolve_vendor("design.plan_drafter", env={"LARCH_DESIGN_DRAFTER": "claude"}, codex_present=True).vendor == "claude"
    result = external_defaults.resolve_vendor("design.plan_drafter", env={"LARCH_DESIGN_DRAFTER": "invalid vendor"}, codex_present=True)
    assert result.vendor == ""
    assert result.skip_reason == "invalid-vendor"
    with pytest.raises(external_defaults.ExternalDefaultError, match="kind=waterfall"):
        _ = external_defaults.tool_order("design.plan_drafter")


def test_panel_role_metadata_is_separate() -> None:
    review_slots = external_defaults.slot_defaults("review.panel")
    review_specialists = [slot for slot in review_slots if slot.slot in {"correctness", "edge-cases", "testing"}]
    assert len(review_specialists) == 6
    assert len(review_slots) == 6
    assert {(slot.slot, slot.tool) for slot in review_specialists} == {
        (slot, tool) for slot in ("correctness", "edge-cases", "testing") for tool in ("cursor", "codex")
    }
    deleted_auto_slot: str = "plan-fidelity-auto"
    assert not any(slot.slot == deleted_auto_slot for slot in review_slots)
    assert not any(slot.slot == "generalist" for slot in review_slots)
    assert all(slot.model_role == "review" for slot in review_specialists if slot.tool == "codex")
    assert all(slot.cursor_model == "" for slot in review_specialists if slot.tool == "cursor")
    review_policy = external_defaults.panel_dispatch_policy("review.panel")
    assert review_policy is not None
    assert review_policy.no_fallback_when_both_present_round_lt is None
    assert review_policy.generic_codex_rounds == frozenset()

    plan_slots = external_defaults.slot_defaults("design.plan_review_panel")
    assert {slot.archetype for slot in plan_slots if slot.archetype != "generic"} == {"arch", "innovation", "pragmatic", "requirements"}
    assert all(slot.model_role == "review" for slot in plan_slots if slot.tool == "codex" and slot.archetype != "generic")
    assert all(slot.cursor_model == "" for slot in plan_slots if slot.tool == "cursor")
    plan_policy = external_defaults.panel_dispatch_policy("design.plan_review_panel")
    assert plan_policy is not None
    assert plan_policy.no_fallback_when_both_present_round_lt is None
    assert plan_policy.generic_codex_rounds == frozenset()


def test_voter_and_decompose_roles() -> None:
    decompose = external_defaults.role_default("design.decompose_panel")
    assert decompose.kind == "slot_panel"
    assert decompose.decompose_panel_policy is not None
    assert decompose.decompose_panel_policy.parallel_tools == ("cursor", "codex")
    assert decompose.decompose_panel_policy.panel_no_fallback is True
    assert decompose.decompose_panel_policy.archetypes == ("decomposition-specialist", "dependency-analyst", "scope-minimalist", "risk-isolation")

    plan_voters = external_defaults.voter_policies("design.plan_voters")
    assert [(p.slot_name, p.primary_tool, p.output_name) for p in plan_voters] == [
        ("voter-1", "codex", "codex-validity-vote-output.txt"),
        ("voter-2", "codex", "codex-plan-fidelity-vote-output.txt"),
        ("voter-3", "codex", "codex-pragmatism-vote-output.txt"),
    ]
    # Plan voters share the code-review voter shape: no always-on --no-fallback,
    # and each voter carries Codex, Cursor, then Claude semantic labels.
    assert external_defaults.voter_dispatch_policy("design.plan_voters") is None
    assert dict(plan_voters[0].semantic_labels) == {"codex": "codex-validity", "cursor": "cursor-validity", "claude": "claude"}
    assert dict(plan_voters[1].semantic_labels) == {"codex": "codex-plan-fidelity", "cursor": "cursor-plan-fidelity", "claude": "claude"}
    assert dict(plan_voters[2].semantic_labels) == {"codex": "codex-pragmatism", "cursor": "cursor-pragmatism", "claude": "claude"}
    assert not config.DIFFICULTY_CODEX_MODEL_ROLE_OVERRIDES

    review_voters = external_defaults.voter_policies("review.voters")
    assert review_voters[0].primary_tool == "codex"
    assert review_voters[0].default_label == "codex-validity"
    assert review_voters[0].output_name == "codex-validity-vote-output.txt"
    # Voter 1 waterfalls Codex -> Cursor -> Claude.
    assert review_voters[0].allow_codex_fallback is True
    assert dict(review_voters[0].semantic_labels) == {"codex": "codex-validity", "cursor": "cursor-validity", "claude": "claude"}
    assert review_voters[0].archetype == "validity-correctness"
    assert review_voters[1].default_label == "codex-plan-fidelity"


def test_single_slot_roles_and_docs_rows() -> None:
    review_aggregator = external_defaults.slot_defaults("review.findings_aggregator")[0]
    plan_aggregator = external_defaults.slot_defaults("design.plan_findings_aggregator")[0]
    assert review_aggregator.tool == "codex"
    assert review_aggregator.model_role == "review"
    assert plan_aggregator.tool == "codex"
    assert plan_aggregator.model_role == "review"
    assert external_defaults.slot_defaults("design.decompose_aggregator")[0].tool == "codex"
    rows = external_defaults.doc_rows()
    assert {row.role_id for row in rows} == set(config.ROLE_DEFAULTS)
    docs = (Path(__file__).resolve().parents[3] / "docs/external-reviewers.md").read_text(encoding="utf-8")
    for role_id in ("review.panel", "design.plan_review_panel", "implement.step2_coder", "review.fix_coder", "design.decompose_panel"):
        assert role_id in docs


def test_fixer_alias_is_derived_from_ci_role() -> None:
    assert external_defaults.tool_order("implement.ci_recovery_fixer") == config.FIXER_TIER_ORDER
    assert config.ROLE_DEFAULTS["implement.ci_recovery_fixer"] is not config.ROLE_DEFAULTS["implement.rebase_conflict_fixer"]


def test_next_untried_tier_selects_in_configured_order() -> None:
    result = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        (),
        codex_present=True,
        cursor_present=True,
    )
    assert result == external_defaults.TierSelectResult(
        config.FIXER_TIER_ACTION_SELECTED,
        "codex",
        "",
    )

    fallback = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        ("cursor", "codex", "codex"),
        codex_present=True,
        cursor_present=True,
    )
    assert fallback.selected_tier == "claude"
    assert fallback.action == config.FIXER_TIER_ACTION_SELECTED
    assert fallback.failure_reason == ""


def test_next_untried_tier_treats_failed_or_timed_out_tier_as_attempted() -> None:
    result = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        ("codex",),
        codex_present=True,
        cursor_present=True,
    )
    assert result.selected_tier == "cursor"


def test_next_untried_tier_skips_unavailable_tiers_without_exhausting() -> None:
    result = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        (),
        codex_present=False,
        cursor_present=True,
    )
    assert result.selected_tier == "cursor"

    unavailable = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        (),
        codex_present=False,
        cursor_present=False,
        claude_present=False,
    )
    assert unavailable == external_defaults.TierSelectResult(
        config.FIXER_TIER_ACTION_UNAVAILABLE,
        "",
        config.FIXER_TIER_FAIL_REASON_UNAVAILABLE,
    )


def test_next_untried_tier_gates_claude_at_launch_time() -> None:
    result = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        ("codex", "cursor"),
        codex_present=True,
        cursor_present=True,
        claude_present=False,
    )
    assert result.action == config.FIXER_TIER_ACTION_UNAVAILABLE
    assert result.selected_tier == ""
    assert result.failure_reason == config.FIXER_TIER_FAIL_REASON_UNAVAILABLE


def test_binary_available_prefers_process_then_session_before_path(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = config.ENV_CURSOR_BINARY_FOUND
    _ = (tmp_path / "session-env.sh").write_text(f"{key}=false\n", encoding="utf-8")
    monkeypatch.delenv(key, raising=False)
    def fake_which(_binary: str) -> str:
        return "/bin/cursor"

    monkeypatch.setattr(external_defaults.shutil, "which", fake_which)
    assert external_defaults.binary_available(name=key, implement_tmpdir=tmp_path, binary="cursor") is False

    monkeypatch.setenv(key, "true")
    assert external_defaults.binary_available(name=key, implement_tmpdir=tmp_path, binary="cursor") is True


def test_binary_available_uses_first_valid_session_value(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    key = config.ENV_CURSOR_BINARY_FOUND
    _ = (tmp_path / "session-env.sh").write_text(
        f"{key}=invalid\n{key}=true\n{key}=false\n",
        encoding="utf-8",
    )
    monkeypatch.delenv(key, raising=False)

    def no_binary(_binary: str) -> None:
        return None

    monkeypatch.setattr(external_defaults.shutil, "which", no_binary)

    assert external_defaults.binary_available(name=key, implement_tmpdir=tmp_path, binary="cursor") is True


def test_next_untried_tier_reports_exhaustion_regardless_of_availability() -> None:
    result = external_defaults.next_untried_tier(
        "implement.ci_recovery_fixer",
        ("claude", "codex", "cursor"),
        codex_present=False,
        cursor_present=False,
        claude_present=False,
    )
    assert result == external_defaults.TierSelectResult(
        config.FIXER_TIER_ACTION_EXHAUSTED,
        "",
        config.FIXER_TIER_FAIL_REASON_EXHAUSTED,
    )


def test_next_untried_tier_rejects_invalid_inputs_and_role_kinds() -> None:
    with pytest.raises(external_defaults.ExternalDefaultError, match="invalid attempted tier"):
        _ = external_defaults.next_untried_tier(
            "implement.ci_recovery_fixer",
            ("unknown",),
        )
    with pytest.raises(external_defaults.ExternalDefaultError, match="kind=waterfall"):
        _ = external_defaults.next_untried_tier("review.panel", ())
    with pytest.raises(external_defaults.ExternalDefaultError, match="unknown role"):
        _ = external_defaults.next_untried_tier("missing.role", ())


def test_fixer_lane_budget_reserves_a_full_timeout_per_configured_tier() -> None:
    for role_id in (
        "implement.lint_fix_coder",
        "implement.ci_recovery_fixer",
        "implement.rebase_conflict_fixer",
        "review.fix_coder",
        "design.plan_revision",
    ):
        assert external_defaults.fixer_lane_budget_sec(role_id) == (
            len(external_defaults.tool_order(role_id))
            * config.FIXER_LANE_TIMEOUT_SEC
        )


def test_debate_panel_and_synthesizer_roles() -> None:
    panel = external_defaults.role_default("debate.panel")
    assert panel.kind == "slot_panel"
    slots = external_defaults.slot_defaults("debate.panel")
    assert [(slot.slot, slot.tool, slot.model, slot.transport) for slot in slots] == [
        ("cursor", "cursor", config.DEBATE_CURSOR_MODEL, "subprocess"),
        ("codex", "codex", config.DEBATE_CODEX_MODEL, "subprocess"),
        ("claude", "claude", config.DEBATE_CLAUDE_MODEL, "agent-tool"),
    ]
    assert sum(1 for slot in slots if slot.transport == "agent-tool") == 1
    assert all(slot.transport == "subprocess" for slot in slots if slot.tool != "claude")
    for field in (panel.doc_phase, panel.doc_role, panel.doc_skills, panel.doc_fallback):
        assert field

    synth = external_defaults.role_default("debate.synthesizer")
    assert synth.kind == "waterfall"
    assert external_defaults.tool_order("debate.synthesizer") == ("codex", "cursor", "claude")
    for field in (synth.doc_phase, synth.doc_role, synth.doc_skills, synth.doc_fallback):
        assert field

    rows = external_defaults.doc_rows()
    assert {row.role_id for row in rows} == set(config.ROLE_DEFAULTS)
    docs = (Path(__file__).resolve().parents[3] / "docs/external-reviewers.md").read_text(encoding="utf-8")
    assert "debate.panel" in docs
    assert "debate.synthesizer" in docs
