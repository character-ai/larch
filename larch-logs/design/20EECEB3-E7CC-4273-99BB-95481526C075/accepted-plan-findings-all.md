### FINDING_1: Grok-only Cursor usage bypasses per-lane pricing
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: major
- **Concern**: `_pricing_from_counts` enters detailed Cursor pricing only when composer or Auto buckets are present. Grok-only invocations can therefore fall through to blended Cursor pricing, mispricing Grok at composer rates or producing an incorrect zero aggregate despite valid `BUCKETS_cursor_by_model` data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend _pricing_from_counts to add u_grok_bucket (u_grok_in/u_grok_cr/u_grok_out), include it in the per-bucket cursor branch guard and CURSOR_TOKENS sum, price Grok with display_rates grok rows, and emit CURSOR_GROK_COST alongside composer/auto lane costs
  - From Cursor-Pragmatic: In report_tokens_cost.py, add u_grok_* count keys and u_grok_bucket; enter per-lane Cursor pricing when any composer, grok, or Auto bucket has counts; price each lane with its DisplayRates row; sum all three into CURSOR_TOKENS; emit component costs only on that path.


### FINDING_3: Final reports ignore per-model Cursor buckets
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Cost Wire Compatibility
- **Severity**: major
- **Concern**: `_token_argv_from_report` still emits aggregate Cursor flags and does not classify `BUCKETS_cursor_by_model`. As a result, Grok and Auto usage in final reports and PR-facing summaries can be priced as composer usage even if the shared token-cost path is corrected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Replace the inline Cursor branch with the shared three-lane classifier exported from report_tokens_cost (same entry point /report-tokens will use) and add the planned test_final_report.py fixture that asserts argv classification for composer grok-4.5 and auto
  - From Cursor-Pragmatic: Extract a shared cursor_bucket_argv(by_model, bucket) helper from _cursor_argv and call it from _token_argv_from_report (parallel to _codex_token_argv); add the mixed-model final-report test the plan lists.
  - From Cursor-dyn-Cost Wire Compatibility: Extract a public `cursor_token_argv_from_buckets(by_model, bucket)` (parallel to `claude_sub_argv_from_buckets` at report_tokens_cost.py:354), have `_cursor_argv` delegate to it, and replace the inline cursor branch in `_token_argv_from_report` with that helper


### FINDING_4: PR summaries do not forward all Cursor lane flags
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: `python/larch/git/pr_body.py` omits `cursor-auto-*` and future `cursor-grok-*` arguments from `_TOKEN_COST_ARGS`. Recomputed run summaries can therefore fold Auto and Grok counts into the composer lane when invoked from forwarded flags rather than precomputed cost fields.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_5: Cursor component cost keys need an explicit wire contract
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-Cost Wire Compatibility
- **Severity**: major
- **Concern**: Newly computed Cursor composer, Grok, and Auto component costs will not reach downstream consumers unless `token_cost_from_args` emits them in its hardcoded order. The legacy aggregate-only path must remain aggregate-only rather than inferring a lane split from `CURSOR_COST`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Extend the order sequence in token_cost_from_args to include CURSOR_COMPOSER_COST, CURSOR_GROK_COST, and CURSOR_AUTO_COST immediately before CURSOR_COST, mirroring the Codex split; assert ordering in test_report_tokens_cost.py.
  - From Cursor-dyn-Cost Wire Compatibility: On `--cursor-tokens` blended fallback emit only `CURSOR_COST`; when per-lane flags are present populate `values` with `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` and insert those keys immediately before `CURSOR_COST` in the `order` tuple; assert sum(lanes)==`CURSOR_COST` in tests


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

