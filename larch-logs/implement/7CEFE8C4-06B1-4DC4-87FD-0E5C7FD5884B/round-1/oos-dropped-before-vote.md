### OOS_1: [OUT_OF_SCOPE] ledger write failure remains swallowed
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_record_gate_b_apply_timing_from_round_window` still swallows `OSError` and `ValueError` from `record_vendor_task`, so a ledger write failure can leave no `gate-b-apply` row and no surfaced warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: log a bounded warning to stderr or execution-issues before returning, or let the exception propagate to a caller that can record it.

### OOS_2: [OUT_OF_SCOPE] mixed-ledger anchor behavior should be locked down
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Dropping the skill filter can let an overlapping non-plan-review `v1 vendor` row in the same ledger shift the apply anchor via `max(row_end_s)`. The current plan accepts this for per-run ledgers, but the behavior would merit a guardrail test if mixed ledgers become realistic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: add a follow-up test with an out-of-window or non-plan-review row to lock expected anchor behavior if mixed ledgers become realistic.

### OOS_3: [OUT_OF_SCOPE] skill-label inconsistency remains
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Plan-review vendor rows still record `skill="implement"` while the synthetic apply row records `skill="design"`, so the fix works around a pre-existing label mismatch instead of aligning it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: a separate change could align writer labels if downstream token/cost reports need consistency.

### OOS_4: [OUT_OF_SCOPE] Regression test covers the implement-skill write path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `test_write_design_round_meta_records_gate_b_apply_timing_idempotently` now parametrizes `vendor_skill=["design", "implement"]`, exercises `_write_design_round_meta` twice for idempotency, and asserts the synthetic `gate-b-apply` row fields; the `implement` case is the regression path that would have failed on `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Existing negative-path coverage remains intact
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Existing negative-path coverage for `_gate_b_apply_start_s` still spans the empty/unreadable ledger, boundary/at-or-after `end_s`, duplicate output basename, and marker-without-vendor-rows cases via `_write_design_vendor_timing`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] No CI or shard-matrix changes are needed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The new tests stay in the existing `python/tests/review/test_plan_review.py` collection and run under the standard pytest shard fallback, so this change does not require CI workflow or shard-matrix updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] renderer end-to-end coverage is still optional
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The optional renderer check was not extended to cover write→render for `skill="implement"` reviewer rows, so `test_render_phase_detail_design_gantt_labels_gate_b_apply` still hand-inserts a `gate-b-apply` row with `skill="design"` and does not validate the fixed production path end-to-end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a follow-up test that builds a ledger via `_write_design_round_meta` with `skill="implement"` vendor rows and asserts `render_phase_detail` contains `gate_b/apply`.

