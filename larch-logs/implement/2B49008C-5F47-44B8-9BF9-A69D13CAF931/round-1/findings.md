### FINDING_1: cancelled-clarify renderer-fail fallback markers are under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cancelled-clarify renderer-fail subcase does not assert the degraded banner, fallback HTML marker, or placement. A regression that emits fallback markers only for approved outcomes could pass current approved-path checks while breaking cancelled fallback summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: duplicated fallback banner and marker literals may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The design and implement fallback composers duplicate identical degraded banner and HTML marker literals. One-sided future edits could make the fallback contract diverge between surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: implement schema-order helper omits degraded banner ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `assert_schema_ordered` does not include the degraded banner between the heading and `Outcome`, so banner-after-Outcome ordering could pass if the separate placement block were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] pre-existing fallback composer duplication
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: The broader near-duplicate `compose_self_fallback` bodies predate this change and increase maintenance cost beyond the new banner and marker literals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] cancelled-outline fallback marker and cancel-site ordering is under-tested
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The cancelled-outline renderer-fail path is not covered for fallback marker ordering before the Cancel site bullet. Existing success-path checks cover rich rendering only, so fallback-only ordering regressions could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: design fallback marker ordering is not explicitly asserted
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The design harness checks marker presence but not that the run-summary marker precedes the final-summary-fallback marker, so swapped printf order could pass design-side tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: verify-run-log fixtures do not exercise degraded final-summary placement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Integration fixtures for verify-run-log or audit-scan consumers do not cover a final summary with heading followed by degraded banner, leaving placement regressions caught only by skill-specific harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] pre-publish renderer-failure fallback path is not covered
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The pre-publish-only renderer-failure path lacks fallback assertions, so it could diverge from post-publish behavior without detection. The plan scoped assertions to post-publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Bash 3.2 harness does not assert fallback contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Bash 3.2 harness only checks pass behavior and does not assert the new fallback banner or marker contract under renderer failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] design RUN_ID validation may permit sentinel-disrupting session IDs
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `RUN_ID` is taken from `SESSION_ID` without the documented sentinel-reader charset gate, so malformed values such as embedded newlines could disrupt heading and marker placement invariants. This is described as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] fallback output still exits successfully for machine consumers
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Fallback paths still exit 0, so callers that check only exit code and non-empty `final-summary.md` may treat degraded output as successful. The change improves human-visible signaling but does not add a hard machine gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] substring-only fallback detection could false-positive on appended notes
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Notes appended after `compose_self_fallback` could theoretically contain fallback banner or marker substrings, making substring-only greps unreliable. Placement-aware detection would avoid false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: design fallback banner may claim a warning was recorded when warning append failed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The banner text unconditionally says a warning was recorded, but `append_render_warning` can no-op if its helper is missing or fails, producing a degraded summary that may still show `Warnings: 0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] unrelated readability commit increases PR surface
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Commit `c990683f` is unrelated to the #3053 plan. It does not affect plan fidelity, but it broadens the PR beyond the planned feature scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
