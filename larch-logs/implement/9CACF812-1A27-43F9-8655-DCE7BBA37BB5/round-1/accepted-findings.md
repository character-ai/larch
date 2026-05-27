### FINDING_2: G7/Q2 test naming mismatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-merge-pr.md` refers to G7 while the harness subsection/assertions use Q2/Q2a-Q2d, making acceptance criteria harder to map to test output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_5: G7 ERROR assertion is too weak
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: G7 checks for `ERROR=` as a substring, so it could pass even if `MERGE_RESULT=main_advanced` is emitted with a non-empty `ERROR` value.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: G7 lacks pr view call-count assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: G7 does not assert the `gh pr view` call count, so the post-force-push UNKNOWN retry sequence could be skipped while stubs still produce `main_advanced` and one `pr checks` call.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


