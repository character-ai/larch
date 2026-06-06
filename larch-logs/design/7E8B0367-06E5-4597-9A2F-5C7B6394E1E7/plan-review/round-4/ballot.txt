### FINDING_1: Step 2b lacks rc 14 drift handling
- **Reviewer(s)**: Codex-Arch, Cursor-Edge
- **Severity**: important
- **Concern**: Initial Step 2b can receive `_postplan_rc=14` from `design-postplan-emit.sh`, but the thin fence is not specified to apply the Continue/Cancel drift semantics used by merged fences. This can make `/design` abort via the default arm instead of prompting on drift after a fix-and-retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the rc 14 branch to the initial Step 2b case arm too, parse DRIFT_* / BASELINE_* from .design-postplan-emit-result.env, prompt Continue / Cancel, and touch step-2b plus step-2b.5 on Continue
  - From Cursor-Edge: Add Step 2b `On _postplan_rc=14` prose mirroring merged fences: parse `DRIFT_*` / `BASELINE_*` from `.design-postplan-emit-result.env`, `AskUserQuestion` Continue/Cancel, touch `.completed/step-2b.5` on Continue, cancel summary on Cancel; keep the thin-fence `14)` arm non-falling-through.

### FINDING_2: Validator override path may skip drift baseline creation
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Concern**: If `design-postplan-emit.sh` exits for validator defects before plan-size runs, then the standalone retained Step 2b.5 Override path can proceed without ever writing `drift-baseline.env`, disabling later cumulative drift checks for that run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: On the Step 2b validator Override path, have the first successful retained Step 2b.5 plan-size parse write drift-baseline.env once, or pass an explicit initial-baseline mode to the retained handler before drift comparisons run

### FINDING_3: Step 3 review harness still pins removed LOOP_STATUS values
- **Reviewer(s)**: Codex-Edge, Codex-Innovation
- **Severity**: important
- **Concern**: The plan removes statuses such as `revision-failed` from the Step 3 review loop but omits updates to the Makefile-covered `test-run-step3-review.sh` harness, which still expects those deleted statuses and will fail or force retained behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add skills/design/scripts/test-run-step3-review.sh to the plan and update this case for the reduced enum, e.g. assert removed statuses normalize to panel-failed or replace it with a complete-plus-rc warning case
  - From Codex-Innovation: Add test-run-step3-review.sh to the plan and rewrite/delete cases for removed statuses so the harness asserts only the reduced enum plus cap-reached

### FINDING_4: Drift baseline parsing lacks invalid-value safeguards
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: A malformed or partially written `drift-baseline.env` can leave missing or non-numeric `BASELINE_*` values; arithmetic under `set -e` may then crash Step 2b.5 instead of treating drift as false/no-baseline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Specify non-negative integer validation for both baseline keys before arithmetic and treat invalid or incomplete baseline files like absent baseline; preferably write drift-baseline.env via an atomic temp+mv helper that refuses symlink targets

### FINDING_5: Drift baseline can be overwritten on re-emit
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Baseline writing lacks an explicit write-once guard, so a later successful re-entry to `--with-plan-size --snapshot-original` can overwrite `drift-baseline.env` and reset the drift anchor, weakening later drift detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `[[ ! -f "$DESIGN_TMPDIR/drift-baseline.env" ]]` (or equivalent) before the first write; align `design-postplan-emit.md` with the test contract "baseline not overwritten on re-emit"

### FINDING_6: Retained docs still reference removed Step 3 handoff statuses
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The plan removes post-apply `plan-review-loop` statuses but leaves retained Step 2b.5 caller prose for Step 3 `plan-size-trigger` and plan-review-loop handoffs, creating conflicting runtime/operator guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add explicit plan bullets to remove Step 3 plan-size-trigger and plan-review-loop retained-caller references from SKILL.md, flags.md, approval-gates.md, check-plan-size.md, and design-postplan-emit.md while keeping only truly retained callers like validator Override

### FINDING_7: Single-pass plan-review-loop exit mapping drops terminal status logic
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Collapsing review to one pass may bypass existing multi-round terminal status handling for tally errors and zero accepted findings, causing incorrect `complete` status and breaking rollback/bypass routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In plan-review-loop.sh single-pass exit after _run_plan_review_round: call _count_collector_evidence; then in order handle main-agent-vote-required; tally-error; ACCEPTED_COUNT=0 with collect_ok_count=0 → degraded-empty-collector; ACCEPTED_COUNT=0 with DEGRADED_PANEL=1 → zero-findings-degraded-panel; else complete. Do not use a bare findings-present → complete rule

### FINDING_8: Broader manual and multi-round harness updates are omitted
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Beyond the Step 3 harness, direct tests still pin removed manual and inner multi-round contracts, including manual flags/schema and old LOOP_STATUS values, so lint/direct targets may fail after the removals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add these harness updates to the plan: remove or rewrite manual-flag assertions, update schema expectations, replace multi-round expectations with the reduced single-pass status set, and keep only stale manual_gate_b ignored-behavior assertions where needed

### FINDING_9: Drift trigger OR rule is underspecified
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The drift guard requires triggering when either the plan body ratio or diff estimate ratio exceeds the configured multiple, but the plan does not explicitly specify the OR combine rule, leaving room for an incorrect AND or arbitrary implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Document and implement DRIFT_TRIGGER_FIRED=true when DRIFT_PLAN_RATIO > LARCH_DESIGN_DRIFT_MULTIPLE OR DRIFT_DIFF_RATIO > LARCH_DESIGN_DRIFT_MULTIPLE (after zero-baseline handling)

### FINDING_10: SECURITY.md not updated for removed auto-revision surface
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Removing `plan-review-loop` auto revision via `revise-plan-with-waterfall.sh` changes security-relevant behavior, but the plan omits `SECURITY.md`, leaving consumers/auditors with stale documentation about LLM-authored patch application.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add SECURITY.md to the plan and revise this section to state that Step 3 no longer invokes revise-plan-with-waterfall.sh, noting any retained legacy/orphaned helper and whether revise/ log allowlisting remains only for historical or follow-up cleanup purposes
