### OOS_1: [OUT_OF_SCOPE] Summary gaps can fabricate negative deltas
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_summarize()` treats absent targets as token count 0 via `snapshot_values.get(target, 0)` during `advance()`, so a target that disappears for one or more baseline revisions can produce fabricated negative summary deltas across the gap in `--summary` mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Boolean token rows need regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: No test now asserts that JSON boolean `closure_estimated_tokens` values are still skipped after the new float branch, so a refactor that reorders `isinstance` checks could let `True`/`False` count as integer token values without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a focused `_parse_snapshot()` test with a boolean token row asserting the row is skipped and no value is recorded.

### OOS_3: [OUT_OF_SCOPE] Test and CLI scope stays contained
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The reviewer notes are guardrail confirmations rather than regressions: the new tests live in existing tracked files, adjacent-revision behavior stays covered, `log_path_commits()` still has a single consumer, and the new stderr warnings do not break success-path tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Float token rows can hide history on skip
- **Reviewer(s)**: dyn-dyn-ledger-gap
- **Severity**: latent
- **Concern**: Rows whose `closure_estimated_tokens` is a JSON float (including integer-valued floats like `1.0`) are skipped with a warning, so the target vanishes from that snapshot, `last_values` is cleared on the next `_build_revisions()` pass, and the following revision shows first-seen semantics rather than a delta from the last integer revision. That is the documented tradeoff, but it can hide a real per-merge change when history contains only a float row for one commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-ledger-gap: Only if product intent changes: coerce `float.is_integer()` values to `int`, or fail closed on any float row instead of skipping.

