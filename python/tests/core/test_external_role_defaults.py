from __future__ import annotations

from pathlib import Path

from larch.core import config
from larch.core import external_defaults
import pytest


def test_all_registry_roles_are_pinned_independently() -> None:
    expected = {
        "implement.step2_coder": ("waterfall", ("codex", "cursor", "claude")),
        "implement.lint_fix_coder": ("waterfall", ("claude", "codex", "cursor")),
        "implement.ci_recovery_fixer": ("waterfall", ("claude", "codex", "cursor")),
        "implement.rebase_conflict_fixer": ("waterfall", ("claude", "codex", "cursor")),
        "review.fix_coder": ("waterfall", ("cursor", "codex")),
        "review.dynamic_archetype_scout": ("waterfall", ("cursor", "claude")),
        "design.plan_archetype_scout": ("waterfall", ("cursor", "claude")),
        "design.plan_revision": ("waterfall", ("cursor", "codex", "claude")),
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
    assert {(slot.slot, slot.tool) for slot in review_specialists} == {
        (slot, tool) for slot in ("correctness", "edge-cases", "testing") for tool in ("cursor", "codex")
    }
    generic = next(slot for slot in review_slots if slot.slot == "generalist")
    assert generic.model_role == "default"
    assert generic.agent == "agents/code-reviewer.md"
    assert generic.focus_area == "code-quality"
    assert generic.weight == 1
    assert all(slot.model_role == "default" for slot in review_specialists if slot.tool == "codex")
    review_policy = external_defaults.panel_dispatch_policy("review.panel")
    assert review_policy is not None
    assert review_policy.no_fallback_when_both_present_round_lt is None
    assert review_policy.generic_codex_rounds == frozenset()

    plan_slots = external_defaults.slot_defaults("design.plan_review_panel")
    assert {slot.archetype for slot in plan_slots if slot.archetype != "generic"} == {"arch", "innovation", "pragmatic", "requirements"}
    assert all(slot.model_role == "default" for slot in plan_slots if slot.tool == "codex" and slot.archetype != "generic")
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
        ("voter-1", "claude", "claude-vote-output.txt"),
        ("voter-2", "codex", "codex-vote-output.txt"),
        ("voter-3", "cursor", "cursor-vote-output.txt"),
    ]
    # Plan voters waterfall fully now (issue #5817): no always-on --no-fallback,
    # and each external voter carries its cross-vendor middle tier.
    assert external_defaults.voter_dispatch_policy("design.plan_voters") is None
    assert dict(plan_voters[1].semantic_labels) == {"codex": "codex", "cursor": "cursor", "claude": "claude"}
    assert dict(plan_voters[2].semantic_labels) == {"cursor": "cursor", "codex": "codex", "claude": "claude"}

    review_voters = external_defaults.voter_policies("review.voters")
    # Voter 1 waterfalls Cursor -> Codex -> Claude (issue #5817).
    assert review_voters[0].allow_codex_fallback is True
    assert dict(review_voters[0].semantic_labels) == {"cursor": "cursor-validity", "codex": "codex-validity", "claude": "claude"}
    assert review_voters[0].archetype == "validity-correctness"
    assert review_voters[1].default_label == "codex-plan-fidelity"


def test_single_slot_roles_and_docs_rows() -> None:
    assert external_defaults.slot_defaults("review.findings_aggregator")[0].tool == "cursor"
    assert external_defaults.slot_defaults("design.plan_findings_aggregator")[0].tool == "cursor"
    assert external_defaults.slot_defaults("design.decompose_aggregator")[0].tool == "codex"
    rows = external_defaults.doc_rows()
    assert {row.role_id for row in rows} == set(config.ROLE_DEFAULTS)
    docs = (Path(__file__).resolve().parents[3] / "docs/external-reviewers.md").read_text(encoding="utf-8")
    for role_id in ("review.panel", "design.plan_review_panel", "implement.step2_coder", "review.fix_coder", "design.decompose_panel"):
        assert role_id in docs


def test_fixer_alias_is_derived_from_ci_role() -> None:
    assert external_defaults.tool_order("implement.ci_recovery_fixer") == config.FIXER_TIER_ORDER
    assert config.ROLE_DEFAULTS["implement.ci_recovery_fixer"] is not config.ROLE_DEFAULTS["implement.rebase_conflict_fixer"]
