### FINDING_2: [OUT_OF_SCOPE] Legacy start lock coordination
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The adapter’s decision lock is not shared with legacy `bgjob start` callers, allowing concurrent registry writes for the same run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_3: [OUT_OF_SCOPE] Consumer liveness-policy drift
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-process-ownership
- **Severity**: minor
- **Concern**: Existing step scripts retain divergent child/daemon liveness policies, so production behavior remains inconsistent until consumer migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-process-ownership: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Corrupt-registry recovery
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Malformed registry entries fail closed without stale clearing, leaving operators to manually remove the corrupt registry entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Global fork-handler side effect
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Importing the adapter registers a global at-fork handler that affects unrelated later forks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Reap and adapter liveness disagreement
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-process-ownership
- **Severity**: minor
- **Concern**: Existing reap/registry helpers treat child-only liveness as live, contrary to the adapter’s daemon-only ownership policy, allowing disagreement after migration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-process-ownership: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_19: Completed results are not bound to `run_id`
- **Reviewer(s)**: dyn-dyn-process-ownership
- **Severity**: major
- **Concern**: A completed result keyed only by temporary directory and step can be consumed as `DONE` by a different run after registry removal, skipping a fresh launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-ownership: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_20: [OUT_OF_SCOPE] Fork-race regression test does not use the real daemon path
- **Reviewer(s)**: dyn-dyn-process-ownership
- **Severity**: minor
- **Concern**: The lock regression test stubs daemon startup with a bare fork and does not cover the real `start_daemon` fork and registry-publication window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-ownership: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
