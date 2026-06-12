## Goal
Implement issue #4121: [IMPLEMENTING] [BUG] (URGENT) /design plan-processing defects: mechanical_churn integer silently bypassed + plan-review loop continues spuriously on empty tally.

## Implementation Plan
## Plan

Fix two `/design` plan-processing defects.

**Bug 1 — `mechanical_churn` integer silently bypassed**: `lib-plan-optional-trailers.awk` only matches `^mechanical_churn: (true|false)$`, so integer values (e.g., `35`) default to `false` with no warning. Fix: emit a stderr diagnostic from awk for invalid values; expose the invalid token through parse output; `check-plan-size.sh` validates the parsed value and exits 2 with `PLAN_SIZE_STATUS=invalid-mechanical-churn`.

**Bug 2 — plan-review loop continues spuriously on empty tally output**: when `INSCOPE_REMAINING > 0` but `findings-classification.tsv` is header-only, the current code treats this identically to a genuinely empty ballot — both surface as `TALLY_PLAN_REVIEW_STATUS=ok + ACCEPTED_COUNT=0 + DEGRADED_PANEL=0`. The fix detects the ballot-items-lost state, sets `DEGRADED_PANEL=1 + LOOP_REASON=ballot-items-lost`, threads the `REASON` signal through `run-step3-review.sh` and `review-design-step3-loop.sh`, and adds a dedicated continuation branch in `plan-review-continuation.sh`.

### UPDATED: `skills/design/scripts/lib-plan-optional-trailers.awk`

Detect `mechanical_churn:` present with non-boolean value. Emit `invalid-mechanical-churn: <value>` to stderr. Set `has_mech=1`. Expose parse output line 4 as `invalid:<value>` (not `false`). Keep `has_key` / `keys` / `values` modes working for invalid-but-present keys.

### UPDATED: `skills/design/scripts/lib-plan-optional-trailers.md`

Document invalid-value handoff: stderr diagnostic, `has_key` success, parse line 4 as `invalid:<value>`, `values` output as `mechanical_churn=invalid:<value>`. Clarify that only lowercase `true`/`false` are valid.

### UPDATED: `skills/design/scripts/check-plan-size.sh`

After `parse_plan_optional_metadata`, validate `mechanical_churn`. Accept only `true`/`false`. On any other value: emit `PLAN_SIZE_STATUS=invalid-mechanical-churn` and exit 2. Do not let invalid metadata silently fall back to `false`.

### UPDATED: `skills/design/scripts/check-plan-size.md`

Add `invalid-mechanical-churn` to the documented `PLAN_SIZE_STATUS` vocabulary. Document that invalid `mechanical_churn:` exits 2 before size-gate calculations.

### UPDATED: `skills/design/scripts/test-check-plan-size.sh`

Add regression: `mechanical_churn: 35` → assert exit 2, `PLAN_SIZE_STATUS=invalid-mechanical-churn`, stderr contains `invalid-mechanical-churn: 35`. Add parser coverage: parse line 4 is `invalid:35`, `has_key` succeeds. Add cases for `mechanical_churn: TRUE` and bare `mechanical_churn:`. Keep existing tests unchanged.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`

- Parse `INSCOPE_REMAINING` from `prune-nit.env` alongside `PRUNED_COUNT`.
- Persist `INSCOPE_REMAINING` to normalized stdout, `.step3-plan-review-result.env`, and `round-summary.env`.
- After tally + baseline `DEGRADED_PANEL` computation: if `TALLY=ok && INSCOPE_REMAINING>0 && TSV-header-only` → `DEGRADED_PANEL=1 + LOOP_REASON=ballot-items-lost`.
- In terminal zero-accepted mapping: do not overwrite `LOOP_REASON=ballot-items-lost`; default to `zero-findings-degraded-panel` only when reason is not already set.

### UPDATED: `skills/design/scripts/run-step3-review.sh`

Initialize `REASON=""`. Relay `REASON` from `plan-review-loop` stdout and `.step3-plan-review-result.env` (env preferred). Emit normalized stdout `REASON=`. Persist `REASON=` to `.step3-review-result.env`. Relay `INSCOPE_REMAINING` defaulting to `0`. Emit empty `REASON` for cap and unrelated terminal paths.

### UPDATED: `skills/design/scripts/review-design-step3-loop.sh`

Preserve `REASON` in the loop envelope. Merge non-empty `REASON` from `.step3-review-result.env` when in-memory value is blank. Write `REASON=` empty for clean later terminal rounds.

### UPDATED: `skills/design/scripts/plan-review-continuation.sh`

Read `STEP3_REASON` from `.step3-review-result.env`. Add branch before existing degraded-with-accepted check: when `STEP3_REASON=ballot-items-lost && ACCEPTED_COUNT==0 && DEGRADED_PANEL!=0 && TALLY=ok && LOOP_STATUS=zero-findings-degraded-panel` → `CONTINUE=true REASON=ballot-items-lost`. Keep stale-clear guard narrow: only clear when `TALLY=ok && LOOP_STATUS=complete`.

### UPDATED: `skills/design/scripts/plan-review-continuation.md`

Add `ballot-items-lost` to reason vocabulary. Document branch order. Clarify that degraded zero-accepted rounds continue only when the full lost-ballot terminal shape is present.

### UPDATED: `skills/design/scripts/plan-review-loop.md`

Add `INSCOPE_REMAINING` to `round-summary.env` schema and normalized Step 3 result KVs. Document ballot-items-lost detector and its mapping to `zero-findings-degraded-panel`.

### UPDATED: `skills/design/scripts/run-step3-review.md`

Add `REASON` to normalized stdout and `.step3-review-result.env`.

### UPDATED: `skills/design/scripts/review-design-step3-loop.md`

Add `REASON` to loop envelope carry-through KVs. Clarify clean-round empty-reason write.

### UPDATED: `skills/design/scripts/test-plan-review-loop.sh`

Add regression: non-empty ballot + header-only TSV → assert `DEGRADED_PANEL=1`, `LOOP_STATUS=zero-findings-degraded-panel`, `REASON=ballot-items-lost`, positive `INSCOPE_REMAINING` in `round-summary.env`. Add negative regression: `INSCOPE_REMAINING=0` + header-only TSV → no `ballot-items-lost`.

### UPDATED: `skills/design/scripts/test-run-step3-review.sh`

Add integration regression: stub `plan-review-loop.sh` to emit `REASON=ballot-items-lost` and write same to `.step3-plan-review-result.env`. Assert `run-step3-review.sh` normalized stdout and `.step3-review-result.env` contain `REASON=ballot-items-lost`.

### UPDATED: `skills/design/scripts/test-review-design-step3-loop.sh`

Add loop-envelope regression: assert envelope does not drop `REASON=ballot-items-lost`. Assert clean terminal envelope writes empty reason.

### UPDATED: `skills/design/scripts/test-step3-review-cap.sh`

Update lost-ballot continuation test to include full terminal shape (`TALLY=ok`, `LOOP_STATUS=zero-findings-degraded-panel`, `DEGRADED_PANEL=1`, `REASON=ballot-items-lost`). Assert `PLAN_REVIEW_CONTINUE=true REASON=ballot-items-lost`. Add negative regression for absent/non-ballot-items-lost reason. Keep stale-degraded stop test unchanged.

## Acceptance

- `bash skills/design/scripts/test-check-plan-size.sh` passes with new invalid-`mechanical_churn` cases.
- `bash skills/design/scripts/test-plan-review-loop.sh` passes with ballot-items-lost detection and negative regression.
- `bash skills/design/scripts/test-run-step3-review.sh` passes with `REASON` relay integration.
- `bash skills/design/scripts/test-review-design-step3-loop.sh` passes with envelope carry-through.
- `bash skills/design/scripts/test-step3-review-cap.sh` passes with updated and new continuation test.
- `bash scripts/relevant-checks.sh` passes clean.

diff_lines: 435

## Test plan
(no test plan section in plan-file)
