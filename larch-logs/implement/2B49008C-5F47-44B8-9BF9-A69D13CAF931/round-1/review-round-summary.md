# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (3 exonerated)

## Accepted Findings

### FINDING_1: cancelled-clarify renderer-fail fallback markers are under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cancelled-clarify renderer-fail subcase does not assert the degraded banner, fallback HTML marker, or placement. A regression that emits fallback markers only for approved outcomes could pass current approved-path checks while breaking cancelled fallback summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: design fallback banner may claim a warning was recorded when warning append failed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The banner text unconditionally says a warning was recorded, but `append_render_warning` can no-op if its helper is missing or fails, producing a degraded summary that may still show `Warnings: 0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: design fallback marker ordering is not explicitly asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The design harness checks marker presence but not that the run-summary marker precedes the final-summary-fallback marker, so swapped printf order could pass design-side tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


