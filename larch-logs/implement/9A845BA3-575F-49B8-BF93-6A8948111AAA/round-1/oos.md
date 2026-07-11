### OOS_1: [OUT_OF_SCOPE] Classification omits recovery publish metadata
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The classifier does not copy validated `PR_URL` and `RECOVERY_BRANCH` from terminal publish-tail state into the classification artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_2: [OUT_OF_SCOPE] Salvage proof does not bind results to the current publish attempt
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Salvage proof ignores `PUBLISH_ATTEMPT_ID`, allowing stale or corrupt result state to theoretically satisfy reconciliation gates. The proof should require a matching current-attempt identifier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### OOS_3: [OUT_OF_SCOPE] Early rc-5 returns lack initialized result state
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Early rc-5 pre-check returns do not initialize fresh result state, leaving no current-attempt progress for diagnostics or classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
