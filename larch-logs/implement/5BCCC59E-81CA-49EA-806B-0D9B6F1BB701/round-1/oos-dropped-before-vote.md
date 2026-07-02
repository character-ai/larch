### OOS_1: [OUT_OF_SCOPE] review self-review emit-tally defaults to diff mode
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: nit
- **Concern**: Self-review `emit-tally` defaults to diff mode although `REVIEW_MODE` is not set. A description-mode zero-survivor fallback can write refreshed summary artifacts as `Mode: diff`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] review_and_fix self-review-required optional timing documentation
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: `self-review-required` returns before round timing capture and `flush_review_batches`. Final timing reports may omit the failed external review round duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] design vs review/implement zero-survivor path divergence
- **Reviewer(s)**: dyn-dyn-zero-survivor
- **Severity**: nit
- **Concern**: `/design` keys off `LOOP_STATUS=degraded-empty-collector` while `/review` and `/implement` Step 5 key off normalized `THRESHOLD_REASON=no successful launched reviewer output`. The two paths can diverge on edge cases such as hard collector failures (`panel-failed`) vs empty OK counts (`degraded-empty-collector`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-zero-survivor: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] review self-review.md reference header harness shape
- **Reviewer(s)**: dyn-dyn-zero-survivor
- **Severity**: nit
- **Concern**: The reference header uses Consumer/Contract/When-to-load, while `scripts/test-review-structure.sh` validates `**Consumer**:` and `**Binding convention**:` for `/review` references. The file satisfies the harness today; keep that shape if the reference grows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-zero-survivor: Address the concern above.

