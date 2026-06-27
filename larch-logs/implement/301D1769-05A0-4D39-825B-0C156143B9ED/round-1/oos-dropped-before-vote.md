### OOS_1: [OUT_OF_SCOPE] design_summary.py subprocess by-model pricing not in plan scope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-token-ledger-output.txt
- **Severity**: important
- **Concern**: `/design` still builds cost argv from aggregate `BUCKETS_claude_sub` only and never emits model-family `--claude-sub-*` flags from `BUCKETS_claude_sub_by_model`, so mixed-model design subprocess costs stay on the Opus aggregate path even when enriched token reports exist. Plan acceptance targets `final_report.py` / `progress_report.py` / `pr_body.render_run_summary_main`; `/design` main-lane pricing is already fixed via `--manifest-path` + `_resolve_run_identity()`. Implement path is wired; design is not in this branch diff or plan file list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-dyn-token-ledger-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] _fallback_cost degraded path pre-existing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_fallback_cost()` still calls `display_rates()` without `claude_model`, so a Sonnet run that falls back after `token_cost_from_args` failure is priced with blended defaults rather than manifest model rates. Pre-existing degraded path; normal pricing goes through `_token_argv_for_run_report()` / `_summary_token_argv()` with `--claude-model`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] subprocess pricing no longer honors LARCH_CLAUDE_* env overrides
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-claude-pricing-output.txt
- **Severity**: nit
- **Concern**: Subprocess buckets now price from raw `rate_row()` / `_claude_sub_rates_for_model()` values instead of env-overridden `display_rates()`, so `LARCH_CLAUDE_*` env overrides no longer affect `--claude-sub-*` / model-family subprocess math (main lane still honors env via `display_rates()`). Matches the plan's main-lane vs subprocess isolation; behavior change for env-override users, not a gap in the stated Sonnet main-agent bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Document or add test only if subprocess env override is still desired
  - From dyn-dyn-claude-pricing-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] No token_cost_argv round-trip parse test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Design findings suggested argv round-trip through parsers; mechanical `_FLAG_NAMES` generation and partial flag tests reduce drift risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add optional round-trip test if panel wants extra hardening

### OOS_5: [OUT_OF_SCOPE] No token_cost_main CLI test for --claude-model
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Acceptance lists manual CLI sanity check; `token_cost_from_args` already tested for `--claude-model`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test_token_cost_cli_prices_sonnet_main_lane mirroring mini CLI test

### OOS_6: [OUT_OF_SCOPE] /report-tokens display rates mismatch with per-run pricing
- **Reviewer(s)**: dyn-dyn-claude-pricing-output.txt
- **Severity**: latent
- **Concern**: `/report-tokens` display still calls `display_rates()` without `claude_model`, so printed rate headers remain Opus-default estimates even when `price_run()` prices each run with `RunRecord.main_model`. Display/pricing mismatch only; aggregate dollar totals from `price_run()` should still be correct for paths using `token_cost_argv()` / `_token_argv_for_run_report()`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-claude-pricing-output.txt: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] final_report vs pr_body argv shape diverges for main="unknown"
- **Reviewer(s)**: dyn-dyn-claude-pricing-output.txt
- **Severity**: latent
- **Concern**: `final_report` prepends `--claude-model` for manifest `main="unknown"` while `pr_body._summary_token_argv()` explicitly skips `unknown`. Both fall back to Opus rates today, but argv shapes differ and could diverge if `unknown` handling changes later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-claude-pricing-output.txt: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] Historical ledgers missing raw/model stay on Opus
- **Reviewer(s)**: dyn-dyn-token-ledger-output.txt
- **Severity**: latent
- **Concern**: Historical ledger rows with neither `model` nor a recognized `raw` label still fall back to Opus. Documented plan behavior, but pre-#5602 ledgers with missing `raw` on reviewer/voter rows remain overpriced until re-scanned from enriched sidecars; raw-role mapping cannot recover them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-token-ledger-output.txt: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] No post-enrichment checksum against BUCKETS_claude_sub
- **Reviewer(s)**: dyn-dyn-token-ledger-output.txt
- **Severity**: latent
- **Concern**: Enrichment correctly avoids overwriting existing canonical by-model data (Codex parity), but there is no post-enrichment checksum against `BUCKETS_claude_sub`. Audit tooling comparing displayed subprocess totals to priced argv may see silent drift when ledger and canonical reports disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-token-ledger-output.txt: Address the concern above.

