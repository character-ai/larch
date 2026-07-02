### FINDING_1: Closure-growth validation can pass without proving a fresh baseline
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan relies on a one-directional `lint skill-closure-growth` check and optional post-step validation, so an edit can shrink prose, still leave `python/skill-closure-baseline.json` stale, and satisfy the plan without proving the acceptance metric was actually ratcheted and committed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Capture pre-edit `panel-tier` `closure_content_estimated_tokens` via `python3 python/cli.py skill-closure report`; before `make regen-skill-closure-baseline`, require that metric to be strictly lower than the captured value and treat failure as not accepted
  - From Cursor-Requirements: Add `make test-lint-skill-closure-growth` (or `python3 -m pytest python/tests/lint/test_lint_skill_closure_growth.py::test_committed_baseline_matches_fresh_scan`) to the required Testing strategy immediately after `make regen-skill-closure-baseline`, and add a Failure modes bullet that `lint skill-closure-growth` alone does not prove the baseline was regenerated and committed.

### FINDING_2: Shared generated reviewer tails can diverge across specialist sections
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Independently compressing the three `GENERATED_BODY` specialist sections can cause their shared contract tails to drift, which would change the `Necessity` gate, `Do NOT report`, output-format, or TSV wording across reviewer slots even though the intent is zero behavior change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Compress the shared tail once, paste the same bytes into all three specialist sections (preserve only each section's primary-focus body), then regenerate the three generated agents

### FINDING_3: Hand-maintained template sync can overwrite specialist-specific contracts
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The alignment step needs to keep specialist-specific prompt contracts intact. Using a plan-review variant or copying the compressed template wording into the hand-maintained agents wholesale can alter `plan`-specific semantics, `file:line` semantics, and per-specialist In-Scope requirements instead of just removing shared boilerplate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Name `agents/reviewer-code-robustness.md` (or the Security + Structure template tail) as the canonical shared-block source for hand-maintained agents; exclude Plan Fidelity plan-review variants from that sync step
  - From Cursor-Pragmatic: Narrow alignment to shared boilerplate only (Do NOT report, prose length cap, TSV header/field literals, OOS cap text). Add an explicit guard: do not replace specialist-specific Primary focus, Input requirement, plan-verification, or In-Scope field requirements; compress those sections in place only

### FINDING_4: Acceptance math is underspecified against the full panel-tier ratchet
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan talks about ~15% reduction on the nine in-scope files, but the acceptance target is measured on the full panel tier, including untouched files, so the implementer can satisfy the narrower file set while missing the actual ratcheted reduction required by the issue.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add an explicit acceptance math note: either expect ~8–10% aggregate panel-tier reduction when non-goal files stay fixed, or require ~25–30% compression on the nine in-scope files to reach ~15% on the ratchet; state which threshold gates baseline regen before `make regen-skill-closure-baseline`

### FINDING_5: Required template-suite verification is optional
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The plan treats `make py-test` as optional or conditional, so an implementer can finish the edit path without running the template and rendering harnesses that the acceptance criteria require.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the required template-suite verification non-optional: run make py-test, or name and require the narrower make py-test template suite if one exists
  - From Codex-Pragmatic: Make the acceptance-required `make py-test` coverage non-optional, or name and require the exact template pytest subset from `make py-test` if a narrower command is sufficient.
  - From Codex-Requirements: Make `make py-test` a required validation step rather than optional.

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-Prompt Contract Preservation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/reviewer-templates.md:7-626
- **Concern**: [SCOPE-REDUCTION] Cross-marker rubric dedupe is allowed by the density bullets but would strip runtime instructions from regenerated agents. Scenario: Approach says to remove duplicate rubric wording globally; `_extract_generated_body` only copies text between each section's GENERATED_BODY markers into `agents/reviewer-plan-fidelity.md`, `agents/reviewer-code-robustness.md`, and `agents/reviewer-security-structure-tests.md` (`python/larch/rendering/_rendering_generators.py:213-214`), so hoisting shared necessity-gate / Do NOT report / OOS-cap prose outside those markers would still pass `generate check` while dropping that guidance from generated agents and breaking the dual-list + TSV contract at runtime
- **Proposed resolution**: Add an explicit constraint: dedupe only by shortening text inside each `<!-- BEGIN GENERATED_BODY -->` block (and inside each hand-maintained `agents/reviewer-*.md`); never move review-runtime instructions to top-level template prose or cross-reference another section; accept residual duplication across blocks 1. **correctness** — `skills/shared/reviewer-templates.md:7-626`: The plan's global "remove duplicate rubric wording" guidance does not forbid hoisting shared blocks out of `<!-- BEGIN GENERATED_BODY -->` sections. Generated agents are built only from intra-marker content (`python/larch/rendering/_rendering_generators.py:213-214`), so that hoist would silently drop necessity-gate, Do NOT report, OOS-cap, and structured-output instructions from `agents/reviewer-plan-fidelity.md` and siblings while `python/cli.py generate check` still passes. **Suggested revision:** State explicitly that every review-runtime instruction must stay inside each target `GENERATED_BODY` block or hand-maintained agent file; shorten in place only. Overall the plan otherwise matches the issue well: it keeps `agents/code-reviewer.md`, implementers, orchestrator-aggregator, and `skills/shared/voting-protocol.md` out of scope; lists all three generated agents, five hand-maintained specialists, full `agents/pre-rendered/*` regen, and `python/skill-closure-baseline.json`; and calls out preservation of `### In-Scope Findings`, `### Out-of-Scope Observations`, severity labels, JSONL/TSV schemas, markers, and placeholders. Regeneration order (template → generated agents → hand-maintained edits → pre-rendered → baseline) is sound.
