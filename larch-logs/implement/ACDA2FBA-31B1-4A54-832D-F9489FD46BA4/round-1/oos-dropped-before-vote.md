### FINDING_3: Verification notes: coverage, CI wiring, baseline parity, and parser alignment
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The reviewer confirmed that the planned cases are covered, the lint target is wired through CI, the committed baseline matches live findings, and entry-boundary handling matches the parser; the only remaining note was residual untested defensive branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] baseline type error message is misleading
- **Reviewer(s)**: dyn-dyn-guideline-parser
- **Severity**: nit
- **Concern**: When a baseline array element is not a dict, the error text says the record must have exactly `['guideline_id', 'reason']`, so the message does not match the actual failure mode even though the exit code is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-guideline-parser: Address the concern above.

