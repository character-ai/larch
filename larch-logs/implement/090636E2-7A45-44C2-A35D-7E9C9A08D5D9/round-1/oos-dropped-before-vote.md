### OOS_1: [OUT_OF_SCOPE] Legacy staged/pin CLI verbs still registered
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Legacy staged/pin CLI verbs are still exposed in dispatch even though staging has been retired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Mark legacy or remove from dispatch table per plan follow-up.

### OOS_2: [OUT_OF_SCOPE] note_fingerprint_stale not wired into live path
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: note_fingerprint_stale is not wired into the live compose path, creating maintenance ambiguity about stale-note handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Wire into consumability or remove if intentionally retired.

### OOS_3: [OUT_OF_SCOPE] Final report still documents stale-fingerprint behavior
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Tests still document rendering notes when the fingerprint is stale but HEAD matches, which is only documentation unless fingerprint-aware consumability is intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Keep as documentation or align tests once consumability includes fingerprint.

### OOS_4: [OUT_OF_SCOPE] Closeout durable-note read tests missing
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Closeout lacks tests for reading consumable versus non-consumable durable notes after pin removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add tests for consumable vs non-consumable durable note at closeout.

### OOS_5: [OUT_OF_SCOPE] Redaction test still uses staged-pin path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The redaction-failure test still exercises the staged-pin alias instead of the compose-time load/write flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Rewrite test against load_or_prepare_guidelines_note / write_compose flow.

### OOS_6: [OUT_OF_SCOPE] Compose helper unit tests still missing
- **Reviewer(s)**: dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: The planned compose-helper unit tests were not added on the out-of-scope branch, so regressions in the core helpers remain unpinned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-compose-gate: Add the planned prepare_compose and write_compose_assessment test matrix from the implementation plan.

### OOS_7: [OUT_OF_SCOPE] Moved-base acceptance test still not end-to-end
- **Reviewer(s)**: dyn-dyn-compose-gate
- **Severity**: important
- **Concern**: The moved-base acceptance test still does not drive the real compose-time end-to-end path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-compose-gate: Add a full run_ship integration test with moved origin/main, guidelines-assessment handoff, compose write, relaunch, and PR-body note assertion.

