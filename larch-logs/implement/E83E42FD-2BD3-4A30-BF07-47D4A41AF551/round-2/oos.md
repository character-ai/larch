### FINDING_1: Stale bgjob result env can short-circuit rejoin
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `skills/design/scripts/design-step3-review.sh` appears to rejoin on any existing bgjob result env file without checking completion KVs or registry liveness, so a crash-orphaned partial env can make waits return DONE immediately and keep retries stuck on stale output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_4: [OUT_OF_SCOPE] Step 3.5 still references the retired wait contract
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Step 3.5 continuation prose still references immediate-background/task-notification for `design-step3-review.sh`, which may mislead manual recovery toward the retired wait contract instead of bgjob wait/result-env parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Migrate Step 3.5 continuation prose in a follow-up chunk.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

