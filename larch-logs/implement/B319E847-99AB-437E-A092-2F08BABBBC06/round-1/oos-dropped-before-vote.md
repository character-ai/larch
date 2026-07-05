### OOS_1: [OUT_OF_SCOPE] missing timeout assertion in checks-only step-3 background marker test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The checks-only hook timeout could regress if the step-3 background wait marker test does not explicitly assert `TIMEOUT_S=10800`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] missing negative coverage for non-step-3 composite preserving step-3 sidecars
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: There is no negative test proving that a non-step-3 composite keeps step-3 sidecars intact; removing the `checks_site == step3` guard could delete artifacts on other composite sites without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] missing design-path regression test for keepalive import
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `design_core`’s keepalive import lacks a design-only regression test, so a design-path marker regression would not be isolated from implement helper coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
