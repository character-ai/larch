### FINDING_1: `price_run()` must populate per-lane `RunRecord` cursor costs
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The scan → `price_run()` → render path is the only pricing path for `/report-tokens` (`report_tokens_cli.py` calls `price_run()` on every scanned record). Today `price_run()` copies only aggregate `CURSOR_COST` into `cursor_cost` and does not map lane component costs onto `RunRecord`. If lane fields are added to `RunRecord` and render/cache are expected to split by lane when those fields exist, leaving `price_run()` unchanged means lane columns stay aggregate-only or render must re-price from `raw_report`, duplicating classification logic that `token_cost_from_args()` / the shared argv helper is meant to own.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add an explicit report_tokens_cost.py step: extend price_run (and _parse_kv consumption) to copy aggregate CURSOR_COST plus component keys into new RunRecord lane fields only when BUCKETS_cursor_by_model is valid; keep render/cache readers display-only on those fields.
  - From Cursor-Requirements: Add an explicit `price_run()` bullet: after `token_cost_from_args()`, map `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` into the new lane fields only when all three component keys are present on the detailed wire; leave lane fields unavailable on aggregate fallback and on `_fallback_cost()`. Keep `cursor_cost` bound to aggregate `CURSOR_COST`.

### FINDING_2: Partially malformed `BUCKETS_cursor_by_model` silently drops invalid buckets
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: `_cursor_argv()` uses `_as_mapping()` on each per-model entry inside an otherwise mapping-shaped `BUCKETS_cursor_by_model`. A report with one valid model bucket and one non-mapping or invalid bucket can silently drop the malformed bucket instead of treating the mapping as invalid and falling back to aggregate `BUCKETS_cursor` flags, yielding incomplete token counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Validate every per-model entry and treat any invalid entry as a malformed mapping, then emit only aggregate `BUCKETS_cursor` flags; add a focused partial-malformation test
