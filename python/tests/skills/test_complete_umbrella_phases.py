"""Structure pins for complete-umbrella phase isolation."""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCES = REPO_ROOT / "skills" / "complete-umbrella" / "references"
PHASES = (
    "recon-design.md",
    "implement.md",
    "adversarial-review.md",
    "ship.md",
)


def _read(name: str) -> str:
    return (REFERENCES / name).read_text(encoding="utf-8")


def test_every_primary_phase_loads_the_shared_context_economy_contract() -> None:
    for phase in PHASES:
        assert (
            "Read `phase-common.md` in this directory in full before acting."
            in _read(phase)
        )

    common = _read("phase-common.md")
    assert "Set `head_limit` on every `Grep` call." in common
    assert "`sed -n`, `grep -n`, or `grep -rn`" in common
    assert "Put independent tool calls in one assistant message." in common
    assert "Put any handoff over 2,000 tokens" in common
    assert "tail -20" in common


def test_implement_and_review_inputs_are_phase_scoped() -> None:
    implementation = _read("implement.md")
    assert (
        "Read only `$SESSION_TMPDIR/design-brief.md` and `$SESSION_TMPDIR/leaf-issue.md`"
        in implementation
    )
    assert "Do not repeat broad repository exploration." in implementation

    review = _read("adversarial-review.md")
    assert "Start from only `$SESSION_TMPDIR/design-brief.md`" in review
    assert "repository-wide stale-caller sweep" in review
    assert "asserts a real success path executed" in review


def test_ship_is_deterministic_and_fixer_is_failure_only() -> None:
    ship = _read("ship.md")
    assert "complete-umbrella ship-leaf" in ship
    assert "refresh CI once every 300 seconds" in ship
    assert "`ci_failed`" in ship
    assert "`needs-orchestrator-finalize`" in ship
    assert "Only the top-level complete-umbrella owner" in ship
    assert "`needs_conflict_fix`" in ship
    assert "conflict-fix.md" in ship
    assert "Do not spawn a CI fixer when checks are pending or green." in ship
    assert (
        "Do not spawn a conflict fixer unless the driver returned `needs_conflict_fix`."
        in ship
    )
    assert "The driver's persisted state enforces the fix-attempt cap." in ship
    assert "The driver's persisted state enforces the conflict-fix attempt cap." in ship

    conflict = _read("conflict-fix.md")
    assert "SHIP_STATUS=needs_conflict_fix" in conflict
    assert "MODE=conflict" in conflict
    assert "caller_kind=ship_pr_pre_push" in conflict
    assert "larch:ci-fixer" in conflict


def test_managed_leaf_phases_persist_and_verify_gate_evidence() -> None:
    recon = _read("recon-design.md")
    assert "valid durable plan" in recon
    assert "named-block write" in recon
    assert "--marker plan" in recon
    assert "before it adds `[IMPLEMENTING]`" in recon

    review = _read("adversarial-review.md")
    assert "--mode line-budget" in review
    assert "RUST_LINE_BUDGET_STATUS=deviation-required" in review
    assert "RUST_LINE_BUDGET_STATUS=deviation-recorded" in review
    assert "Publish the complete updated plan" in review


def test_top_level_routes_stale_budget_evidence_to_the_parent_finalizer() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "CHILD_STATUS=needs-orchestrator-finalize" in skill
    assert "--mode finalize-budget-deviation" in skill
    assert "active plan lease" in skill
    assert "only the plan record's measured base SHA, head SHA, and count" in skill
