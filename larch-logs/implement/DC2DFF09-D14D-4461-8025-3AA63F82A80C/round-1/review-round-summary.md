# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_1: HTML-comment marker literals bypass ownership ratchet
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: The literal scan detects only bare `larch:plan:start/end` tokens, while `issue_wire` emits HTML-comment markers. Consumers can hardcode the emitted markers and bypass the ownership ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
