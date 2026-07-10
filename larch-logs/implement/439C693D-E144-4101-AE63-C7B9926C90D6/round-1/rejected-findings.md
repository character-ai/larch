### [rejected] FINDING_5

**Rejected subtype:** dismissed (0 YES)

### FINDING_5: Step 5c retry lookup depends on the ambient working directory
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Registry lookup keyed by the current working directory can miss a live Step 5c job when re-run from another directory, causing the result environment to be cleared and a second concurrent job to launch. The launcher should resolve persisted run identity independently of the ambient directory and fail closed when identity is unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Step 5c stale-result regression coverage is not reached by CI
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The Step 5c stale-result regression test is not wired into the test-harness CI shard, so CI can pass even if stale terminal result rejoining is reintroduced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** dismissed (0 YES)

### FINDING_11: Step 5c tests do not cover live-registry rejoin behavior
- **Reviewer(s)**: dyn-dyn-bgjob-recovery
- **Severity**: major
- **Concern**: The Step 5c harness covers stale results with an absent registry but does not simulate live registry entries. It therefore does not guard against regressions in live-plus-stale recovery or live rejoin without a second job start.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-recovery: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
