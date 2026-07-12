### FINDING_1: [OUT_OF_SCOPE] completed-result race
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: A completed result can appear after the final verification and before `STARTED` is emitted, causing one invocation to report `STARTED` despite an already-published result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: call `_result_or_none` once more right before `_emit_started` if you want to close that window.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] legacy adapter locking
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The per-run/step lock serializes `bgjob adapt` only; legacy `bgjob start` callers can still race on the registry row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] both-dead fail-closed coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The in-budget case where both daemon and child identities are proven dead lacks regression coverage proving `registry-dead`, no unlink, and no restart.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] legacy liveness-policy divergence
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Legacy production step scripts still diverge on `and` versus `or` liveness policy until consumer migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_9: [OUT_OF_SCOPE] global atfork handler scope
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Import-time registration makes unrelated forks in the process run the child hook.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] completion is not run_id-bound
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: A stale result environment can produce a false `DONE` for a new run sharing the same temporary directory and step.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
