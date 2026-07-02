### OOS_1: [OUT_OF_SCOPE] Failed-reviewer and Gantt labels skip fallback remap
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-attribution
- **Severity**: latent
- **Concern**: `_failed_reviewers` and Gantt rendering (`_progress_vendor_rows`) still use unremapped `label_map` labels, so vendor-fallback slots can show the nominal vendor in the failures table and timing chart even when Top reviewers are annotated. This predates the branch but remains a user-visible attribution gap beyond this PR’s Top-reviewers scope.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_2: [OUT_OF_SCOPE] Session-wide fallback remap across rounds
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `_apply_fallback_remap` builds one session-wide remap across all `round_dirs`; if the same label (e.g. `cursor/arch`) falls back in one round but runs natively in another, all aggregated points get `(via …)` or none. Same structural limitation as before #5838; unlikely when vendor availability is stable per run.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_3: [OUT_OF_SCOPE] Duplicate fallback-label reconciliation helpers may drift
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-attribution
- **Severity**: latent
- **Concern**: `_fallback_reconciled_manifest_label()` parallels `plan_review_round.reconciled_reviewer_label()` but uses manifest `tool` instead of slot-prefix nominal vendor. That split is intentional for code-review slots (`arch`, `generalist`) and improves dynamic slots, but fallback label reconciliation now lives in manifest `tool`-based logic while `/design` live reviewer-status still uses slot-prefix-based `reconciled_reviewer_label()`. Consolidating into one shared helper (manifest `tool` for code review, slot prefix for plan review) would be cleanup only and reduce future drift between Top reviewers and reviewer-status attribution; pre-existing split, not introduced by this diff’s scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Consider sharing one helper later to avoid drift; pre-existing split, not introduced by this diff’s scope.
  - From dyn-dyn-attribution: A shared helper (manifest `tool` for code review, slot prefix for plan review) would reduce future drift between Top reviewers and reviewer-status attribution.

### OOS_4: [OUT_OF_SCOPE] Collector path walk stops on empty parse result
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_round_collector_tool_by_norm_basename` returns on the first collector file that is present, non-symlink, and non-empty by byte size, even when parsing yields no `REVIEWER_FILE`/`TOOL` pairs, so it never falls through to a parent collector. Low risk today because `/review --diff` usually has no round-local collector (covered by the new parent-collector test).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Only treat a collector as authoritative when `_executing_tool_by_norm_basename` returns a non-empty map; otherwise continue the path walk.

### OOS_5: [OUT_OF_SCOPE] Documented plan edge cases lack unit fixtures
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Plan edge cases (`TOOL=unknown`, manifest rows missing `tool`/`slot`/`output`) are documented but not unit-tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add small negative fixtures if you want explicit regression locks; not required for the primary `/review --diff` parent-collector path already covered.

### OOS_6: [OUT_OF_SCOPE] Fallback remap limited to Top reviewers list
- **Reviewer(s)**: dyn-dyn-attribution
- **Severity**: latent
- **Concern**: `_apply_fallback_remap` only rewrites the Top reviewers list in `render_phase_detail`. Reviewer-status tables for `/design` are still produced separately by `write_reviewer_status_tsv()` (which already calls `reconciled_reviewer_label()`), and standalone `/review --diff` does not appear to render Review Phase Detail at all. If the original bug expected live `/review` reviewer-status output, this branch may not fully close that surface.
- **Suggested revisions (informational for voters; coder decides)**:

