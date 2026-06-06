### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:912-970
- **Concern**: Initial Step 2b merged post-plan fence is not planned to handle new rc 14. Scenario: design-postplan-emit.sh --with-plan-size can now exit 14 at any merged site; a Step 2b fix-and-retry after a baseline exists would hit the default abort arm instead of the planned Continue / Cancel drift prompt
- **Proposed resolution**: Add the rc 14 branch to the initial Step 2b case arm too, parse DRIFT_* / BASELINE_* from .design-postplan-emit-result.env, prompt Continue / Cancel, and touch step-2b plus step-2b.5 on Continue

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:929-973; skills/design/scripts/design-postplan-emit.sh:515-520
- **Concern**: Baseline is not established when initial validator defects are overridden into standalone Step 2b.5. Scenario: design-postplan-emit exits 10 before plan-size, then Override runs retained Step 2b.5; because the plan only writes the baseline inside design-postplan-emit after plan-size, later drift checks see no baseline and silently disable the cumulative guard for that run
- **Proposed resolution**: On the Step 2b validator Override path, have the first successful retained Step 2b.5 plan-size parse write drift-baseline.env once, or pass an explicit initial-baseline mode to the retained handler before drift comparisons run

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:923-975
- **Concern**: Step 2b thin-fence lacks `_postplan_rc=14` Continue/Cancel semantics. Scenario: `design-postplan-emit.sh` can exit 14 on initial Step 2b (e.g. validator fix-and-retry re-entering `--with-plan-size --snapshot-original` with a larger plan). Plan only documents rc 14 handling under Merged Gate B / discussion fences; structure pins add case arm 14 but not handler prose. A stub `14)` arm or missing On `_postplan_rc=14` block falls through to the default `*` arm and aborts /design on drift.
- **Proposed resolution**: Add Step 2b `On _postplan_rc=14` prose mirroring merged fences: parse `DRIFT_*` / `BASELINE_*` from `.design-postplan-emit-result.env`, `AskUserQuestion` Continue/Cancel, touch `.completed/step-2b.5` on Continue, cancel summary on Cancel; keep the thin-fence `14)` arm non-falling-through.

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-run-step3-review.sh:552-561
- **Concern**: Reduced LOOP_STATUS plan omits the run-step3-review harness that still pins revision-failed. Scenario: The PR removes revision-failed from plan-review-loop/run-step3-review, but make lint runs test-run-step3-review and this case still expects LOOP_STATUS=revision-failed to survive rc 1, so the harness fails or pressures the implementation to keep a deleted status
- **Proposed resolution**: Add skills/design/scripts/test-run-step3-review.sh to the plan and update this case for the reduced enum, e.g. assert removed statuses normalize to panel-failed or replace it with a complete-plus-rc warning case

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:142-156
- **Concern**: Drift baseline contract does not cover malformed or partially written baseline values. Scenario: A crash or interrupted write can leave drift-baseline.env readable but missing or non-numeric BASELINE_* keys; a naive arithmetic comparison under set -e can abort Step 2b.5 instead of the promised no-crash drift false path
- **Proposed resolution**: Specify non-negative integer validation for both baseline keys before arithmetic and treat invalid or incomplete baseline files like absent baseline; preferably write drift-baseline.env via an atomic temp+mv helper that refuses symlink targets

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-postplan-emit.sh:176-188
- **Concern**: Drift baseline write lacks an explicit write-once guard. Scenario: Fix-and-retry on initial Step 2b re-enters `--with-plan-size --snapshot-original`; a second successful plan-size pass can overwrite `drift-baseline.env` and reset the anchor to a smaller pre-fix plan, weakening or disabling drift detection on later Gate B growth
- **Proposed resolution**: Add `[[ ! -f "$DESIGN_TMPDIR/drift-baseline.env" ]]` (or equivalent) before the first write; align `design-postplan-emit.md` with the test contract "baseline not overwritten on re-emit"

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-run-step3-review.sh:551-561
- **Concern**: Plan omits updating a Makefile-covered Step 3 harness that still expects removed LOOP_STATUS values. Scenario: make lint still runs test-run-step3-review; after run-step3-review rejects revision-failed/converged/cap-hit/plan-size-trigger, this stale case will fail or force keeping removed behavior
- **Proposed resolution**: Add test-run-step3-review.sh to the plan and rewrite/delete cases for removed statuses so the harness asserts only the reduced enum plus cap-reached

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:981-983; skills/design/references/flags.md:33-35; skills/design/scripts/check-plan-size.md:73-76
- **Concern**: Plan removes plan-review-loop post-apply statuses but leaves retained Step 2b.5 caller prose for Step 3 plan-size-trigger and plan-review-loop handoffs. Scenario: The runtime prompt/docs can still instruct operators to route through a removed status path, conflicting with the reduced LOOP_STATUS enum and single-pass Step 3
- **Proposed resolution**: Add explicit plan bullets to remove Step 3 plan-size-trigger and plan-review-loop retained-caller references from SKILL.md, flags.md, approval-gates.md, check-plan-size.md, and design-postplan-emit.md while keeping only truly retained callers like validator Override

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1703-1818
- **Concern**: Single-pass exit mapping does not port multi-round terminal status logic. Scenario: Production always passes --round-cap today so tally-error and ACCEPTED_COUNT=0 degradation only run in the multi-round tail; collapsing to one pass without porting lines 1780-1818 leaves tally-error as complete and skips degraded-empty-collector / zero-findings-degraded-panel, breaking run-step3-review.sh rollback and Step 3 bypass routing
- **Proposed resolution**: In plan-review-loop.sh single-pass exit after _run_plan_review_round: call _count_collector_evidence; then in order handle main-agent-vote-required; tally-error; ACCEPTED_COUNT=0 with collect_ok_count=0 → degraded-empty-collector; ACCEPTED_COUNT=0 with DEGRADED_PANEL=1 → zero-findings-degraded-panel; else complete. Do not use a bare findings-present → complete rule

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-parse-design-argv.sh:56-87,121-127; scripts/test-write-run-params.sh:48-56,85-100,167-210; scripts/test-step0b-router-flag-recovery.sh:22-60,117-125; skills/design/scripts/test-write-design-current-env.sh:37-60,222-268; skills/design/scripts/test-plan-review-loop.sh:1328-1804
- **Concern**: Plan removes manual and inner multi-round contracts but omits the direct harness updates that still pin them. Scenario: make lint or direct targets will fail after the proposed removals because tests still expect MANUAL_REQUESTED, --manual, --manual-gate-b, --manual-requested, manual_gate_b JSON, and LOOP_STATUS values like converged/cap-hit/revision-failed/plan-size-trigger
- **Proposed resolution**: Add these harness updates to the plan: remove or rewrite manual-flag assertions, update schema expectations, replace multi-round expectations with the reduced single-pass status set, and keep only stale manual_gate_b ignored-behavior assertions where needed

### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/check-plan-size.sh:155-179
- **Concern**: Drift-fire combine rule not specified. Scenario: Feature requires flag when plan body OR diff estimate exceeds the baseline multiple; without an explicit OR rule implementers may require both ratios to trip or pick an arbitrary rule
- **Proposed resolution**: Document and implement DRIFT_TRIGGER_FIRED=true when DRIFT_PLAN_RATIO > LARCH_DESIGN_DRIFT_MULTIPLE OR DRIFT_DIFF_RATIO > LARCH_DESIGN_DRIFT_MULTIPLE (after zero-baseline handling)

### FINDING_12:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:225-227
- **Concern**: Plan removes plan-review-loop auto revision via revise-plan-with-waterfall.sh but does not update SECURITY.md despite the repo instruction to update it for security-relevant behavior changes. Scenario: After the PR lands, SECURITY.md still says /design applies LLM-authored patches during the multi-round review loop, giving consumers and auditors a stale security model for a removed write surface
- **Proposed resolution**: Add SECURITY.md to the plan and revise this section to state that Step 3 no longer invokes revise-plan-with-waterfall.sh, noting any retained legacy/orphaned helper and whether revise/ log allowlisting remains only for historical or follow-up cleanup purposes
