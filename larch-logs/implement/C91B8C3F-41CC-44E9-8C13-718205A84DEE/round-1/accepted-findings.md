### FINDING_4: Attestation-only aggregate success lacks review-core coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `review-core` lacks an integration test for `REASON=ok` with `MERGED_COUNT=0`, so wrapper-level regressions could still exit incorrectly or skip/mis-order voters even while aggregate unit tests pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Missing execution-issues assertion for nonconforming heading with attestation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The `nonconforming_heading_with_attestation` case does not assert the expected `execution-issues.md` warning, so the new warning branch could break without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


