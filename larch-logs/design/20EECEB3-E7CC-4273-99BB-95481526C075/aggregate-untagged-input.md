### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/report/report_tokens_cost.py:740-756
- **Concern**: RunRecord lane costs are assigned under report_tokens_render.py but must be populated in price_run. Scenario: Scan → price_run → render is the only pricing path today (report_tokens_cli.py calls price_run on every scanned record). Leaving lane fields out of price_run forces render to re-price from raw_report or leaves lane columns empty even when token_cost_from_args already emits CURSOR_COMPOSER_COST/CURSOR_GROK_COST/CURSOR_AUTO_COST. Either outcome breaks token-report lane splits or reintroduces duplicated classification logic the shared argv helper is meant to remove.
- **Proposed resolution**: Add an explicit report_tokens_cost.py step: extend price_run (and _parse_kv consumption) to copy aggregate CURSOR_COST plus component keys into new RunRecord lane fields only when BUCKETS_cursor_by_model is valid; keep render/cache readers display-only on those fields.

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/report/report_tokens_cost.py:35-40
- **Concern**: The shared Cursor argv helper does not define validation for malformed entries inside an otherwise mapping-shaped `BUCKETS_cursor_by_model` value. Scenario: A report containing one valid model bucket and one non-mapping or invalid bucket could silently drop the malformed bucket, producing incomplete token counts instead of using the required aggregate fallback
- **Proposed resolution**: Validate every per-model entry and treat any invalid entry as a malformed mapping, then emit only aggregate `BUCKETS_cursor` flags; add a focused partial-malformation test

### FINDING_3:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: code-quality
- **Location**: python/larch/report/report_tokens_cost.py:740-756
- **Concern**: `price_run()` is not a firm update step though it is the only path that materializes per-lane `RunRecord` costs for `/report-tokens`. Scenario: The plan adds lane fields to `RunRecord`, requires render/cache splits when those fields are available, and tests that `price_run()` exposes lane values; `report_tokens_cli` still prices via `price_run()` which today only copies `CURSOR_COST` into `cursor_cost`. Wire and argv fixes alone leave token-report vendor breakdown, top-runs lane columns, and cache rows aggregate-only despite valid `BUCKETS_cursor_by_model` data.
- **Proposed resolution**: Add an explicit `price_run()` bullet: after `token_cost_from_args()`, map `CURSOR_COMPOSER_COST`, `CURSOR_GROK_COST`, and `CURSOR_AUTO_COST` into the new lane fields only when all three component keys are present on the detailed wire; leave lane fields unavailable on aggregate fallback and on `_fallback_cost()`. Keep `cursor_cost` bound to aggregate `CURSOR_COST`.
