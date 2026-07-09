### FINDING_1: [OUT_OF_SCOPE] Live-registry stall cache coverage gap
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-step5-cache
- **Severity**: minor
- **Concern**: The live-registry test path still lacks a non-complete cached result env fixture, so it does not prove the clear-before-wait branch for stall or other non-complete envelopes beside a live registry row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a fixture that seeds a stall result env, asserts it is removed, and still rejoins via `bgjob wait` without a second daemon launch.
  - From cursor-specialist-edge-cases: Add a live-registry fixture seeded with `seed_zero_rc_stall_result_env` that asserts cache removal and `bgjob wait` rejoin
  - From dyn-dyn-step5-cache: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Branches contract and structure ratchet still allow BGJOB_RC=0 reuse
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-step5-cache
- **Severity**: minor
- **Concern**: The branches reference and the structure ratchet still describe cached reuse as allowed when `BGJOB_RC=0` plus required keys are present, without requiring `STEP5_REVIEW_STATUS=complete`. That leaves the written contract stale relative to `step-5-review.md` and the tightened classifier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align the sentence with `step-5-review.md` so reusable cached completion explicitly requires `STEP5_REVIEW_STATUS=complete`.
  - From cursor-specialist-edge-cases: Update the reuse sentence to require `BGJOB_RC=0 STEP5_REVIEW_STATUS=complete` and all required Step 5 KVs
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-step5-cache: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Canonical-stall fixture never exercises done-stall wait output
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: canonical-stall-result sets done-stall wait mode but fresh-starts without calling wait. done-stall mock wait output is never exercised in the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pre-existing; add a separate test if terminal stall wait consumption needs coverage.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Missing stale-classification test for missing required keys
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No test for complete status with a missing required key classifying as stale. Plan edge case relies on code review rather than harness enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Pre-existing; add seed_complete_missing_key fixture if desired.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_6: Step-5 reuse is too narrow for other terminal statuses
- **Reviewer(s)**: dyn-dyn-step5-cache
- **Severity**: major
- **Concern**: The tightened predicate fixes `STEP5_REVIEW_STATUS=stall` misclassification, but it over-narrows reusable terminal envelopes to only `complete`. `review-and-fix step5` exits `0` with several other terminal statuses, and those envelopes include the full required key set. On wrapper re-entry with no live registry row, they now classify as `stale` and fall through to a fresh `bgjob start` instead of the cached `bgjob wait` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step5-cache: Keep the explicit `stall` branch, but treat reuse as an allowlisted terminal set (at minimum `complete` and `cap-hit`, plus the Step 5 handoff statuses that exit `0`), or rename the shell state to something like `reusable` and document the exact set; add harness cases that seed `BGJOB_RC=0` with `STEP5_REVIEW_STATUS=cap-hit` (and one handoff status) and assert `bgjob wait` reuse without `bgjob-start-argv.txt`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: [OUT_OF_SCOPE] SKILL.md does not describe the tightened Step 5 cache contract
- **Reviewer(s)**: dyn-dyn-step5-cache
- **Severity**: minor
- **Concern**: The orchestrator prose still does not spell out the complete-only cached-reuse vs stall-clearing contract that `step-5-review.md` now documents. That mismatch predates this branch but is wider after the classifier change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-step5-cache: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

