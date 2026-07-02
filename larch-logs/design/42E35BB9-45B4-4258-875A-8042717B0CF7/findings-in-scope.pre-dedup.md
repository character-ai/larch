### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan: Testing strategy
- **Concern**: Issue acceptance requires measurable panel-tier token reduction but the plan has no blocking gate before baseline write. Scenario: `python/cli.py lint skill-closure-growth` only fails when live metrics exceed baseline; a run that rearranges prose without lowering `closure_content_estimated_tokens` can still pass `make regen-skill-closure-baseline`, `make py-test`, and `make test-review-structure`, leaving acceptance unmet
- **Proposed resolution**: Capture pre-edit `panel-tier` `closure_content_estimated_tokens` via `python3 python/cli.py skill-closure report`; before `make regen-skill-closure-baseline`, require that metric to be strictly lower than the captured value and treat failure as not accepted



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/reviewer-templates.md:286-625
- **Concern**: Plan compresses three specialist GENERATED_BODY sections independently even though they duplicate shared contract tails with intentional differences today. Scenario: Per-section compression can yield divergent Necessity gate, Do NOT report, Output format, or TSV tails across `reviewer-plan-fidelity`, `reviewer-code-robustness`, and `reviewer-security-structure-tests`, violating zero behavior change across reviewer slots
- **Proposed resolution**: Compress the shared tail once, paste the same bytes into all three specialist sections (preserve only each section's primary-focus body), then regenerate the three generated agents



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan: Approach / agents/reviewer-correctness.md
- **Concern**: Hand-maintained alignment target is unspecified relative to plan-review-only contract variants. Scenario: `## Reviewer: Plan Fidelity` uses plan-specific In-Scope wording (`plan requirement anchor`, `concrete breakage path`); copying that tail into the five code specialists would change their output contract away from current `file:line` semantics
- **Proposed resolution**: Name `agents/reviewer-code-robustness.md` (or the Security + Structure template tail) as the canonical shared-block source for hand-maintained agents; exclude Plan Fidelity plan-review variants from that sync step



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/lint/lint_skill_closure_growth.py:543-576
- **Concern**: The plan targets ~15% reduction on nine in-scope reviewer sources, but issue acceptance is measured on the full panel-tier ratchet, which also counts six untouched files (~117KB of ~233KB; code-reviewer, implementer agents, orchestrator-aggregator, voting-protocol).. Scenario: Compressing only reviewer-templates.md plus the eight reviewer-*.md agents by ~15% yields ~8% panel-tier closure_content_estimated_tokens drop. The implementer can satisfy the plan yet miss the issue’s ~15% ratchet target, and skill-closure report only prints aggregate panel-tier totals (not per-file deltas).
- **Proposed resolution**: Add an explicit acceptance math note: either expect ~8–10% aggregate panel-tier reduction when non-goal files stay fixed, or require ~25–30% compression on the nine in-scope files to reach ~15% on the ratchet; state which threshold gates baseline regen before `make regen-skill-closure-baseline`.



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:138-139
- **Concern**: Acceptance-required make py-test is optional. Scenario: The issue acceptance requires rendering and template harnesses to pass, but the plan lets the implementer skip make py-test and still follow the plan, so template-suite failures can ship unverified
- **Proposed resolution**: Make the required template-suite verification non-optional: run make py-test, or name and require the narrower make py-test template suite if one exists



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan Approach (manual compression of five hand-maintained agents)
- **Concern**: Align ... output format ... with the compressed template wording overwrites specialist-specific output contracts. Scenario: Hand-maintained agents intentionally differ in In-Scope list fields (e.g. reviewer-plan-fidelity.md requires plan anchors and concrete breakage paths; reviewer-correctness.md uses different Important-finding scenario rules). Verbatim template alignment can drop those per-specialist bullets while dual-list headers remain, changing reviewer behavior and violating zero-behavior-change acceptance
- **Proposed resolution**: Narrow alignment to shared boilerplate only (Do NOT report, prose length cap, TSV header/field literals, OOS cap text). Add an explicit guard: do not replace specialist-specific Primary focus, Input requirement, plan-verification, or In-Scope field requirements; compress those sections in place only



### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:127-139
- **Concern**: Acceptance-required Python template verification is optional. Scenario: The issue acceptance requires rendering and template harnesses to pass, but the plan marks `make py-test` as "if time allows"; an implementer can follow the plan, skip it, and ship prompt-template compression without the accepted template suites being verified.
- **Proposed resolution**: Make the acceptance-required `make py-test` coverage non-optional, or name and require the exact template pytest subset from `make py-test` if a narrower command is sufficient.



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan:Testing strategy
- **Concern**: Required validation omits shrink-path baseline freshness gate. Scenario: Acceptance requires measurable panel-tier token reduction committed in python/skill-closure-baseline.json. The plan only requires python3 python/cli.py lint skill-closure-growth --skill panel-tier, which is one-directional (fails only on growth). After a prose shrink, that check can pass while the committed baseline is still stale; CI then fails test_committed_baseline_matches_fresh_scan in python/tests/lint/test_lint_skill_closure_growth.py. make py-test is optional here, so an implementer can mark validation done without catching the miss.
- **Proposed resolution**: Add make test-lint-skill-closure-growth (or python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py::test_committed_baseline_matches_fresh_scan) to the required Testing strategy immediately after make regen-skill-closure-baseline, and add a Failure modes bullet that lint skill-closure-growth alone does not prove the baseline was regenerated and committed.



### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:138-139
- **Concern**: Acceptance-required `make py-test` is conditional. Scenario: The feature acceptance requires rendering and template harnesses under `make py-test` to pass, but the plan says to run full Python tests only if time allows, so an implementer can skip a required acceptance check and still appear plan-compliant.
- **Proposed resolution**: Make `make py-test` a required validation step rather than optional.



### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-Prompt Contract Preservation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/reviewer-templates.md:7-626
- **Concern**: [SCOPE-REDUCTION] Cross-marker rubric dedupe is allowed by the density bullets but would strip runtime instructions from regenerated agents. Scenario: Approach says to remove duplicate rubric wording globally; `_extract_generated_body` only copies text between each section's GENERATED_BODY markers into `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, and `agents/reviewer-security-structure-tests.md` (`python/larch/rendering/_rendering_generators.py:213-214`), so hoisting shared necessity-gate / Do NOT report / OOS-cap prose outside those markers would still pass `generate check` while dropping that guidance from generated agents and breaking the dual-list + TSV contract at runtime
- **Proposed resolution**: Add an explicit constraint: dedupe only by shortening text inside each `<!-- BEGIN GENERATED_BODY -->` block (and inside each hand-maintained `agents/reviewer-*.md`); never move review-runtime instructions to top-level template prose or cross-reference another section; accept residual duplication across blocks 1. **correctness** — `skills/shared/reviewer-templates.md:7-626`: The plan's global "remove duplicate rubric wording" guidance does not forbid hoisting shared blocks out of `<!-- BEGIN GENERATED_BODY -->` sections. Generated agents are built only from intra-marker content (`python/larch/rendering/_rendering_generators.py:213-214`), so that hoist would silently drop necessity-gate, Do NOT report, OOS-cap, and structured-output instructions from `agents/reviewer-plan-fidelity.md` and siblings while `python/cli.py generate check` still passes. **Suggested revision:** State explicitly that every review-runtime instruction must stay inside each target `GENERATED_BODY` block or hand-maintained agent file; shorten in place only. Overall the plan otherwise matches the issue well: it keeps `agents/code-reviewer.md`, implementers, orchestrator-aggregator, and `skills/shared/voting-protocol.md` out of scope; lists all three generated agents, five hand-maintained specialists, full `agents/pre-rendered/*` regen, and `python/skill-closure-baseline.json`; and calls out preservation of `### In-Scope Findings`, `### Out-of-Scope Observations`, severity labels, JSONL/TSV schemas, markers, and placeholders. Regeneration order (template → generated agents → hand-maintained edits → pre-rendered → baseline) is sound.



