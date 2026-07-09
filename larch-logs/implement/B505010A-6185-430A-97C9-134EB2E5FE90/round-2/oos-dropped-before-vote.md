### FINDING_3: [OUT_OF_SCOPE] Path-based and dirfd-based active-run readers could drift
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Production cleanup reads `current` via `_read_active_run_id_from_dirfd`, while `_read_active_run_id` is only exercised in tests, so the two parsers could drift over time.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### FINDING_9: Plan-fidelity notes are already covered
- **Reviewer(s)**: cursor-specialist-plan-fidelity-auto
- **Severity**: nit
- **Concern**: The current implementation and tests already cover the earlier current-preservation and fd-pinned cleanup items, so the plan-fidelity review notes do not expose a remaining behavioral gap in this patch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-auto: Address the concern above.

