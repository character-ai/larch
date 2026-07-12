### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Re-attach result race
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: A daemon can finish between the initial result check and `STARTED` emission, causing the adapter to emit `STARTED` instead of `DONE` until the next invocation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: CWD-dependent clone validation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Re-attach validates `clone_path` against the ambient working directory, so a changed CWD can block re-attachment to a live daemon.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Duplicate reserved result keys accepted
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Duplicate `BGJOB_RC` or `STEP` rows are accepted with last-value-wins semantics, allowing conflicting result data to be treated as valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Missing adapt subprocess end-to-end test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No subprocess test covers adapt launch, re-attach, daemon startup, and `DONE` output grammar together.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (0 YES)

### FINDING_14: Missing `result_env` identity-mismatch test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The test suite lacks a case proving that a registry entry with a foreign `result_env` path is rejected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (0 YES)

### FINDING_17: Fork releases the adapter lock during daemon startup
- **Reviewer(s)**: dyn-dyn-process-ownership
- **Severity**: major
- **Concern**: The daemon child closes the inherited `flock` descriptor after fork, potentially releasing the parent’s lock while startup is still blocked and allowing a concurrent adapter invocation to launch a duplicate daemon. Existing tests do not exercise the real fork path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-process-ownership: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
