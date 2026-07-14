### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Independent estimate is not enforced for threshold gates
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-proposal-contract
- **Severity**: major
- **Concern**: Thresholds use the self-reported Size budget even though the plan requires an independent estimate. An understated budget can suppress the 150-line justification and 400-line split or approval gates. The effective size must be independently recorded or mechanically derived, and all thresholds must use it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: Per-section prevention-field checklists are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-proposal-contract
- **Severity**: minor
- **Concern**: Section 4, Section 5 lint/hook proposals, and Section 7 regression-test proposals do not repeat the required Host, Size budget, and Cheaper alternative fields and their conditional requirements. Authors can therefore produce incomplete proposals while following the numbered checklists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_4: New-hook proposals lack a valid Host exception
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The Host definition permits a new module but not a necessary new hook, leaving truthful Section 5 hook proposals unable to satisfy the fail-closed contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (0 YES)

### FINDING_9: Regression-test Host semantics are undefined
- **Reviewer(s)**: dyn-dyn-proposal-contract
- **Severity**: minor
- **Concern**: Host is defined using lint, module, hook, or harness terminology but does not specify the appropriate target for test-only proposals. Cheaper alternative semantics are likewise undefined for regression tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-proposal-contract: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
