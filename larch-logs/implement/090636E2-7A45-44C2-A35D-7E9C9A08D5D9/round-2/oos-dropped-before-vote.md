### OOS_1: [OUT_OF_SCOPE] final report still renders stale guidelines notes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Final report rendering can still show a note when fingerprint metadata is stale, so the closeout summary may disagree with compose freshness rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Pre-existing; PR compose path now validates fingerprint
  - From cursor-specialist-testing: Align closeout with compose gate if that surface matters.

### OOS_2: [OUT_OF_SCOPE] legacy prepare wrapper can wipe durable notes
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-compose-gate
- **Severity**: latent
- **Concern**: The retired prepare wrapper still invalidates durable compose-time notes during an in-flight handoff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Retired from live path; remove or guard legacy verb
  - From cursor-specialist-edge-cases: Remove or narrow prepare_main invalidation to staged artifacts only, or drop the verb from the live dispatch table.
  - From dyn-dyn-compose-gate: Remove or narrow `prepare_main` invalidation to staged artifacts only, or drop the verb from the live dispatch table.

### OOS_3: [OUT_OF_SCOPE] empty BASE_REF short-circuit is missing
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Compose precheck skips the current short-circuit when `BASE_REF` metadata is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] guidelines-assessment resume should not rerun postbump
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The guidelines-assessment resume path still needs explicit coverage to prove it does not re-enter postbump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Assert run_ship with PHASE=guidelines-assessment never calls finalize.postbump.
  - From cursor-specialist-testing: Add run_ship resume test with postbump forbidden when PHASE=guidelines-assessment.

### OOS_5: [OUT_OF_SCOPE] fresh-path NEEDS_USER_INPUT coverage is missing
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is still no direct `run_ship` test that proves the fresh compose path emits `NEEDS_USER_INPUT` for `architectural-guidelines-assessment`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add one run_ship test with guidelines present, no durable note, postbump stubbed OK, expecting Outcome.NEEDS_USER_INPUT.
  - From cursor-specialist-testing: Add one fresh-path run_ship test expecting exit-3 handoff.

### OOS_6: [OUT_OF_SCOPE] merge-loop rebase path still skips compose-gate refresh
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-compose-gate
- **Severity**: latent
- **Concern**: The in-driver merge-loop rebase path can still resume without re-running the compose gate before CI continues.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Defer unless PR body update on merge-loop rebase is added.
  - From dyn-dyn-compose-gate: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] unused import in ship.py
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `_pin_and_load_guidelines_note` is unused in the live ship path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Remove unused import when convenient.

### OOS_8: [OUT_OF_SCOPE] open-PR resume stale-note test gap remains
- **Reviewer(s)**: dyn-dyn-compose-gate
- **Severity**: latent
- **Concern**: The open-PR resume test still does not exercise stale durable-note rejection after HEAD/fingerprint drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-compose-gate: Address the concern above.

