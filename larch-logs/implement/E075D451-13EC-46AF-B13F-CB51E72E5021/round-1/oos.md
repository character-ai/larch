### FINDING_1: [OUT_OF_SCOPE] Stale re-entry cleanup can still expose legacy bgjob results
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: On `.step3-reentry`, cleanup can clear the direct bgjob result envs but still leave a legacy `.step3-review-result.env` / downstream result-env fallback reachable long enough for `normalize-status` to reuse the prior round's next action before fresh merge input is recreated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Clear legacy merge envs in `_step3_clear_downstream_sentinels()` or disable legacy fallback while `.step3-reentry` is present.
  - From cursor-specialist-plan-fidelity-auto: Add both `bgjob/*.result.env` paths to `_step3_clear_downstream_sentinels()` with `missing_ok=True`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] Review provenance should not trust mutable status without plan fingerprinting
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: `review_provenance()` can still authorize a publish from mutable review status plus `.completed/step-3` state even after the plan body changes, so a stale review verdict could be paired with a revised plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add plan-content fingerprinting to review_provenance as defense-in-depth (explicitly out of scope for this PR).
  - From cursor-specialist-edge-cases: Bind plan content hash in review_provenance() or compare snapshot-pre-review to current plan.txt before publish.
  - From cursor-specialist-testing: Add plan fingerprinting to review_provenance() if defense-in-depth is desired later.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Pause hygiene is missing during re-entry before publish
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: When `.step3-reentry` is set, pause publishing can snapshot stale downstream bgjob state unless the direct-review pause hygiene step runs first.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Call plan-review step3-state --direct-review-pause-hygiene before pause publish when .step3-reentry exists.
  - From cursor-specialist-plan-fidelity-auto: Call plan-review step3-state --direct-review-pause-hygiene before pause publish when .step3-reentry exists, matching the retired shell ordering.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Re-entry cleanup lacks integration proof of STARTED handoff
- **Reviewer(s)**: cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: minor
- **Concern**: There is no harness or integration case proving that seeding stale bgjob env on `.step3-reentry` still yields a fresh `BGJOB_STATUS=STARTED` handoff, so launcher/rejoin behavior can regress without a failing test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add an integration case: seed stale bgjob env, run step3-state --direct-review-entry with .step3-reentry, then assert wrapper emits BGJOB_STATUS=STARTED.
  - From cursor-specialist-plan-fidelity-auto: Optional follow-up: a harness asserting entry-state cleanup plus launcher stdout `BGJOB_STATUS=STARTED`.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Noop direct-review-entry test should assert result-env preservation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The noop pause-hygiene test seeds bgjob result envs but does not assert that they remain untouched, so a mistaken clear on the noop path would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Mirror the assertions in test_step3_state_direct_review_entry_noop_without_reentry for both result env paths.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

