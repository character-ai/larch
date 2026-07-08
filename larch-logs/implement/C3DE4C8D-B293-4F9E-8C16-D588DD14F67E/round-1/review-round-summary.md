# Review Round 1

- Mode: `diff`
- 1 accepted, 3 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Legacy DONE recovery is missing for stalled summaries
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The stalled-summary reconciler does not recover legacy bare `DONE` outcomes when the heading is stalled, so a committed summary with no state rows stays stale instead of being rewritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


