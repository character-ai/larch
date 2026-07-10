### FINDING_2: Invalid Cursor model maps fall back to the wrong aggregate pricing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: `cursor_argv_from_buckets()` validates the full `BUCKETS_cursor_by_model` map and falls back to aggregate `--cursor-tokens` for missing, empty, or partially malformed maps. That fallback reprices legacy or malformed-detail reports with blended Cursor pricing instead of preserving aggregate Composer-priced bucket rates. The helper should emit aggregate `--cursor-input-tokens`, `--cursor-cache-read-tokens`, and `--cursor-output-tokens` from `BUCKETS_cursor` in this fallback path, reserving `--cursor-tokens` for explicit legacy blended pricing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_11: [OUT_OF_SCOPE] Progress-report pricing does not use the shared Cursor bucket helper
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: `python/larch/report/progress_report.py:135-136` still emits only Composer `--cursor-*` flags and does not use `cursor_argv_from_buckets()`, so mid-run progress summaries may overstate Cursor cost for Grok-heavy usage once the MODERATE Grok coder lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_12: [OUT_OF_SCOPE] Fallback pricing can retain stale lane fields
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: `python/larch/report/report_tokens_cost.py:777-792` does not explicitly clear `cursor_composer_cost`, `cursor_grok_cost`, and `cursor_auto_cost` in `_fallback_cost()`. A `RunRecord` with pre-set lane fields could retain stale values after fallback while `priced_by_token_cost=False`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_13: [OUT_OF_SCOPE] Planned malformed-map and final-report coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The planned malformed-map and `_final_report_token_fields()` lane-split coverage is not fully present beyond the updated Cursor argv tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_14: [OUT_OF_SCOPE] Mixed legacy and detailed cohorts suppress lane subtotals
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: Per-lane vendor breakdowns require every record to have lane fields. Mixed legacy and model-aware datasets therefore hide lane subtotals even when some records contain valid splits. The behavior should be documented or changed if partial lane totals are desired.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_15: [OUT_OF_SCOPE] Cursor rate text lacks direct golden coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Golden tests strip the rates section, so new Grok and Auto rate lines are not snapshot-covered and rate-text regressions may go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_16: [OUT_OF_SCOPE] Strict integer-only Cursor bucket validation is untested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Strict integer-only validation in `_cursor_bucket_counts` is untested, so float bucket values could force unexpected aggregate fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_17: [OUT_OF_SCOPE] Generated implementation logs are present in the branch
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Generated implementation logs are included in the branch. This is excluded by `AGENTS.md` for `chore(larch-logs)` flush commits; no action is required.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
