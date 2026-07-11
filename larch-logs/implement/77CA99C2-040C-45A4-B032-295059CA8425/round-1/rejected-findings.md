### [rejected] FINDING_3

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_3: Reject duplicate and malformed invariant identity sidecars
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: First-wins sidecar parsing accepts duplicate or malformed identity data. A valid first `STEP` followed by a conflicting value can pass validation, weakening fail-closed stale-identity protection. Use strict exact-key parsing that rejects duplicates, malformed rows, control characters, and unexpected keys.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_10: Expand wrapper and lane integration coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Acceptance coverage is incomplete beyond the stale test: multi-tier `retry-next-tool` after a `HEAD` change, scope-aware run selection, stale identity rejection, exhaustion, route selection, waterfall retry, and transcript isolation are not exercised. Shell checks and smoke tests do not verify the actual start/finalize lifecycle or lineage progression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_12: Make finalize idempotent
- **Reviewer(s)**: dyn-dyn-bgjob-lineage
- **Severity**: major
- **Concern**: Repeating `--finalize --step "$STEP"` appends another lineage row for the same attempt and tier. Duplicate wakeups or operator re-drives can inflate the next attempt and desynchronize tier progression from actual fixer work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-lineage: Before appending, check for an existing row matching `ATTEMPT`, `TIER`, `STEP`, and `STARTING_HEAD`, or write a `.completed/ci-fixer-finalize-<step>` sentinel and treat a repeat finalize as a no-op that re-emits the same compact `RESULT` envelope.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (0 YES)

### FINDING_13: Extend the wrapper harness beyond smoke checks
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `test-step-8-ci-fixer.sh` checks string presence but does not exercise start/finalize behavior, scope routing, lineage handling, or failure cases. Fixture-driven lifecycle scenarios are needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
