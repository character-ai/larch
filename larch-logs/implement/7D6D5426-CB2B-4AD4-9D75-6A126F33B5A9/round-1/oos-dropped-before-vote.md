### OOS_1: [OUT_OF_SCOPE] Heading is prompt-only
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The `## Raw reviewer findings (input)` → `## Reviewer findings` heading is prompt-only, so nothing parses it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Rules block still preserves the required constraints
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The rules block still preserves the required test substrings (`must appear in at least one`, `Use only slots from this inventory`), and `agents/orchestrator-aggregator.md` still carries the cross-attribution rules.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Scope-reduction marker remains accurate
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_run_scope_marker()` still delegates to `has_scope_reduction_marker()`, which keys off leading `[SCOPE-REDUCTION]` in the heading, Concern, and what fields.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Validation surfaces remain unchanged
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: The plan leaves `_validation_retry_prompt()`, the `payload_base_bytes` formula, the agent file, and the scope-anchor wrappers unchanged, so mechanical validation (`_validate_aggregate_output`, `_check_revision_traceability`) is still enforced in code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

