# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_3: summary end should reflect the last selected snapshot
- **Reviewer(s)**: dyn-dyn-ledger-history
- **Severity**: important
- **Concern**: Summary `end` is derived from the last aggregated delta row rather than the last selected revision’s snapshot, so if a target disappears in the final selected commit the summary overstates the terminal value and delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-history: Address the concern above.


