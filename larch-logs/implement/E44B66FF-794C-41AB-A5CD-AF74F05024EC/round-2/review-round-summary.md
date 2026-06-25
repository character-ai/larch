# Review Round 2

- Mode: `diff`
- 2 accepted, 7 rejected (5 neutral)

## Accepted Findings

### FINDING_1: codex_role_costs uses `_single_ledger` instead of session-scoped ledger resolution
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_single_ledger` requires exactly one `larch-tokens-*.jsonl` glob while `tokens.run_log_ledger_path` resolves via session-id hash first. Run directories with multiple ledger files and a valid session-id get correct `/report-tokens` enrichment but `codex_role_costs` skips the ledger path: design Codex roles can become $0; implement runs fall back to per-step pricing at gpt-5.5 aggregate rates (~6.67x mini overstatement in role-cost analysis). `_implement_roles()` only uses the per-row-model ledger path when exactly one ledger exists, so resumed runs with multiple ledgers still use the old `codex.per_step` effective-rate path and misprice mixed gpt-5.5 / gpt-5.4-mini lanes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Replace `_single_ledger` with `tokens.run_log_ledger_path(run_dir)` in `_design_roles` and `_implement_roles`.
  - From codex-specialist-correctness: Resolve the ledger with `tokens.run_log_ledger_path()` or merge all ledgers with `tokens.build_report_from_ledgers()` and price from that data instead of gating on `_single_ledger()`.
  - From cursor-specialist-edge-cases: Replace `_single_ledger` with `tokens.run_log_ledger_path`; enrich the report in `_build_run_cost` before report-based Codex fallback.


### FINDING_8: Implement role-cost path mis-splits coder vs reviewer on cross-step mixed models without run-dir ledger
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-codex-pricing-split-output.txt
- **Severity**: important
- **Concern**: `_implement_roles` per-step fallback uses one blended effective Codex rate when ledger resolution fails, misallocating coder vs reviewer costs under mixed models. Committed implement run dirs never contain `larch-tokens-*.jsonl` (design-only retention in `python/gc_run_logs.py`), so `_single_ledger` is always `None` on the implement analysis path and the code always falls through to `_codex_step_cost` + `_codex_eff_per_token`. That distributes a single blended $/token across `codex.per_step` buckets even when `BUCKETS_codex_by_model` is present (e.g. 1M Step 2 `gpt-5.5` input + 1M Step 5 `gpt-5.4-mini` input yields ~$2.88/$2.88 instead of $5.00/$0.75). Run total may be near-correct via effective rate but coder/reviewer split in role-cost analysis is wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fix ledger resolution first; use enriched `BUCKETS_codex_by_model` for any per_step fallback.
  - From dyn-dyn-codex-pricing-split-output.txt: For implement runs without a run-dir ledger, derive role costs from `BUCKETS_codex_by_model` plus per-row ledger data flushed into the report (or commit a session-scoped ledger slug into the implement run-log tree), instead of the per-step effective-rate shortcut; keep the ledger path for design.


