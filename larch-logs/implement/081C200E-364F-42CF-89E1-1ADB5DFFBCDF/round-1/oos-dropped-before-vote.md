### OOS_1: [OUT_OF_SCOPE] Plan traceability gap for semantic-validation e2e coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The new semantic-validation test is validator-only and does not assert e2e `REASON=validation-failed` or ballot preservation required by the plan. Family regression could be misread as fully covered when only the validator helper is pinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add a small e2e stub-dispatch test or document this as intentional validator-only coverage atop existing e2e tests.

