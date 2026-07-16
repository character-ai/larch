# Review Round 1

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Attribute evidence is broader than the semantic-member grammar
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Any name-rooted attribute is accepted as semantic status evidence, causing ordinary object/config attributes or attribute-to-attribute comparisons to trigger false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_4: BoolOp and `not` detection is limited to conditional tests
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: Same-scope `BoolOp` and `not` expressions outside conditional tests, including return and assignment expressions, are not linted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_5: Nested, local-class, and module-level function scopes are skipped
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Scope discovery omits nested or local-class methods and module-level control-flow functions, so qualifying violations are silently missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: `elif` handling lacks a targeted regression test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The documented `elif` flagged context is not covered by a detector regression test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
