## Proposed Design Outline

### Goals
- Price the main `claude` lane by the actual model (`manifest.model_roster.main`), not always Opus 4.8.
- Add rate rows for all current Claude models and split the `claude_sub` lane by model too.
- Make new runs (PR body, final/progress) and historical `/report-tokens` reprice correctly.

### Non-goals
- New per-model aggregate breakdown section in the `/report-tokens` report body (stays #5099/#5129 "task 4").
- Codex/Cursor pricing changes; token wire-format changes beyond adding `model` to `claude_sub` ledger rows.
- Recovering env-overridden subagent models for historical runs (role-to-model map assumes defaults).

### Approach sketch
- `report_tokens_cost.py`: add the 3 rate rows; add a `model` param to `display_rates()`/`_pricing_from_counts()`; mirror the existing Codex per-model split (`_codex_argv` → `_claude_sub_argv`, `--claude-model` + `--claude-sub-*-by-model` flags).
- Thread `model_roster.main` at every site: `pr_body.render_run_summary`, `final_report`, `progress_report` (live), and `report_tokens_scan` → `RunRecord` → `token_cost_argv`/`price_run` (historical).
- `claude_sub` by model: record model in `_record_claude_sub_usage`/`_record_claude_ci_usage`; build `BUCKETS_claude_sub_by_model` in `tokens.py`; add `enrich_claude_sub_by_model`; apply the role-to-model map for model-less historical rows.
- Centralize new Claude model ids and the role-to-model map in `config.py` (G-Cfg-1); keep frozen dataclasses (G-Py-1); fail-closed default for model-less rows (G-Py-4).

### Surfaces in scope
- `python/report_tokens_cost.py`, `python/report_tokens_models.py`, `python/report_tokens_scan.py`
- `python/tokens.py`, `python/larch/agents/agents.py`, `python/larch/core/config.py`
- `python/larch/git/pr_body.py`, `python/final_report.py`, `python/progress_report.py`
- Tests: `test_report_tokens_cost.py`, `test_report_tokens_models.py`, `test_pr_body.py`, `test_run_logs.py`, `test_tokens.py`, `test_agents.py` (+ confirm `analysis/codex_role_costs.py` still prices via `display_rates()`)

### Open questions
- None. Pricing values, model coverage, fix reach, and historical `claude_sub` handling were all resolved in Round 1.
