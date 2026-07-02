### OOS_1: [OUT_OF_SCOPE] Fenced voter template still uses the wrong OOS heuristic
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The fenced OOS guidance in `skills/shared/voting-protocol.md` still uses a concrete-or-important heuristic instead of the canonical materiality gate, so copied instructions can diverge from the runtime rubric.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Severity rubric assertions are too shallow
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The severity rubric tests only check prefix substrings, so wording can drift while the tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

