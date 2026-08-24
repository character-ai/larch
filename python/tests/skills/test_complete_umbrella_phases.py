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


def test_recon_does_not_repeat_the_imported_agents_rules_read() -> None:
    recon = _read("recon-design.md")
    normalized = " ".join(recon.split())
    assert recon.count("`AGENTS.md`") == 1
    assert "Read `AGENTS.md`" not in recon
    assert (
        "Read `ARCHITECTURAL_INVARIANTS.md` and "
        "`ARCHITECTURAL_GUIDELINES.md` when present."
    ) in recon
    assert (
        "`AGENTS.md` is already loaded through the `CLAUDE.md` import chain." in recon
    )
    assert "Do not read it again." in normalized


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
    assert "needs-orchestrator-finalize" not in ship
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
    assert "It does not\nvalidate a durable plan." in recon
    assert "named-block write" in recon
    assert "--marker plan" in recon
    assert "bound the\n`[IMPLEMENTING]` change to the live leaf snapshot" in recon

    review = _read("adversarial-review.md")
    assert "--mode line-budget" in review
    assert "RUST_LINE_BUDGET_STATUS=over-limit" in review
    assert "automatic continue-with-warning path" in review
    assert "do not edit or publish the" in review


def test_recon_routes_only_malformed_plans_or_unactionable_bodies() -> None:
    recon = _read("recon-design.md")
    normalized = " ".join(recon.split())
    assert "plan-block read" in recon
    assert "Do not replace or republish it." in recon
    assert "MALFORMED=<reason>" in recon
    assert "body is totally unactionable" in normalized
    assert "A body is actionable when it contains any discernible" in normalized
    assert "absent plan block, M1/M2 grammar gaps" in normalized
    assert "cross-leaf ordering" in normalized
    assert "narrowest evidence-based decision" in normalized
    assert "These are the only `needs-design` routes." in recon
    assert (
        "Do not stop or route to `needs-design` over an M1/M2 grammar gap"
        in normalized
    )
    assert "SHIP_STATUS=needs-design" not in recon
    assert "PHASE_STATUS=needs-design" in recon
    assert "HANDOFF_FILE=needs-design.md" in recon
    assert "oversize_override" not in recon

    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    needs_design = skill.index("CHILD_FAILURE_CLASS=needs-design")
    reset = skill.index("resets only a stale active leaf title", needs_design)
    assert needs_design < reset


def test_top_level_continues_after_an_over_limit_budget_warning() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "needs-orchestrator-finalize" not in skill
    assert "finalize-budget-deviation" not in skill
    assert "independently measured advisory" in skill
    assert "continues through the ordinary merge path" in skill


def test_top_level_recovers_only_an_exact_remote_done_orphan() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "complete-umbrella recover-orphaned-child" in skill
    assert "BGJOB_RC=orphaned" in skill
    assert "CHILD_RECOVERED=true" in skill
    assert "already closed with its exact `[DONE]`" in skill
    assert "Do not wait, sleep, or retry the recovery." in skill


def test_phase_return_contract_uses_basename_handoffs() -> None:
    common = _read("phase-common.md")
    assert "Prefer `HANDOFF_FILE=<basename under $SESSION_TMPDIR>`" in common
    assert "Do not echo driver stdout, `SHIP_STATUS`" in common

    recon = _read("recon-design.md")
    assert "HANDOFF_FILE=design-brief.md" in recon
    assert "Do not echo `SHIP_STATUS`" in recon
    assert "<absolute path to design-brief.md>" not in recon

    for phase, basename in (
        ("implement.md", "implementation-summary.md"),
        ("adversarial-review.md", "review-summary.md"),
        ("ship.md", "ship-summary.md"),
        ("ci-fix.md", "ci-fix-round-<N>.md"),
        ("conflict-fix.md", "conflict-fix-round-<N>.md"),
    ):
        text = _read(phase)
        assert f"HANDOFF_FILE={basename}" in text
        assert "<absolute path" not in text

    ship = _read("ship.md")
    assert "ignore surrounding narration and cosmetic `HANDOFF_FILE` path slips" in ship
    assert "re-spawn that fixer in a fresh context up to two additional times" in ship


def test_whole_leaf_loop_bgjob_binds_one_durable_session_owner() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    start = (
        'LARCH_CLAUDE_PID="$COMPLETE_UMBRELLA_OWNER_PID" '
        '"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" bgjob start'
    )
    assert skill.count(start) == 1
    assert "STEP=complete-umbrella-leaves" in skill
    assert "complete-umbrella run-leaves" in skill
    assert "complete-umbrella next" not in skill
    assert "complete-umbrella run-child" not in skill
    assert "complete-umbrella verify-child" not in skill
    assert "uses that same graph to verify the prior child and select the next leaf" in skill
    for key in (
        "CHILD_ATTEMPT_COUNT",
        "TRANSIENT_CHILD_RETRY_COUNT",
        "NET_PROBE_ATTEMPT_COUNT",
        "NET_WAIT_SECONDS",
        "LEAF_RESET_ATTEMPT_COUNT",
        "RESET_BACKOFF_SECONDS",
        "FAILED_STEP",
        "FAILED_LEAF",
        "FAILURE_REASON",
    ):
        assert key in skill
    assert "fixed Anthropic and GitHub endpoints" in skill
    assert "capped exponential backoff" in skill
    assert "up to three times with bounded backoff" in skill
    assert "same handoff root up to twenty additional times" in skill
    assert "sleeps one minute" in skill
    assert "host suspend does not consume the budget" in skill
    assert "Offline probe rounds do not consume child relaunch attempts." in skill
    assert "wait lease" in skill
    assert "--max-wait-s 7200" in skill
    assert "run_in_background: true" in skill
    assert "330000" not in skill
    wait_contract = (
        REPO_ROOT / "skills" / "shared" / "bgjob-wait.md"
    ).read_text(encoding="utf-8")
    assert 'LARCH_CLAUDE_PID="$PPID"' in wait_contract
    assert "wait lease" in wait_contract


def test_top_level_uses_one_call_bootstrap_before_start() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    step_zero = skill.split("## Step 0:", 1)[1].split("## Step 1:", 1)[0]
    assert step_zero.count("```bash") == 1
    assert "complete-umbrella bootstrap" in step_zero
    assert "scripts/larch.sh" in step_zero
    assert "python3" not in step_zero
    assert "python/cli.py" not in step_zero
    assert "The bootstrap calls `resume` before session setup or `start`." in step_zero
    assert "complete-umbrella resume" not in step_zero
    assert "complete-umbrella start" not in step_zero
    assert "session setup \\" not in step_zero
    assert "kv get" not in skill
    assert "Do not redirect bootstrap stdout." in step_zero
    assert "COMPLETE_UMBRELLA_OWNER_PID" in step_zero
    assert "RESUME_ACTION=wait" in skill
    assert "RESUME_ACTION=reselect" in skill
    assert "without truncating a file or starting another bgjob" in skill
    assert "A resumed `wait` has no new start marker" in skill
    assert "Set `RESUME_ACTION=reselect`, then return immediately to Step 1" in skill
    assert "complete-umbrella clear-pointer" in skill
    assert "POINTER_CLEARED=true" in skill


def test_audit_gap_uses_one_file_and_attach_driver_call() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    step5 = skill.split("## Step 5: File and attach one audit gap", 1)[1].split(
        "## Step 6: Finish and close", 1
    )[0]

    assert step5.count("complete-umbrella file-gap") == 1
    assert "complete-umbrella validate-gap" not in step5
    assert "complete-umbrella attach-leaf" not in step5
    assert "larch:issue" not in step5
    assert "Skill tool" not in step5
    assert "gap-issue.sentinel" not in step5
    assert "ISSUE_NUMBER" in step5
    assert "LEAF_ATTACHED=true" in step5
    assert "security-sensitive" in step5


def test_audit_distinguishes_full_first_pass_from_bounded_repeat_scope() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    step4 = skill.split("## Step 4: Audit the complete umbrella inline", 1)[1].split(
        "## Step 5: File and attach one audit gap", 1
    )[0]

    assert "**First audit — full breadth.**" in step4
    assert "**Repeat audit — bounded to the gap round.**" in step4
    assert (
        "Verify only (a) each gap leaf landed since the prior audit against its own "
        "acceptance criteria on current `main`"
    ) in step4
    assert "(b) the integration surfaces the prior audit flagged." in step4
    assert "Do not delegate the audit." in step4


def test_top_level_bounds_host_agnostic_production_guard_false_denies() -> None:
    skill = (REPO_ROOT / "skills" / "complete-umbrella" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    recovery = (
        REPO_ROOT / "docs" / "complete-umbrella-recovery.md"
    ).read_text(encoding="utf-8")
    installation = (REPO_ROOT / "docs" / "installation-and-setup.md").read_text(
        encoding="utf-8"
    )
    catalog = (REPO_ROOT / "docs" / "skills.md").read_text(encoding="utf-8")
    security = (
        REPO_ROOT / "docs" / "security" / "workflow-trust-and-mutations.md"
    ).read_text(encoding="utf-8")
    assert "Production-guard false-deny" in skill
    assert "packaged reader" in skill
    assert "Do not rephrase the driver as `gh`, curl, wget" in skill
    assert "## Harness false-denies" in recovery
    for guard in ("pagerduty", "hyperdx", "changes", "log-evidence"):
        assert guard in recovery
    assert "hand-edit lifecycle titles" in recovery
    for text in (skill, recovery, installation, catalog, security):
        prose = " ".join(text.split())
        assert "v2.0.3" in prose
        assert "guard is unavailable" in prose
        assert "Claude Code" in prose
        assert "request_smart_mode_approval=true" not in prose
    for text in (skill, recovery, installation, security):
        assert "character-tech/smarts#909" in " ".join(text.split())
    for text in (skill, recovery, security):
        prose = " ".join(text.split())
        assert "request_smart_mode_approval" in prose
        assert "has no" in prose
    assert "`permissionDecision: deny`" in recovery
    assert "`pd`" in recovery
    assert "`--tmpdir`" in recovery
    assert "repeat the identical denied workflow-driver command once" in skill
    assert "Attempt each remaining diagnostic and cleanup command at most once" in skill
    assert "with no guard retry" in skill
    assert "stop without claiming terminal success" in skill
    assert "preserve any pointer and the session tmpdir" in recovery
    assert "## Co-installed PreToolUse gates" in security
