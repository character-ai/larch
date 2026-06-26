### OOS_1: [OUT_OF_SCOPE] Collector/dropped dedupe
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_failed_reviewers` builds `seen_bases` from all collector records (including `OK` / `cap_hit`) before merging dropped rows; covered by `test_render_phase_detail_suppresses_dropped_row_when_collector_ok`.

### OOS_2: [OUT_OF_SCOPE] Straggler backstop false positives
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_dynamic_evidence_in_manifest` requires a dropped-slots ledger and intersection with dropped `dyn-*` slots.

### OOS_3: [OUT_OF_SCOPE] Codex generalist basename
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Special-cased in `_dropped_reviewer_output_base` and `progress_report._dropped_progress_base`.

### OOS_4: [OUT_OF_SCOPE] Integration coverage
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `test_review_core_real_threshold_dynamic_straggler_nine_slots`, `test_run_round_dynamic_straggler_warn_count_reaches_count_load_result`, and related e2e warn tests provide integration coverage.

### OOS_5: [OUT_OF_SCOPE] Synthetic / collector-precedence paths
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: Dedicated threshold tests include basename-miss and collector-OK carve-out paths.

### OOS_6: [OUT_OF_SCOPE] Symlink hardening
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_preserve_drop_diagnostic` rejects symlink sources and confines reads with `relative_to(round_dir)`.

### OOS_7: [OUT_OF_SCOPE] Scrub gate (implementation)
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_stage_round_artifact` runs `scrub_log_secrets` before `redact.redact()` for dropped artifacts.

### OOS_8: [OUT_OF_SCOPE] Complexity baseline
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `_run_coder_cursor` and related entries updated; `lint complexity-baseline` exits 0. Rejected/neutral ledger items (`FINDING_3`, `FINDING_5`, `FINDING_6`, unbounded diagnostics, etc.) are intentionally encoded in tests (e.g. `DYNAMIC_DROPPED_SLOTS=1` with `FAILED_SLOTS=0` when collector is `OK`); not re-raised without new evidence.

### OOS_9: [OUT_OF_SCOPE] SECURITY.md understates dropped-artifact scrub gate
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, dyn-dyn-retry-warnings
- **Severity**: latent
- **Concern**: The dropped-artifact section in `SECURITY.md` says carriers are staged through `redact.redact()` only, but `python/run_logs.py:_stage_round_artifact` (lines 3138–3144) also runs `scrub_log_secrets()` with fail-closed residual checking for `dropped-*` / `*.dropped-slots`. Implementation is stricter than the doc states; operators auditing scrub policy may read the wrong gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Document both `scrub_log_secrets` and `redact.redact()` in the dropped-artifact section.

### OOS_10: [OUT_OF_SCOPE] Missing secondary fallback to review-core-threshold.env
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan called for a secondary fallback to `review-core-threshold.env` `FAILED_SLOTS` / `DROPPED_SLOTS` when per-reviewer labels are unavailable, but `_failed_reviewers()` only merges collector and `*.dropped-slots` sources. Primary paths for this feature (committed dropped ledgers + collector) are covered by tests; the gap only matters if both label sources are missing while threshold env is present.

### OOS_11: [OUT_OF_SCOPE] Missing straggler + invalid-slot combined WARN test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The plan asked for a straggler + invalid-slot combined `WARN` merge test; the harness tests `cost-fallback-exceeded-threshold;invalid-slots-dropped` and straggler-only separately, but not straggler + invalid-slot in one dispatch. The merge logic is shared (`warn_tokens` list), so regression risk is low.

### OOS_12: [OUT_OF_SCOPE] DYNAMIC_DROPPED_SLOTS counter vs collector precedence
- **Reviewer(s)**: dyn-dyn-retry-warnings
- **Severity**: latent
- **Concern**: `python/review_pipeline.py:1960-1961` vs `python/review_and_fix.py:2304-2305`: `DYNAMIC_DROPPED_SLOTS` increments for every `dyn-*` dropped TSV row before collector/output precedence, while `_surface_dropped_reviewer_warning` warns on that counter alone. Prior panels rejected treating this as a defect when collector already recorded success; it can still produce `Warnings: 1` with `failed=0, dropped=1` in synthetic edge cases, but it matches the plan's slot-prefix semantics.

### OOS_13: [OUT_OF_SCOPE] Unbounded diagnostic carrier size at preservation
- **Reviewer(s)**: dyn-dyn-retry-warnings
- **Severity**: latent
- **Concern**: `python/agent_waterfall.py:833-855`: Round 3 added a symlink guard on diagnostic sources, but copied `failure-diag` / `launch-stderr` content still has no byte cap at preservation time. Prior unbounded-carrier findings were rejected; hung vendor stderr could still produce very large committed `dropped-*-*.txt` artifacts.

