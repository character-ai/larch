### FINDING_16: [OUT_OF_SCOPE] ship-pr file size concentrates CI recovery logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `ship-pr.sh` has accumulated substantial CI recovery logic, increasing long-term maintenance cost as more CI jobs or recovery modes are added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] Per-job path still runs relevant-checks before push
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The per-job path still runs relevant-checks before pushing, so remote-only job failures can remain possible even after local per-job verification succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_18: [OUT_OF_SCOPE] Outer retry clears bail metadata between attempts
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: Each outer `_fix_attempt` clears `BAIL_REASON` and `BAIL_FAILURE_DETAIL_LOG` before re-running `ci-failed-jobs.sh` against the same run. This matches current verification-retry tests, but partial local fixes persist across attempts and may matter if vendor and per-job paths interact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_19: [OUT_OF_SCOPE] Graceful degrade for ci-failed-jobs failures is wired correctly
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: `run_evaluate_failure` graceful degrade when `ci-failed-jobs.sh` returns `1` or `3` records a warning and runs vendor recovery as expected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_20: [OUT_OF_SCOPE] Branch commit list is informational
- **Reviewer(s)**: dyn-per-job-loop-states-output.txt
- **Severity**: nit
- **Concern**: The reviewer reported the branch commits since `main`: `84c246ae`, `7bbd2199`, and `671dc47f`. This is contextual metadata, not a code finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-per-job-loop-states-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

