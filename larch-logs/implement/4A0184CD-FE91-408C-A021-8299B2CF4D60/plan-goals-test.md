## Goal
Implement issue #6649: [IMPLEMENTING] [OOS] [OUT_OF_SCOPE] step5 result-env classifier mislabels stall as complete.

## Implementation Plan
## Plan

### Context

- `approach-synthesis.txt` is `NO_SKETCHES`; this plan is based on direct repo inspection.
- The approved outline has no open questions.
- Confidence: high. The bug is localized and directly visible in `step5_canonical_result_env_state`.

## Approach

Tighten the cached Step 5 result classifier from "any non-empty status with `BGJOB_RC=0`" to "explicit `STEP5_REVIEW_STATUS=complete` with `BGJOB_RC=0`."

Keep existing stall handling unchanged:
- `STEP5_REVIEW_STATUS=stall` plus required keys still classifies as `stall`.
- Cached stall envs still clear before fresh launch when no live registry exists.
- Live registry rejoin still clears non-complete cached result envs before waiting.

## Files to modify/create

### UPDATED: skills/implement/scripts/step-5-review.sh

Change the complete predicate in `step5_canonical_result_env_state`:

- Replace `status and required_keys.issubset(rows)` with `status == "complete" and required_keys.issubset(rows)`.
- Leave the next `status == "stall"` branch intact.
- Do not alter the live-registry clearing path.

### UPDATED: skills/implement/scripts/test-step-5-review.sh

Add a focused regression case for a cached stall envelope with `BGJOB_RC=0`.

Recommended shape:
- Add a helper such as `seed_zero_rc_stall_result_env`, or parameterize `seed_stall_result_env`.
- Seed all required Step 5 keys, with:
  - `BGJOB_RC=0`
  - `STEP5_REVIEW_STATUS=stall`
  - `FINAL_REVIEW_AND_FIX_STATUS=stall`
- Run the wrapper with `STEP5_REGISTRY_MODE=missing`.
- Assert stdout is the fresh bgjob start line.
- Assert `bgjob-start-argv.txt` exists.
- Assert `bgjob/implement-step5-review.result.env` was removed before the fresh start.

Place the case near the existing `canonical-stall-result` test so both cached-stall paths are reviewed together.

### MAY_UPDATE: skills/implement/scripts/step-5-review.md

Only update this if the implementer finds the current prose remains ambiguous after the code change.

If changed, clarify that reusable cached completion requires:
- `BGJOB_RC=0`
- `STEP5_REVIEW_STATUS=complete`
- all required Step 5 keys

Do not broaden the docs beyond this classifier contract.

## Edge cases

- A complete env missing one required key must still classify as `stale`.
- A stall env with all required keys and non-zero `BGJOB_RC` must still classify as `stall`.
- A stall env with all required keys and `BGJOB_RC=0` must now classify as `stall`, not `complete`.
- Symlink and non-regular result env checks must remain fail-closed.

## Failure modes

- If the predicate only checks `status != "stall"`, an unexpected future status could still reuse a cached env. Use exact `status == "complete"`.
- If the test omits required keys, it may pass through the stale path rather than proving the stall classifier path.
- If the test reuses `STEP5_WAIT_MODE=done-stall` as the assertion source, it may mask whether the wrapper fresh-started. Assert `bgjob-start-argv.txt` and exact fresh-start stdout.

## Testing strategy

Run focused checks only:

1. `bash -n skills/implement/scripts/step-5-review.sh skills/implement/scripts/test-step-5-review.sh`
2. `bash skills/implement/scripts/test-step-5-review.sh`
3. `make test-step-5-review`

If docs are updated, also run the relevant markdown/lint target only if available in the changed-file workflow.

## Acceptance

Run focused checks only:

1. `bash -n skills/implement/scripts/step-5-review.sh skills/implement/scripts/test-step-5-review.sh`
2. `bash skills/implement/scripts/test-step-5-review.sh`
3. `make test-step-5-review`

If docs are updated, also run the relevant markdown/lint target only if available in the changed-file workflow.

diff_added: 24
diff_deleted: 1
mechanical_churn: false
diff_lines: 25

## Test plan
(no test plan section in plan-file)
