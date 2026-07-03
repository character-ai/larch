### OOS_1: [OUT_OF_SCOPE] Round reruns can suppress fresh timing rows
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-timing-ledger
- **Severity**: important
- **Concern**: Existing round-row and Gate B idempotence can suppress fresh timing rows on rerun, so a replayed round may not get a new window or a second `gate-b-apply` span.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address separately if design re-entry should get per-attempt round rows like implement stall recovery.
  - From cursor-specialist-testing: Follow-up: version output basename per attempt or clear prior gate-b-apply rows on Step 3 re-entry
  - From dyn-dyn-timing-ledger: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Missing tests for Gate B helper edge cases
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The helper's empty-ledger, boundary, and unreadable-ledger paths are not directly covered, so overlap and max-end regressions could hide a missing Gate B bar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add focused tests for _gate_b_apply_start_s returning None on empty ledger, equal/after end_s, and unreadable ledger.
  - From cursor-specialist-testing: Add a test: .gate-b-postapply-ready-1 present, no vendor rows, assert no gate-b-apply row and round window unchanged

### OOS_3: [OUT_OF_SCOPE] Timing append failures can hide Gate B timing
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `TimingLedger._append` can skip appends on flock lock timeout with only a warning, so Gate B timing can fail quietly under contention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Consider surfacing append failure to execution-issues or retry; pre-existing behavior amplified by new row type.

### OOS_4: [OUT_OF_SCOPE] Gate B timing helper is imported across modules
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: A private Gate B timing helper is imported across modules, which makes refactoring the timing path brittle.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Export a public helper or colocate Gate B timing in one module if this grows.

### OOS_5: [OUT_OF_SCOPE] Gate B apply can still be dropped under the cap
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: Under the row cap, `gate-b-apply` is still not reserved, so heavy panels can truncate it and bring back the unlabeled tail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add gate-b-apply to _CODER_APPLY_TASK_KINDS only if cap truncation is observed in production

### OOS_6: [OUT_OF_SCOPE] TimingLedger append can fail silently on lock timeout
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `TimingLedger._append` can skip appends on lock timeout with only a warning, so Gate B timing can be lost silently under contention.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Consider surfacing append failure to execution-issues or retry; pre-existing behavior amplified by new row type.

### OOS_7: [OUT_OF_SCOPE] Timing vendor column constants are duplicated
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `TIMING_VENDOR_COLS` duplicates the vendor column constant from `progress_report`, so future layout changes could drift between modules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Import or share the constant from progress_report/timing module.

