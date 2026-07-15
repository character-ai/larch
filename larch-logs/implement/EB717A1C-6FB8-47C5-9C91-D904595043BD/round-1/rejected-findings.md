### [rejected] FINDING_1

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_1: Strict-stale mode omits active findings
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: In strict-stale mode, `StrictStaleError` is raised before active findings are returned or printed, so newly introduced violations are omitted alongside stale warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (0 YES)

### FINDING_12: Multi-row baseline rewrite coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: No-op baseline rewrite coverage uses only one synthetic row and may miss ordering or reason-preservation regressions in the committed multi-row schema.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
