### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Duplicate terminal-state keys are accepted
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Terminal-state parsing accepts duplicate keys and silently uses the final value. A contradictory publish-tail state can therefore be overwritten and upgraded to a recoverable-looking state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: Tail-copy I/O failures are swallowed
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Tail-copy read or atomic-write failures are swallowed and converted to an empty tail. Temporary captures are then deleted without preserving the diagnostic or recording a durable execution issue, leaving terminal failure reporting without the original evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: Nested diagnostics and exception-mapped rc-5 paths lack lifecycle coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Lifecycle tests do not cover nested rename or log-publish stderr when outer Step 5c stderr is empty, nor exception-mapped rc-5 behavior through `step5c_core`. Nested subprocess diagnostics and status persistence can regress without preserving useful failure detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_6: Invalidation failure and stale rc-4 retry paths lack tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: minor
- **Concern**: Focused tests are missing for invalidation failure and two-attempt stale rc-4 invalidation/retry behavior. Regressions could reintroduce stale refusal state or misclassify a recoverable retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Reconciliation failure, deduplication, and close-verification paths lack coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Reconcile-failure retry, deduplication safety, and close-verification mismatch behavior are missing or unreachable in the salvage tests. These paths remain unproven even after the fixture issue is corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_8: Required publish-tail and reconciliation tests are missing from shard assignments
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `python/shard-assignments.json` still contains a renamed or removed publish test and omits new publish-tail tests. Shard CI may skip, misassign, or fail artifact-cleanliness checks for the new coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Log-merge failure exit-code contract lacks a main-level regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `design_log_ship.main` now returns rc 1 on merge failure, but tests cover only the success rc 0 path. Callers branching on the exit code lack coverage that failure returns rc 1 and persists `PUBLISH_OK=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
