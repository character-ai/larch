### [rejected] FINDING_2

**Rejected subtype:** dismissed (0 YES)

### FINDING_2: cover mid-history first-seen targets
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: important
- **Concern**: The suite does not exercise a target that first appears in a later revision, so a regression could treat that first appearance as a raise or include it incorrectly in summary calculations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: empty filtered selections should be explicit
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: important
- **Concern**: When `--window` or `--since-tag` selects no baseline-touching commits, the command exits 0 and prints only the TSV header, which can be mistaken for a real no-growth result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

