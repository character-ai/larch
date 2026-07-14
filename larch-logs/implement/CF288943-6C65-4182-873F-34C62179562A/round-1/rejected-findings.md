### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Assert `qualified_symbol` unconditionally
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: `qualified_symbol` is not compared when the expected value is null or omitted, allowing an adapter to drop the symbol while incomplete fixtures still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
