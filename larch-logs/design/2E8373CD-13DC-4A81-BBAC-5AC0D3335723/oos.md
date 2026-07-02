### FINDING_1: /design degraded-empty-collector must pin postplan emit after plan.txt edits
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: On the `LOOP_STATUS=degraded-empty-collector` path, Step 3 self-review may rewrite `plan.txt`, but the plan only says to run the same post-plan validation/settle path without naming the pinned launcher (`python/cli.py design postplan-emit` or `design-step2b-postplan.sh`). Other design revision sites require that helper for every plan change. An ad-hoc settle or Gate B bypass can skip `diff-lines.txt`, trailers, and command validation, causing Step 3b/5c publish failures or stale plan metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `skills/design/SKILL.md`, after self-review may edit `plan.txt`, require the same launcher used elsewhere: `python/cli.py design postplan-emit` (or `design-step2b-postplan.sh` with the existing site flags) before `design-step3-gate-b-bypass.sh`.
  - From Cursor-Innovation: In the `LOOP_STATUS=degraded-empty-collector` branch, when self-review rewrites `plan.txt`, require `python/cli.py design postplan-emit` (or the existing launcher fence) before `design-step3-gate-b-bypass.sh`; skip emit when the plan is unchanged.
  - From Cursor-Requirements: In the `LOOP_STATUS=degraded-empty-collector` branch, after any in-place `plan.txt` edit, invoke `python/cli.py design postplan-emit` through the existing launcher (same contract as Gate B / discussion re-emits) before `design-step3-gate-b-bypass.sh`.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_3: Implement self-review reference scoped only to explicit `--self-review`
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan adds a runtime `STEP5_REVIEW_STATUS=self-review-required` consumer in `/implement` Step 5, but `skills/implement/references/self-review.md` still limits `Consumer`, `When to load`, and the opening body to explicit `self_review=true` / `--self-review`. Orchestrators on the zero-survivor fallback path can skip or treat the reference as out of contract even after `skills/implement/SKILL.md` is updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update `Consumer`, `When to load`, and the first body sentence to name both entry conditions: explicit `self_review=true` and runtime zero-survivor `STEP5_REVIEW_STATUS=self-review-required`.
  - From Cursor-Innovation: Update `**Consumer**` and `**When to load**` to cover both `self_review=true` and `STEP5_REVIEW_STATUS=self-review-required`, matching the new entry-condition note.


Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Lazy-loaded plan-review reference still frames degraded-empty-collector only as a loop exit
- **Description**: [OUT_OF_SCOPE] Lazy-loaded plan-review reference still frames degraded-empty-collector only as a loop exit. Scenario: Step 3 MANDATORY-reads `plan-review.md`, which still documents `degraded-empty-collector` as zero-findings with no successful collectors and does not mention the new orchestrator self-review before Gate C bypass. SKILL.md owns the new branch, but maintainers debugging Step 3 from the reference can miss the self-review obligation.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:62-65
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Reviewer-templates header still claims conflict Phase 3 uses an external panel
- **Description**: [OUT_OF_SCOPE] Reviewer-templates header still claims conflict Phase 3 uses an external panel. Scenario: The plan rewrites conflict-resolution Phase 3 to main-agent self-review only, but the shared templates intro still lists `/implement` Phase 3 conflict-resolution reviewer panel alongside plan and code review. That stale contract can mislead future prompt or generator edits.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/reviewer-templates.md:3
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_3: [OUT_OF_SCOPE] Review-agents topology table still documents external conflict panel
- **Description**: [OUT_OF_SCOPE] Review-agents topology table still documents external conflict panel. Scenario: The plan only MAY_UPDATE `docs/review-agents.md` if it claims runtime zero-survivor always fails. The conflict-resolution row still links to the 3-reviewer topology anchor after Phase 3 drops externals, leaving operator docs inconsistent even when code and skills change.
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/review-agents.md:97
- **Phase**: design




Vote tally: YES=1 NO=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] Shared reviewer-templates header still claims Phase 3 conflict resolution uses an external panel
- **Description**: [OUT_OF_SCOPE] Shared reviewer-templates header still claims Phase 3 conflict resolution uses an external panel. Scenario: After the rewrite, line 3 will contradict conflict-resolution and mislead future prompt edits; runtime behavior follows the loaded reference, not this header.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/reviewer-templates.md:3
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_5: [OUT_OF_SCOPE] Design plan-review reference still describes degraded-empty-collector only as a zero-findings bypass
- **Description**: [OUT_OF_SCOPE] Design plan-review reference still describes degraded-empty-collector only as a zero-findings bypass. Scenario: Normative text will not mention main-agent self-review before Step 3b; operators reading plan-review.md alone may think the plan went unreviewed.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/references/plan-review.md:65
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] No structure harness pin for `self-review-required` Step 5 branch order
- **Description**: [OUT_OF_SCOPE] No structure harness pin for `self-review-required` Step 5 branch order. Scenario: The plan adds explicit ordering in `skills/implement/SKILL.md`, but unlike other Step 5 branches there is no grep pin; a future edit could restore the generic non-stall continuation before self-review.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_7: Design reference still describes degraded-empty-collector as unreviewed bypass only
- **Description**: Design reference still describes degraded-empty-collector as unreviewed bypass only. Scenario: `plan-review.md` still frames `degraded-empty-collector` as a Gate B bypass outcome with zero successful collectors, with no main-agent self-review step. Implementers loading this lazy reference may miss the new Step 3 prompt contract even after `skills/design/SKILL.md` is updated.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/references/plan-review.md:62-65
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_8: Usage table still documents external conflict-resolution panel
- **Description**: Usage table still documents external conflict-resolution panel. Scenario: After Phase 3 drops Codex/Cursor, the table row still lists Claude+Codex+Cursor for `/implement` Phase 3 conflict review. Operators reading only this doc will believe externals still launch, contrary to the issue acceptance criterion.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: docs/review-agents.md:97
- **Phase**: design




Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_9: Progress-reporting still mandates 3-reviewer conflict-review tables
- **Description**: Progress-reporting still mandates 3-reviewer conflict-review tables. Scenario: `progress-reporting.md` still instructs `/implement` Phase 3 conflict review to use the 3-reviewer `📊 Reviewers` table shape. After externals are removed, conflict-resolution progress breadcrumbs have no Codex/Cursor slots to report.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/progress-reporting.md:97-101
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

