### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: Missing runtime-before-entry regression assertion
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The harness checks that the plan-review runtime text exists, but not that its mandatory read precedes `design-step3-entry.sh`. The preview may therefore run before loading its runtime contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_5: Missing Step 3 preview contract pins
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The structure harness does not pin the Step 3 preview requirements in `plan-review-runtime.md`, including the Plan Candidate header, `--variant step3`, summary mode, and show-full-plan note. Preview behavior can drift without structural-test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (0 YES)

### FINDING_7: Degraded-empty-collector bypass remains duplicated in SKILL.md
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The degraded-empty-collector self-review bypass contract remains inline in `skills/design/SKILL.md` instead of being moved to `plan-review-runtime.md`, leaving duplicated runtime authority and reducing the intended lazy-load savings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (0 YES)

### FINDING_8: Harness documentation overclaims Gate A coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `scripts/test-design-structure.md` claims Gate A negative coverage that the harness does not currently provide, which can mislead maintainers about the available regression guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Orchestrator-fence harness lacks planned load-order and preview pins
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The Step 3 orchestrator-fence harness does not independently check runtime-before-entry ordering or the planned preview contract, leaving those regressions dependent on limited structure-test coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (0 YES)

### FINDING_10: Shared-core header misstates post-apply ownership
- **Reviewer(s)**: dyn-dyn-load-closure
- **Severity**: minor
- **Concern**: `approval-gates.md` still claims ownership of post-apply behavior even though its body no longer contains the Shared post-apply pipeline. The header therefore misrepresents the contract delivered by the shared core.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-load-closure: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
