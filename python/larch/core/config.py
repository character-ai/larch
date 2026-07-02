"""Tunables for the ship-pr Python rewrite (stdlib-only; no logic)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final, Literal

from larch.outcomes import Outcome

ToolName = Literal["cursor", "codex", "claude"]
RoleKind = Literal["waterfall", "first_available", "slot_panel", "voter_policies", "single_slot"]

# Exit codes (align with ship-pr / implement conventions)
EXIT_OK: Final = 0
EXIT_USAGE: Final = 2
EXIT_NEEDS_USER_INPUT: Final = 3
EXIT_STALLED: Final = 4
EXIT_TRANSIENT: Final = 6
EXIT_INTERNAL_ERROR: Final = 1
# Helper-script parity exits used by the sh-to-py CLI companions.
EXIT_USAGE_ONE: Final = 1
EXIT_USAGE_TWO: Final = 2
EXIT_FORCE_PUSH_SETUP: Final = 2
EXIT_REBASE_CONFLICT: Final = 1
EXIT_REBASE_PUSH_FAILED: Final = 2
EXIT_REBASE_ERROR: Final = 3
EXIT_CHECK_MAIN_SYNC_BLOCKED: Final = 1
EXIT_CHECK_MAIN_SYNC_ERROR: Final = 2
EXIT_BEHIND_COUNT_USAGE: Final = 2
EXIT_PHANTOM_PROBE_USAGE: Final = 2
EXIT_GH_RUN_LOGS_IN_PROGRESS: Final = 3
# report_tokens_cli uses EXIT_BAIL; ship STALLED uses EXIT_STALLED.
EXIT_BAIL: Final = 4
EXIT_TIMEOUT: Final = 124
OUTCOME_EXIT_MAP: Final[dict[Outcome, int]] = {
    Outcome.OK: EXIT_OK,
    Outcome.NEEDS_USER_INPUT: EXIT_NEEDS_USER_INPUT,
    Outcome.STALLED: EXIT_STALLED,
    Outcome.TRANSIENT: EXIT_TRANSIENT,
    Outcome.INTERNAL_ERROR: EXIT_INTERNAL_ERROR,
}


# ship.py JSON/result literals
JOURNAL_EVENT_SHIP_RESULT: Final = "ship-result"
NEEDS_USER_FIRST_FIXER_NON_HEALTH: Final = "first-fixer-non-health"
NEEDS_USER_CI_FIX_EXHAUSTED: Final = "ci-fix-exhausted"
NEEDS_USER_FIX_ATTEMPTS_EXHAUSTED: Final = "fix-attempts-exhausted"
NEEDS_USER_REVIEW_REQUIRED: Final = "review-required"
NEEDS_USER_LOCAL_UNFIXABLE: Final = "local-unfixable"
NEEDS_USER_CI_LOCAL_UNFIXABLE: Final = "ci-local-unfixable"
NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX: Final = "ship-pr-internal-lint-fix"
NEEDS_USER_REASON_TOKENS: Final = (
    NEEDS_USER_FIRST_FIXER_NON_HEALTH,
    NEEDS_USER_CI_FIX_EXHAUSTED,
    NEEDS_USER_FIX_ATTEMPTS_EXHAUSTED,
    NEEDS_USER_REVIEW_REQUIRED,
    NEEDS_USER_LOCAL_UNFIXABLE,
    NEEDS_USER_CI_LOCAL_UNFIXABLE,
    NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
)
POST_DISPATCH_NEXT_CONTINUE: Final = "continue"
POST_DISPATCH_NEXT_BAIL: Final = "bail"
POST_DISPATCH_BAIL_MAIN_BRANCH: Final = "main-branch-post-dispatch"
BAIL_REASON_RECOVERY_OUT_OF_SCOPE: Final = "recovery-out-of-scope"
IMPLEMENTATION_COMMIT_FAILED: Final = "implementation-commit-failed"
REVIEW_CHANGE_DETECTION_FAILED: Final = "review-change-detection-failed"
CHECKS_COMMIT_ROUTE_MARKER_STEP3: Final = "implement-step3-checks"
CHECKS_COMMIT_ROUTE_MARKER_STEP5_SELF_REVIEW: Final = "implement-step5-self-review"
STALL_RECOVERY_NEEDS_USER_BAIL_REASON_TOKENS: Final[tuple[str, ...]] = (
    NEEDS_USER_FIRST_FIXER_NON_HEALTH,
    NEEDS_USER_CI_FIX_EXHAUSTED,
    NEEDS_USER_FIX_ATTEMPTS_EXHAUSTED,
    NEEDS_USER_REVIEW_REQUIRED,
    NEEDS_USER_LOCAL_UNFIXABLE,
    NEEDS_USER_SHIP_PR_INTERNAL_LINT_FIX,
)

# Subprocess / CI wait
SUBPROCESS_DEFAULT_TIMEOUT_SEC: Final = 1800
CI_WAIT_TIMEOUT_SEC: Final = 1800
CI_WAIT_POLL_INTERVAL_SEC: Final = 10
# Per-call subprocess timeout for the poll-time CI status queries (gh pr view /
# gh pr checks). Dedicated and far shorter than SUBPROCESS_DEFAULT_TIMEOUT_SEC so
# a single hung gh read cannot block gather_status for the whole poll budget
# (issue #5066). A hung query hits this timeout, returns exit EXIT_TIMEOUT, and a
# pr-view timeout counts toward CI_MONITOR_STATUS_FAILURE_BAIL (bail with
# CI_WAIT_BAIL_STATUS_STALE after the threshold).
CI_STATUS_QUERY_TIMEOUT_SEC: Final = 120
# Default empty-checks grace for the manual `ci status` / `ci wait` CLIs: a
# runless PR head (zero attached checks) classifies as NO_CHECKS within this
# window instead of polling the full CI_WAIT_TIMEOUT_SEC budget (issue #4924).
CI_WAIT_EMPTY_CHECKS_GRACE_SEC: Final = 120
# Bounded "did a fresh CI run start?" window for the ship merge loop after a
# head-changing push (CI-fix or rebase). When the push triggers no fresh run
# (observed: GitHub drops the `synchronize` event, issue #4867), zero checks on
# the new head would otherwise classify as "pending" and the monitor would poll
# the full CI_WAIT_TIMEOUT_SEC budget (~30 min) with no signal. Passing this
# grace makes a missing run surface as NO_CHECKS within the window so the driver
# fails loudly to a recoverable stall instead of hanging.
CI_WAIT_POST_FIX_EMPTY_CHECKS_GRACE_SEC: Final = 120
# Ship-driver-only poll-based startup deadline for the initial CI wait. First
# PR runs can attach more slowly than post-fix synchronize runs, so this window
# is longer than the post-fix grace but still avoids the full poll timeout for a
# truly runless head. This is not passed through empty_checks_grace because that
# path sleeps once for the whole grace period instead of probing every poll.
CI_WAIT_INITIAL_EMPTY_CHECKS_GRACE_SEC: Final = 300
CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED: Final = "poll-budget-exhausted"
CI_WAIT_BAIL_UNEXPECTED_EXIT: Final = "ci-wait-unexpected-exit"
CI_WAIT_BAIL_NO_CHECKS_OBSERVED: Final = "no-ci-checks-observed"
CI_WAIT_BAIL_STATUS_STALE: Final = "ci-status-stale"
CI_WAIT_BAIL_DECIDE_ERROR: Final = "ci-decide-error"
CI_WAIT_BAIL_REASON_TOKENS: Final[tuple[str, ...]] = (
    CI_WAIT_BAIL_POLL_BUDGET_EXHAUSTED,
    CI_WAIT_BAIL_UNEXPECTED_EXIT,
    CI_WAIT_BAIL_NO_CHECKS_OBSERVED,
    CI_WAIT_BAIL_STATUS_STALE,
    CI_WAIT_BAIL_DECIDE_ERROR,
)
CI_DECIDE_BAIL_STATUS_ERROR: Final = "ci-status-error"
CI_DECIDE_BAIL_TIMEOUT: Final = "ci-timeout"
CI_DECIDE_BAIL_TOO_MANY_REBASES: Final = "ci-too-many-rebases"
CI_DECIDE_BAIL_FIX_ATTEMPTS_EXHAUSTED: Final = NEEDS_USER_FIX_ATTEMPTS_EXHAUSTED
CI_DECIDE_BAIL_REASON_TOKENS: Final[tuple[str, ...]] = (
    CI_DECIDE_BAIL_STATUS_ERROR,
    CI_DECIDE_BAIL_TIMEOUT,
    CI_DECIDE_BAIL_TOO_MANY_REBASES,
    CI_DECIDE_BAIL_FIX_ATTEMPTS_EXHAUSTED,
)
# Step 5 review-loop terminal bail tokens, covering lint-fix loop failures and
# MAV/coder resume handoff commit failures. Single source of truth for the
# render-safe set below, the python/stall_recovery._classify_text lint-fix-bail-token
# check, and the bash safe_bail_reason_value() allowlist (kept in sync via
# scripts/python/cli.py stall-recovery lint_runtime_bail_tokens).
LINT_FIX_BAIL_REASON_TOKENS: Final[tuple[str, ...]] = (
    "lint-fix-failed",
    "lint-fix-attempt-cap",
    "lint-fix-main-agent-required",
    "lint-fix-commit-failed",
    "resume-handoff-commit-failed",
    "review-fix-commit-failed",
)
STALL_RECOVERY_BAIL_REASON_TOKENS: Final[tuple[str, ...]] = tuple(dict.fromkeys((
    *CI_WAIT_BAIL_REASON_TOKENS,
    *CI_DECIDE_BAIL_REASON_TOKENS,
    *STALL_RECOVERY_NEEDS_USER_BAIL_REASON_TOKENS,
    *LINT_FIX_BAIL_REASON_TOKENS,
    IMPLEMENTATION_COMMIT_FAILED,
    REVIEW_CHANGE_DETECTION_FAILED,
    "design-flaw",
    "escalate",
    "all-vendors-failed",
)))

# Transient retry defaults shared with python/retry.py.
TRANSIENT_RETRY_MAX_ATTEMPTS: Final = 3
TRANSIENT_RETRY_BACKOFF_SEC: Final = (2, 4)

# Voter calibration prompt-feedback.
ENV_LARCH_VOTER_CALIBRATION_FEEDBACK: Final = "LARCH_VOTER_CALIBRATION_FEEDBACK"
ENV_LARCH_VOTER_CALIBRATION_WINDOW: Final = "LARCH_VOTER_CALIBRATION_WINDOW"
VOTER_CALIBRATION_WINDOW_DEFAULT: Final = 100

# Loop caps
RCC_MAX_ITER_DEFAULT: Final = 3
CI_LOCAL_FIX_ITER_DEFAULT: Final = 6
WATERFALL_MAX_TIERS: Final = 3

@dataclass(frozen=True)
class SlotDefault:
    slot: str
    tool: ToolName
    semantic_label: str = ""
    model_role: str = ""
    agent: str = ""
    output: str = ""
    focus_area: str = ""
    weight: int = 0
    archetype: str = ""


@dataclass(frozen=True)
class VoterPolicyDefault:
    slot_num: str
    slot_name: str
    primary_tool: ToolName
    default_label: str
    archetype: str
    prompt_label: str
    output_name: str
    semantic_labels: tuple[tuple[str, str], ...] = ()
    allow_codex_fallback: bool = True


@dataclass(frozen=True)
class PanelDispatchPolicy:
    no_fallback_when_both_present_round_lt: int | None = None
    generic_codex_rounds: frozenset[int] = frozenset()


@dataclass(frozen=True)
class VoterDispatchPolicy:
    voter_waterfall_no_fallback: bool = False
    no_fallback_slots: frozenset[str] = frozenset()


@dataclass(frozen=True)
class DecomposePanelPolicy:
    parallel_tools: tuple[ToolName, ...] = ()
    panel_no_fallback: bool = False
    archetypes: tuple[str, ...] = ()


@dataclass(frozen=True)
class RoleDefault:
    role_id: str
    kind: RoleKind
    order: tuple[ToolName, ...] = ()
    slots: tuple[SlotDefault, ...] = ()
    voter_policies: tuple[VoterPolicyDefault, ...] = ()
    dispatch_policy: PanelDispatchPolicy | None = None
    voter_dispatch_policy: VoterDispatchPolicy | None = None
    decompose_panel_policy: DecomposePanelPolicy | None = None
    env_override: str = ""
    doc_phase: str = ""
    doc_role: str = ""
    doc_skills: str = ""
    doc_fallback: str = ""


_CODE_REVIEW_ARCHETYPES: Final[tuple[str, ...]] = ("correctness", "edge-cases", "testing")
_PLAN_REVIEW_ARCHETYPES: Final[tuple[str, ...]] = ("arch", "innovation", "pragmatic", "requirements")
_DECOMPOSE_ARCHETYPES: Final[tuple[str, ...]] = ("decomposition-specialist", "dependency-analyst", "scope-minimalist", "risk-isolation")


def _waterfall_role(role_id: str, *, order: tuple[ToolName, ...], doc_phase: str, doc_role: str, doc_skills: str, doc_fallback: str) -> RoleDefault:  # noqa: PLR0913
    return RoleDefault(role_id=role_id, kind="waterfall", order=order, doc_phase=doc_phase, doc_role=doc_role, doc_skills=doc_skills, doc_fallback=doc_fallback)


ROLE_DEFAULTS: Final[dict[str, RoleDefault]] = {
    "implement.step2_coder": _waterfall_role("implement.step2_coder", order=("codex", "cursor", "claude"), doc_phase="Implement Step 2", doc_role="Write the implementation", doc_skills="/implement", doc_fallback="Pick exactly one first-eligible coder; --coder reorders the two external tools, then Claude."),
    "implement.lint_fix_coder": _waterfall_role("implement.lint_fix_coder", order=("claude", "codex", "cursor"), doc_phase="Lint/checks", doc_role="Repair local lint/check failures", doc_skills="/implement, /review", doc_fallback="Claude, then Codex, then Cursor; main agent required after external tiers fail."),
    "implement.ci_recovery_fixer": _waterfall_role("implement.ci_recovery_fixer", order=("claude", "codex", "cursor"), doc_phase="CI recovery", doc_role="Fix failing CI/checks", doc_skills="/implement", doc_fallback="Distinct registry role using Claude, then Codex, then Cursor."),
    "implement.rebase_conflict_fixer": _waterfall_role("implement.rebase_conflict_fixer", order=("claude", "codex", "cursor"), doc_phase="Rebase conflicts", doc_role="Resolve rebase conflicts", doc_skills="/implement", doc_fallback="Distinct registry role using Claude, then Codex, then Cursor."),
    "review.fix_coder": _waterfall_role("review.fix_coder", order=("codex", "cursor", "claude"), doc_phase="Review fixes", doc_role="Apply accepted review findings", doc_skills="/implement, /review", doc_fallback="Codex, then Cursor, then Claude; main agent required after automated tiers fail."),
    "review.dynamic_archetype_scout": _waterfall_role("review.dynamic_archetype_scout", order=("cursor", "claude"), doc_phase="Code-review scout", doc_role="Propose dynamic reviewer archetypes", doc_skills="/review", doc_fallback="Cursor, then Claude. Codex is deliberately excluded."),
    "design.plan_archetype_scout": _waterfall_role("design.plan_archetype_scout", order=("cursor", "claude"), doc_phase="Plan-review scout", doc_role="Propose dynamic plan-review archetypes", doc_skills="/design", doc_fallback="Cursor, then Claude. Codex is deliberately excluded."),
    "design.brainstorm_framing": _waterfall_role("design.brainstorm_framing", order=("cursor", "codex", "claude"), doc_phase="Brainstorm framing", doc_role="Generate framing ideas", doc_skills="/design", doc_fallback="Step 1d.5 reads this role before launch and picks the first eligible external, then Claude text fallback."),
    "design.brainstorm_scope": _waterfall_role("design.brainstorm_scope", order=("codex", "cursor", "claude"), doc_phase="Brainstorm scope", doc_role="Generate scope ideas", doc_skills="/design", doc_fallback="Step 1d.5 reads this role before launch and picks the first eligible external, then Claude text fallback."),
    "design.plan_drafter": RoleDefault(
        role_id="design.plan_drafter",
        kind="first_available",
        order=("codex", "claude"),
        env_override="LARCH_DESIGN_DRAFTER",
        doc_phase="Plan drafting",
        doc_role="Draft the implementation plan",
        doc_skills="/design",
        doc_fallback="Codex when present, else Claude; LARCH_DESIGN_DRAFTER is the only env override and invalid values soft-skip to inline drafting.",
    ),
    "review.panel": RoleDefault(
        role_id="review.panel",
        kind="slot_panel",
        slots=(
            *(
                SlotDefault(
                    slot=archetype,
                    tool=tool,
                    agent=f"agents/reviewer-{archetype}.md",
                    output=f"{tool}-specialist-{archetype}-output.txt",
                    model_role="default" if tool == "codex" else "",
                    archetype=archetype,
                )
                for archetype in _CODE_REVIEW_ARCHETYPES
                for tool in ("cursor", "codex")
            ),
            SlotDefault(slot="generalist", tool="codex", agent="agents/code-reviewer.md", output="codex-generalist-output.txt", focus_area="code-quality", weight=1, model_role="default", archetype="generic"),
        ),
        dispatch_policy=PanelDispatchPolicy(generic_codex_rounds=frozenset()),
        doc_phase="Code review panel",
        doc_role="Review code changes",
        doc_skills="/review, /implement Step 5",
        doc_fallback="Cursor static rows emit when Cursor is available; Codex static rows emit when Codex is available and use the default model role; no generic Codex reviewer is emitted; reviewer panels always dispatch with --no-fallback so missing vendors drop rows instead of backfilling.",
    ),
    "design.plan_review_panel": RoleDefault(
        role_id="design.plan_review_panel",
        kind="slot_panel",
        slots=(
            *(
                SlotDefault(
                    slot=f"{tool}-plan-{archetype}",
                    tool=tool,
                    output=(f"codex-primary-plan-{archetype}-output.txt" if tool == "codex" else f"cursor-plan-{archetype}-output.txt"),
                    focus_area=archetype,
                    model_role="default" if tool == "codex" else "",
                    archetype=archetype,
                )
                for archetype in _PLAN_REVIEW_ARCHETYPES
                for tool in ("cursor", "codex")
            ),
            SlotDefault(slot="codex-plan-generic", tool="codex", output="codex-plan-generic-output.txt", focus_area="code-quality", model_role="default", archetype="generic"),
        ),
        dispatch_policy=PanelDispatchPolicy(generic_codex_rounds=frozenset()),
        doc_phase="Plan review panel",
        doc_role="Review implementation plans",
        doc_skills="/design",
        doc_fallback="Static archetypes are arch, innovation, pragmatic, requirements. Cursor rows emit when Cursor is available; Codex rows emit when Codex is available and use the default model role; no generic Codex reviewer is emitted; panel dispatch always uses --no-fallback.",
    ),
    "design.decompose_panel": RoleDefault(
        role_id="design.decompose_panel",
        kind="slot_panel",
        slots=tuple(
            SlotDefault(slot=f"decomp-{tool}-{archetype}", tool=tool, output=f"decomp-{tool}-{archetype}-output.txt", archetype=archetype)
            for archetype in _DECOMPOSE_ARCHETYPES
            for tool in ("cursor", "codex")
        ),
        decompose_panel_policy=DecomposePanelPolicy(parallel_tools=("cursor", "codex"), panel_no_fallback=True, archetypes=_DECOMPOSE_ARCHETYPES),
        doc_phase="Decompose panel",
        doc_role="Propose issue partitions",
        doc_skills="/design",
        doc_fallback="Allowed parallel tools are Cursor and Codex; emit only present vendors per archetype with --no-fallback. Claude generic remains an explicit both-absent branch.",
    ),
    "review.voters": RoleDefault(
        role_id="review.voters",
        kind="voter_policies",
        voter_policies=(
            VoterPolicyDefault("1", "voter-1", "codex", "codex-validity", "validity-correctness", "validity", "codex-validity-vote-output.txt", (("codex", "codex-validity"), ("cursor", "cursor-validity"), ("claude", "claude"))),
            VoterPolicyDefault("2", "voter-2", "codex", "codex-plan-fidelity", "plan-fidelity-completeness", "plan-fidelity", "codex-plan-fidelity-vote-output.txt", (("codex", "codex-plan-fidelity"), ("cursor", "cursor-plan-fidelity"), ("claude", "claude"))),
            VoterPolicyDefault("3", "voter-3", "codex", "codex-pragmatism", "pragmatism-cost", "pragmatism", "codex-pragmatism-vote-output.txt", (("codex", "codex-pragmatism"), ("cursor", "cursor-pragmatism"), ("claude", "claude"))),
        ),
        doc_phase="Code-review voters",
        doc_role="Vote on code-review findings",
        doc_skills="/review",
        doc_fallback="All voters dispatch through one shared waterfall manifest and re-dispatch on runtime failure: all three voters waterfall Codex, then Cursor, then Claude and voters 2/3 join the manifest whenever either external is present, so a both-external-down panel shrinks to the single Claude voter-1 anchor.",
    ),
    "design.plan_voters": RoleDefault(
        role_id="design.plan_voters",
        kind="voter_policies",
        voter_policies=(
            VoterPolicyDefault("1", "voter-1", "claude", "claude", "validity-correctness", "claude", "claude-vote-output.txt", (("claude", "claude"),)),
            VoterPolicyDefault("2", "voter-2", "codex", "codex", "plan-fidelity-completeness", "codex", "codex-vote-output.txt", (("codex", "codex"), ("cursor", "cursor"), ("claude", "claude"))),
            VoterPolicyDefault("3", "voter-3", "cursor", "cursor", "pragmatism-cost", "cursor", "cursor-vote-output.txt", (("cursor", "cursor"), ("codex", "codex"), ("claude", "claude"))),
        ),
        doc_phase="Plan voters",
        doc_role="Vote on plan-review findings",
        doc_skills="/design",
        doc_fallback="Voter 1 is Claude. Voter 2 waterfalls Codex, then Cursor, then Claude. Voter 3 waterfalls Cursor, then Codex, then Claude.",
    ),
    "review.findings_aggregator": RoleDefault(
        role_id="review.findings_aggregator",
        kind="single_slot",
        slots=(SlotDefault(slot="aggregator", tool="codex", output="aggregator-output.txt", model_role="review"),),
        doc_phase="Code findings aggregation",
        doc_role="Merge code-review findings",
        doc_skills="/review, /implement Step 5",
        doc_fallback="Codex-primary single slot through dispatch-waterfall, using the review model role before Cursor or Claude fallback.",
    ),
    "design.plan_findings_aggregator": RoleDefault(
        role_id="design.plan_findings_aggregator",
        kind="single_slot",
        slots=(SlotDefault(slot="aggregator", tool="codex", output="aggregator-output.txt", model_role="review"),),
        doc_phase="Plan findings aggregation",
        doc_role="Merge plan-review findings",
        doc_skills="/design",
        doc_fallback="Codex-primary single slot through dispatch-waterfall, using the review model role before Cursor or Claude fallback.",
    ),
    "design.decompose_aggregator": RoleDefault(
        role_id="design.decompose_aggregator",
        kind="single_slot",
        slots=(SlotDefault(slot="decompose-aggregator", tool="codex", output="aggregator-raw-output.txt"),),
        doc_phase="Decompose aggregator",
        doc_role="Merge partition proposals",
        doc_skills="/design",
        doc_fallback="Codex-primary single slot through dispatch-waterfall.",
    ),
}

# Deprecated compatibility alias. Runtime consumers should use role-specific
# external_defaults.tool_order(...) calls instead of this shared name.
FIXER_TIER_ORDER: Final[tuple[str, ...]] = ROLE_DEFAULTS["implement.ci_recovery_fixer"].order
CLAUDE_OPUS_4_8_MODEL: Final = "claude-opus-4-8"
CLAUDE_SONNET_4_6_MODEL: Final = "claude-sonnet-4-6"
CLAUDE_HAIKU_4_5_MODEL: Final = "claude-haiku-4-5"
CLAUDE_FABLE_5_MODEL: Final = "claude-fable-5"
CLAUDE_CI_FIX_MODEL: Final = CLAUDE_OPUS_4_8_MODEL
CLAUDE_SUB_DEFAULT_MODEL_BY_RAW: Final[dict[str, str]] = {
    "claude_review": CLAUDE_SONNET_4_6_MODEL,
    "claude_vote": CLAUDE_SONNET_4_6_MODEL,
    "claude_scout": CLAUDE_SONNET_4_6_MODEL,
    "claude_draft": CLAUDE_SONNET_4_6_MODEL,
    "claude_ci_fix": CLAUDE_OPUS_4_8_MODEL,
    "claude_lint_fix": CLAUDE_OPUS_4_8_MODEL,
    "claude_review_fix": CLAUDE_SONNET_4_6_MODEL,
}


def claude_sub_default_model(raw: str) -> str:
    return CLAUDE_SUB_DEFAULT_MODEL_BY_RAW.get(raw, CLAUDE_OPUS_4_8_MODEL)


CI_AGENTIC_FIX_MAX_CYCLES: Final = 20
FIXER_ROLE: Final = "resolve-conflict"
REBASE_MAX_ATTEMPTS: Final = 20
# Rebase conflicts confined to these generated files are mechanically
# auto-resolvable: regenerate the file from the working tree (mirroring the
# matching `make regen-*` recipe) and continue, rather than attempting a textual
# merge. Maps the tracked repo-relative path to the `python/cli.py` argv that
# regenerates it. Consumed by finalize._rebase_no_push to auto-resolve pre-PR
# (postbump) rebase conflicts confined to these files instead of stalling
# unconditionally. See issue #5930.
REBASE_AUTORESOLVE_GENERATED_FILES: Final[dict[str, tuple[str, ...]]] = {
    "python/skill-closure-baseline.json": ("lint", "skill-closure-growth", "--write"),
}
# Defensive bound on the postbump auto-resolve `rebase --continue` loop; the
# realistic case resolves in one or two steps.
REBASE_AUTORESOLVE_MAX_STEPS: Final = 32
SHIP_PR_RRR_RESUME_PHASE: Final = "ship-pr-rrr-phase14"
SHIP_PR_PRE_PUSH_CALLER_KIND: Final = "ship_pr_pre_push"
SHIP_PR_RRR_AFTER_PHASE14_FLAG_BASENAME: Final = "ship-pr-rrr-after-phase14.flag"

# Environment variable names
ENV_LARCH_CI_LOCAL_FIX_ITER: Final = "LARCH_CI_LOCAL_FIX_ITER"
ENV_LARCH_NO_LOGS_COMMIT: Final = "LARCH_NO_LOGS_COMMIT"
ENV_LARCH_RUN_ID: Final = "LARCH_RUN_ID"
ENV_DESIGN_TMPDIR: Final = "DESIGN_TMPDIR"
ENV_IMPLEMENT_TMPDIR: Final = "IMPLEMENT_TMPDIR"
ENV_CLAUDE_PLUGIN_ROOT: Final = "CLAUDE_PLUGIN_ROOT"
ENV_REPO: Final = "REPO"
ENV_ISSUE_NUMBER: Final = "ISSUE_NUMBER"
ENV_SESSION_ID: Final = "SESSION_ID"
ENV_SESSION_TMPDIR: Final = "SESSION_TMPDIR"
ENV_CLAUDE_PID: Final = "CLAUDE_PID"
ENV_CODEX_BINARY_FOUND: Final = "CODEX_BINARY_FOUND"
ENV_CURSOR_BINARY_FOUND: Final = "CURSOR_BINARY_FOUND"
ENV_CODEX_PRESENT: Final = "CODEX_PRESENT"
ENV_CURSOR_PRESENT: Final = "CURSOR_PRESENT"
ENV_SUMMARY_OUTCOME: Final = "SUMMARY_OUTCOME"
ENV_FINAL_SUMMARY_PATH: Final = "FINAL_SUMMARY_PATH"
ENV_LARCH_DESIGN_DRIFT_MULTIPLE: Final = "LARCH_DESIGN_DRIFT_MULTIPLE"
ENV_LARCH_EXEC_ISSUE_ASSESSMENT_MODEL: Final = "LARCH_EXEC_ISSUE_ASSESSMENT_MODEL"
ENV_LARCH_CURSOR_MODEL: Final = "LARCH_CURSOR_MODEL"
ENV_LARCH_CODEX_MODEL: Final = "LARCH_CODEX_MODEL"
ENV_LARCH_CODEX_REVIEW_MODEL: Final = "LARCH_CODEX_REVIEW_MODEL"
ENV_LARCH_CODEX_VOTE_MODEL: Final = "LARCH_CODEX_VOTE_MODEL"
ENV_LARCH_CODEX_FIX_MODEL: Final = "LARCH_CODEX_FIX_MODEL"
ENV_LARCH_CODEX_EFFORT: Final = "LARCH_CODEX_EFFORT"
ENV_CLAUDE_PLUGIN_OPTION_CURSOR_MODEL: Final = "CLAUDE_PLUGIN_OPTION_CURSOR_MODEL"
ENV_CLAUDE_PLUGIN_OPTION_CODEX_MODEL: Final = "CLAUDE_PLUGIN_OPTION_CODEX_MODEL"
ENV_CLAUDE_PLUGIN_OPTION_CODEX_EFFORT: Final = "CLAUDE_PLUGIN_OPTION_CODEX_EFFORT"
ENV_RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX: Final = "RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX"
ENV_RUN_EXTERNAL_AGENT_POLL_INTERVAL: Final = "RUN_EXTERNAL_AGENT_POLL_INTERVAL"
ENV_LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME: Final = "LARCH_EXTERNAL_STARTUP_LOCK_FORCE_UNAME"
ENV_LARCH_EXTERNAL_STARTUP_LOCK_TTL: Final = "LARCH_EXTERNAL_STARTUP_LOCK_TTL"
ENV_LARCH_EXTERNAL_STARTUP_LOCK_TRIES: Final = "LARCH_EXTERNAL_STARTUP_LOCK_TRIES"
ENV_VALIDATE_STATUS: Final = "VALIDATE_STATUS"
ENV_VALIDATE_DEFECT_COUNT: Final = "VALIDATE_DEFECT_COUNT"
ENV_VALIDATE_MISSING_SCRIPT_COUNT: Final = "VALIDATE_MISSING_SCRIPT_COUNT"
ENV_VALIDATE_UNSAFE_TOKEN_COUNT: Final = "VALIDATE_UNSAFE_TOKEN_COUNT"
ENV_VALIDATE_SKIPPED_COUNT: Final = "VALIDATE_SKIPPED_COUNT"
ENV_VALIDATE_LOG_FILE: Final = "VALIDATE_LOG_FILE"
ENV_VALIDATOR_TARGET_FILE: Final = "_validator_target_file"
ENV_SITE: Final = "SITE"
ENV_MODE: Final = "MODE"
ENV_TMPDIR: Final = "TMPDIR"
ENV_HOME: Final = "HOME"
ENV_PATH: Final = "PATH"
ENV_USER: Final = "USER"
ENV_LOGNAME: Final = "LOGNAME"
ENV_LARCH_QUIET_DISABLE: Final = "LARCH_QUIET_DISABLE"
ENV_LARCH_QUIET_ACTIVE: Final = "LARCH_QUIET_ACTIVE"
ENV_LARCH_QUIET_LOG_FILE: Final = "LARCH_QUIET_LOG_FILE"
ENV_LARCH_QUIET_PID: Final = "LARCH_QUIET_PID"
ENV_LARCH_DESIGN_DRAFTER: Final = "LARCH_DESIGN_DRAFTER"
ENV_LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT: Final = "LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT"
EXTERNAL_HEALTH_CHECK_TIMEOUT_DEFAULT_SEC: Final = 30
EXEC_ISSUE_ASSESSMENT_MODEL_DEFAULT: Final = "claude-haiku-4-5"
CODEX_DEFAULT_MODEL: Final = "gpt-5.5"
CODEX_REVIEW_MODEL_DEFAULT: Final = "gpt-5.4-mini"
CODEX_VOTE_MODEL_DEFAULT: Final = "gpt-5.4-mini"
CODEX_FIX_MODEL_DEFAULT: Final = "gpt-5.4-mini"
CURSOR_DEFAULT_MODEL: Final = "composer-2.5"
CURSOR_AUTO_MODEL: Final = "auto"
# Teams plan per-token surcharge on all tokens (input, cache-read, output) for non-Auto
# Cursor agent requests. Source: cursor.com/docs/account/teams/pricing — "Cursor Token
# Rate $0.25/1M tokens" applies to pinned-model (composer-2.5) non-Auto requests.
# Empirically confirmed via June 2026 usage export (R²=0.998, no per-request fee).
CURSOR_TEAMS_TOKEN_RATE_SURCHARGE_PER_M: Final = 0.25
ENV_LARCH_CURSOR_TEAMS_SURCHARGE_PER_M: Final = "LARCH_CURSOR_TEAMS_SURCHARGE_PER_M"

# Implementation selector values
SHIP_PR_IMPL_BASH: Final = "bash"
SHIP_PR_IMPL_PYTHON: Final = "python"

# Path / artifact templates (format with .format or str.replace as needed)
PATH_MANIFEST_TEMPLATE: Final = "{tmpdir}/manifest.json"
PATH_QA_PENDING_TEMPLATE: Final = "{tmpdir}/qa-pending.json"
PATH_QUIET_LOG_TEMPLATE: Final = "{tmpdir}/larch-quiet-{script}-{pid}.log"
PATH_JSONL_JOURNAL_TEMPLATE: Final = "{tmpdir}/larch-journal-{run_id}.jsonl"

# Redaction placeholders (must not match redact patterns)
REDACTED_TOKEN: Final = "<REDACTED-TOKEN>"
REDACTED_PRIVATE_KEY: Final = "<REDACTED-PRIVATE-KEY>"
REDACTED_TMPDIR: Final = "<TMPDIR>"
REDACTED_OPERATOR_REPO: Final = "<OPERATOR_REPO_PATH>"

# proc.run timeout handling
PROC_TIMEOUT_EXIT_CODE: Final = EXIT_TIMEOUT


# /report-tokens live Python entrypoint
GITHUB_ISSUE_BODY_MAX_BYTES: Final = 65536
ENV_LARCH_REPORT_TOKENS_NO_ISSUE: Final = "LARCH_REPORT_TOKENS_NO_ISSUE"
ENV_LARCH_REPORT_TOKENS_NO_PLOT: Final = "LARCH_REPORT_TOKENS_NO_PLOT"
ENV_LARCH_REPORT_TOKENS_NO_OPEN: Final = "LARCH_REPORT_TOKENS_NO_OPEN"
ENV_LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND: Final = "LARCH_REPORT_TOKENS_POST_ACTUAL_SPEND"
ENV_LARCH_REPORT_TOKENS_ACTUAL_SPEND: Final = "LARCH_REPORT_TOKENS_ACTUAL_SPEND"
ENV_LARCH_REPORT_TOKENS_REPO: Final = "LARCH_REPORT_TOKENS_REPO"
ENV_LARCH_REPORT_TOKENS_LIMIT: Final = "LARCH_REPORT_TOKENS_LIMIT"
REPORT_TOKENS_TITLE_BY_SKILL: Final[dict[str, str]] = {
    "design": "[Design Analysis Report] Token costs as of {timestamp}",
    "implement": "[Implement Analysis Report] Token costs as of {timestamp}",
}

# Version bump classification helpers (dev/CI; release owns live versioning)
BUMP_COMMIT_SUBJECT_TEMPLATE: Final = "Bump version to {version}"
SEMVER_RE: Final = r"^[0-9]+\.[0-9]+\.[0-9]+$"
PLUGIN_JSON_PATH: Final = ".claude-plugin/plugin.json"
IDEMPOTENCY_DEPTH: Final = 3
TRANSPARENT_LARCH_LOGS_SUBJECT_PREFIX: Final = "chore(larch-logs): "
CLASSIFY_SCOPE_DIRS: Final[tuple[str, ...]] = ("skills", "agents")
APPLY_BUMP_ALLOWED_UNTRACKED_SUFFIXES: Final = (".launcher-stderr", ".redacted.log")
GIT_COMMIT_CO_AUTHORED_BY_TRAILER: Final = "Co-Authored-By: Claude Code <noreply@anthropic.com>"

# CI monitor loop (Phase 6)
CI_MONITOR_MAX_ITERATIONS: Final = 50
SHIP_MERGE_LOOP_MAX_ITERATIONS: Final = 50
SHIP_MERGE_CI_NOT_READY_STALL_THRESHOLD: Final = 3
CI_MONITOR_MAX_REBASES: Final = 20
CI_MONITOR_MAX_FIX_ATTEMPTS: Final = 10
CI_MONITOR_FIX_WATERFALL_MAX_ATTEMPTS: Final = 3
CI_MONITOR_TRANSIENT_RERUN_MAX: Final = 1
CI_MONITOR_STATUS_FAILURE_BAIL: Final = 3
CI_MONITOR_LOG_TAIL_LINES: Final = 100
CI_MONITOR_IN_PROGRESS_POLL_INTERVAL: Final = 15
CI_MONITOR_IN_PROGRESS_TIMEOUT: Final = 3600
CI_FIX_ROLE: Final = "fix"
CI_FIXABLE_JOBS: Final[frozenset[str]] = frozenset({
    "lint",
    "lint-local",
    "lint-mermaid",
    "shellcheck",
    "test-harnesses",
    "agent-lint",
    "agnix",
    "agent-sync",
    "python-lint",
    "python-pyright",
    "python-lint-duplicate-code",
    "python-tests",
    "bash32-check",
})

# Phase 5 — PR / merge / logging (live/default Python driver)
TRACKING_ISSUE_STATES: Final[tuple[str, ...]] = (
    "designing",
    "designed",
    "implementing",
    "done",
    "stalled",
)
TRACKING_ISSUE_PREFIX_BY_STATE: Final[dict[str, str]] = {
    "designing": "[DESIGNING] ",
    "designed": "[DESIGNED] ",
    "implementing": "[IMPLEMENTING] ",
    "done": "[DONE] ",
    "stalled": "[STALLED] ",
}
TRACKING_TITLE_MAX_LEN: Final = 256
REFRESH_SKIP_NO_REPO_CWD: Final = "no-repo-cwd"

MERGE_RESULT_MERGED: Final = "merged"
MERGE_RESULT_ADMIN_MERGED: Final = "admin_merged"
MERGE_RESULT_MAIN_ADVANCED: Final = "main_advanced"
MERGE_RESULT_CI_NOT_READY: Final = "ci_not_ready"
MERGE_RESULT_VERSION_ALREADY_PUBLISHED: Final = "version_already_published"
MERGE_RESULT_POLICY_DENIED: Final = "policy_denied"
MERGE_RESULT_ADMIN_FAILED: Final = "admin_failed"
MERGE_RESULT_REVIEW_REQUIRED: Final = "review_required"
MERGE_RESULT_ERROR: Final = "error"
MERGE_RESULTS: Final[frozenset[str]] = frozenset({
    MERGE_RESULT_MERGED,
    MERGE_RESULT_ADMIN_MERGED,
    MERGE_RESULT_MAIN_ADVANCED,
    MERGE_RESULT_CI_NOT_READY,
    MERGE_RESULT_VERSION_ALREADY_PUBLISHED,
    MERGE_RESULT_POLICY_DENIED,
    MERGE_RESULT_ADMIN_FAILED,
    MERGE_RESULT_REVIEW_REQUIRED,
    MERGE_RESULT_ERROR,
})
MERGE_RESULT_DRIVER_ALREADY_MERGED: Final = "already_merged"
POST_MERGE_MERGE_RESULTS: Final[frozenset[str]] = frozenset({
    MERGE_RESULT_MERGED,
    MERGE_RESULT_ADMIN_MERGED,
    MERGE_RESULT_DRIVER_ALREADY_MERGED,
})

FLUSH_COMMIT_SUBJECT_PREFIX: Final = "chore(larch-logs): flush "
FLUSH_RECOVERY_MAX_COMMITS: Final = 5
MERGE_PR_INITIAL_UNKNOWN_RETRIES: Final = 4
MERGE_PR_POST_PUSH_UNKNOWN_RETRIES: Final = 3
MERGE_DIAGNOSTIC_MAX_LEN: Final = 500

MANIFEST_STATUS_PARTIAL: Final = "partial"
MANIFEST_STATUS_DONE: Final = "done"
MANIFEST_STATUS_IN_PROGRESS: Final = "in-progress"

REFRESH_SKIP_STATE_FILE_MISSING: Final = "state-file-missing-fail-closed"
REFRESH_SKIP_POST_MERGE: Final = "post-merge"
REFRESH_SKIP_NO_RUN_ID: Final = "no-run-id"
REFRESH_SKIP_INVALID_RUN_ID: Final = "invalid-run-id"
REFRESH_SKIP_NO_LOGS_COMMIT: Final = "no-logs-commit"
REFRESH_SKIP_COMMIT_FAILED: Final = "commit-failed"
REFRESH_SKIP_VOLATILE_ONLY: Final = "volatile-only"
# Pre-merge flush skips merge_pr may continue past (bash refresh-run-logs || true).
REFRESH_SKIP_MERGE_OK: Final[frozenset[str]] = frozenset({
    REFRESH_SKIP_NO_REPO_CWD,
    REFRESH_SKIP_POST_MERGE,
    REFRESH_SKIP_STATE_FILE_MISSING,
    REFRESH_SKIP_NO_RUN_ID,
    REFRESH_SKIP_INVALID_RUN_ID,
    REFRESH_SKIP_NO_LOGS_COMMIT,
    REFRESH_SKIP_COMMIT_FAILED,
    REFRESH_SKIP_VOLATILE_ONLY,
})
REFRESH_SKIP_POST_ENSURE_PR_OK: Final[frozenset[str]] = frozenset({
    REFRESH_SKIP_NO_REPO_CWD,
    REFRESH_SKIP_POST_MERGE,
    REFRESH_SKIP_STATE_FILE_MISSING,
    REFRESH_SKIP_NO_RUN_ID,
    REFRESH_SKIP_INVALID_RUN_ID,
    REFRESH_SKIP_NO_LOGS_COMMIT,
    REFRESH_SKIP_VOLATILE_ONLY,
})

MERGE_SKIP_NOT_REQUESTED: Final = "merge skipped: merge=false"
MERGE_SKIP_DRAFT: Final = "merge skipped: draft PR"
MERGE_SKIP_FORKED: Final = "merge skipped: forked implement"
MERGE_SKIP_REPO_UNAVAILABLE: Final = "merge skipped: repo unavailable"

MERMAID_REASON_PIPE_IN_NODE: Final = "pipe-in-node-label"
MERMAID_REASON_BR_IN_ALIAS: Final = "br-in-participant-alias"
MERMAID_REASON_DOLLAR_IN_ALIAS: Final = "dollar-in-participant-alias"
MERMAID_REASON_UNCLOSED_FRONTMATTER: Final = "unclosed-frontmatter"

RUN_LOG_BATCH_TOKEN_REPORT: Final = "token-report"
RUN_LOG_BATCH_TIMING_REPORT: Final = "timing-report"
RUN_LOG_BATCH_SESSION_TRANSCRIPT: Final = "session-transcript"

TOKEN_SIDECAR_KEYS: Final[frozenset[str]] = frozenset({
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_create_tokens",
    "total_tokens",
})

PUSH_MAX_ATTEMPTS: Final = 3
ADMIN_ELIGIBLE_MERGE_STATES: Final[frozenset[str]] = frozenset({
    "CLEAN",
    "UNSTABLE",
    "HAS_HOOKS",
    "BLOCKED",
    "BEHIND",
})

INLINE_TRIAGE_MARKER: Final = "Inline-triage rule"
OOS_FILED_URL_FIELD: Final = "**Filed URL**"
