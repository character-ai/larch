### OOS_1: [OUT_OF_SCOPE] Pin the non-numeric warning copy
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The `REVIEW_ROUND_COUNT_WARN=non-numeric` path does not pin the canonical warning prose, so orchestrator output can drift or omit it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Emit WARNING_MESSAGE from renderer or pin exact warning text in approval-gates.md.

### OOS_2: [OUT_OF_SCOPE] Step 3 count-reader OSError parity
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Step 3 `_read_count` has no `OSError` guard, so unreadable count files can still raise there even though the renderer fail-opens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Align plan_review_common._read_count with design_publish fail-open read (separate change).

### OOS_3: [OUT_OF_SCOPE] Review-count reader duplication
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The review-count reader is duplicated, which can let cap-shaping logic drift between Step 3 and Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extract one shared digit-only review-round-count reader (optional follow-up).

### OOS_4: [OUT_OF_SCOPE] Pin the non-numeric warning copy
- **Reviewer(s)**: dyn-dyn-gate-render
- **Severity**: nit
- **Concern**: The `REVIEW_ROUND_COUNT_WARN=non-numeric` path still leaves the warning string implicit, so byte-stable logging remains at risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-render: consider emitting `WARN_MESSAGE=...` from Python if byte-stable logging matters.

### OOS_5: [OUT_OF_SCOPE] Token-reduction target still barely advanced
- **Reviewer(s)**: dyn-dyn-gate-render
- **Severity**: latent
- **Concern**: The eager-closure shrink is tiny, so the large `approval-gates.md` reduction goal is still barely met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-render: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Warn-KV absence test gap
- **Reviewer(s)**: dyn-dyn-gate-render
- **Severity**: nit
- **Concern**: Valid-count tests still do not assert that `REVIEW_ROUND_COUNT_WARN` is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-gate-render: Address the concern above.

