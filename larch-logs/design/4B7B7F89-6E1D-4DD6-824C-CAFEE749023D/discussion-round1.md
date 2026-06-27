# Round 1 — Scope & Constraints (issue #5602)

## Decision 1: Rate-table model coverage
- **Question**: Which Claude models get rows in `DEFAULT_RATE_TABLE_PER_M`?
- **Resolution**: All current models. Add `claude-sonnet-4-6`, `claude-haiku-4-5`, `claude-fable-5` (`claude-opus-4-8` row already exists).
- **Source**: user

## Decision 2: Fix reach across cost-report paths
- **Question**: How far should the fix reach?
- **Resolution**: All paths. Thread the model into pricing and fix every call site: PR body (`pr_body.render_run_summary`), `final_report.py`, `progress_report.py`, AND the `/report-tokens` historical scan (`report_tokens_scan.py` → `RunRecord` → `price_run`). No NEW per-model aggregate breakdown in the `/report-tokens` report body (that remains the #5099/#5129 "task 4" follow-up). Scope here is correct per-run repricing, not a new report dimension.
- **Source**: user

## Decision 3: claude_sub (subagent) lane per-model attribution
- **Question**: Include per-subagent model pricing now, or defer?
- **Resolution**: Include now. Going forward, record the subagent model at launch and split the lane by model (mirror the existing Codex `BUCKETS_codex_by_model` precedent).
- **Source**: user

## Decision 4: Historical / unattributable claude_sub pricing
- **Question**: How to price historical claude_sub tokens (committed ledgers carry no per-subagent model)?
- **Resolution**: Role-to-model mapping. Map the ledger `raw` role to its known default model: `review`/`vote`/`scout`/`draft` → `claude-sonnet-4-6`, CI-fix → `claude-opus-4-8`. Assumes config defaults (env overrides such as `LARCH_VOTER_MODEL` cannot be recovered after the fact). Going-forward runs use the recorded model directly.
- **Source**: user

## Hard constraints / findings (from codebase + claude-api reference)
- **Pricing values are fixed** (per-1M, from the `claude-api` reference; the existing Opus 4.8 row already matches). Cache rates follow the standard multipliers (cache_read = 0.1x input, 5m write = 1.25x, 1h write = 2x):
  - opus-4-8: in 5.00 / read 0.50 / 5m 6.25 / 1h 10.00 / out 25.00 (unchanged, already present)
  - sonnet-4-6: in 3.00 / read 0.30 / 5m 3.75 / 1h 6.00 / out 15.00
  - haiku-4-5: in 1.00 / read 0.10 / 5m 1.25 / 1h 2.00 / out 5.00
  - fable-5: in 10.00 / read 1.00 / 5m 12.50 / 1h 20.00 / out 50.00
- **Mirror the Codex per-model precedent**, do not invent a new mechanism: `BUCKETS_codex_by_model`, `_codex_argv`, `enrich_codex_by_model`, and the `--codex-mini-*` flag family are the template for both the main-model threading and the claude_sub by-model split.
- **Main `claude` lane**: model is `manifest.model_roster.main`. Available live (pr_body `_resolve_run_identity`); for `/report-tokens` the scanner must surface it into `RunRecord`.
- **Backward compatibility**: model-less legacy ledger/report rows must keep pricing at the existing default (`DEFAULT_VENDOR_MODEL["claude"]` = opus-4-8) where no role/model is available; do not break old runs.
- **No new report dimension**: per-model aggregate rollups in the `/report-tokens` body are explicitly out of scope (task 4).

## Non-goals
- Adding a per-model aggregate breakdown section to the `/report-tokens` report body.
- Changing token-collection wire formats beyond adding `model` to the claude_sub ledger rows.
