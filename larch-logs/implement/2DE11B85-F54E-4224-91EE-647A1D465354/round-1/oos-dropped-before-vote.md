### OOS_1: [OUT_OF_SCOPE] relevant-check dispatch omits marker launcher files
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: latent
- **Concern**: Relevant-check wiring omits runtime launcher files that arm bg-wait markers, so incremental `checks run-relevant` can miss marker-plumbing regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.

