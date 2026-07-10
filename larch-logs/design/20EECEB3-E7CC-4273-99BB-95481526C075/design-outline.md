## Proposed Design Outline

### Goals
- Add `("cursor","grok-4.5")` rate row at 2.00/0.50/6.00 (no Teams surcharge) to `DEFAULT_RATE_TABLE_PER_M`.
- Classify `BUCKETS_cursor_by_model` into three pricing lanes: composer (surcharged), grok (no surcharge), auto.
- Emit `CURSOR_GROK_COST` as an additive per-model cost field while preserving aggregate `CURSOR_COST`; render cursor splits in token reports, final reports, and PR summaries.

### Non-goals
- Routing changes (dispatch_step2.py, bootstrap.py, config.py coder order) are in other partition pieces.
- Backfilling historical run logs with cursor per-model data.
- Modifying `tokens.py` or adding `enrich_cursor_by_model`.

### Approach sketch
- `report_tokens_models.py`: add `cursor_grok_{input,cache_read,output}` fields to `DisplayRates` (defaulted 0.0).
- `report_tokens_cost.py`: add rate row, add `CURSOR_GROK_MODELS`, extend `_cursor_argv` to 3 lanes, add `--cursor-grok-*` flags, price grok bucket, emit `CURSOR_GROK_COST`, update `_emit_cost_line` to show grok sub-label when nonzero.
- `report_tokens_render.py`: add cursor-grok line to `_rates_text`.
- `final_report.py`: add `_cursor_token_argv` helper (mirror of `_codex_token_argv`) using grok/composer/auto routing; update `_token_argv_from_report`; add `cursor_grok_cost` to returned fields.
- `pr_body.py`: add `--cursor-grok-*` to `_TOKEN_COST_ARGS`, add `_cursor_cost_segment` helper, update cost line to show per-model cursor breakdown.

### Surfaces in scope
- `python/larch/report/report_tokens_models.py`
- `python/larch/report/report_tokens_cost.py`
- `python/larch/report/report_tokens_render.py`
- `python/larch/report/final_report.py`
- `python/larch/git/pr_body.py`
- `python/tests/report/test_report_tokens_cost.py`
- `python/tests/report/test_report_tokens_render.py`
- `python/tests/report/test_final_report.py`
- `python/tests/git/test_pr_body.py`

### Open questions
- None.
