### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Gate C clean path missing assessed-clean branch
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Gate C’s invariant persist flow is missing an assessed-clean branch, so non-empty invariants can fail to persist after the assessment reports no violations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Invariant remediation counter is documented in the wrong section
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The invariant remediation counter prose is placed under guideline persist bullets instead of the invariant assessment section, which can let remediation loops proceed without the counter being read or incremented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** dismissed (0 YES)

### FINDING_6: Summary rerendering can leave stale warning blocks in place
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The summary prefixer only adds missing warnings, so rerenders can leave stale invariant text in the file or reorder invariant and guideline warnings incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_7: Approved-partition publish path is not exercised end-to-end
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The approved-partition plan test stops at the helper and never calls `publish_core`, so a publish wiring regression could pass while the isolated helper test still succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a publish_core integration test for approved-partition refusal with full rc/KV assertions.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Symlinked assessment artifacts are not covered on the publish path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Symlinked assessment artifacts are rejected, but the publish path does not have regression coverage for that case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add publish tests for symlink artifacts and absent/invalid invariant states mirroring guideline coverage.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Dry-run invariant warnings lack regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The new dry-run invariant-warning code has no regression test, so warning-path regressions could reach production unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Extend dry-run tests with invariants present and assert warning marker plus execution-issues output.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Approved-partition and invalid invariant states still lack parameterized test coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The new invariant test coverage still leaves the plan-required approved-partition refusal and invalid, absent, and present-empty invariant states unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add parameterized publish and run-log tests for approved-partition, invalid, absent, and present-empty invariant states, and assert the refusal/KV behavior for the partitioned case.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

