# Review Round 1

- Mode: `diff`
- 2 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Canonical token-report preferred over ledger when `BUCKETS_codex_by_model` missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `_resolve_report` returns canonical `token-report.json` whenever it has numeric tokens, even when it lacks `BUCKETS_codex_by_model` while the committed ledger has per-row `gpt-5.4-mini`. Combined with `_codex_argv` pricing all aggregate `BUCKETS_codex` at gpt-5.5 when the by-model split is absent, mixed-model implement runs can overstate mini tokens by ~6.67× in `/report-tokens`, `final_report`, and role-cost analysis.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: When canonical report lacks BUCKETS_codex_by_model and a ledger exists, rebuild or merge per-model buckets from build_report_from_ledgers before pricing; mirror in final_report._token_argv_from_report.
  - From cursor-specialist-edge-cases: When canonical JSON lacks BUCKETS_codex_by_model but the ledger has per-row model, rebuild or merge via build_report_from_ledgers before pricing; only use the gpt-5.5-only fallback for genuinely model-less legacy rows.


### FINDING_3: `_implement_roles` uses run-wide effective Codex rate instead of per-row model pricing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, codex-generalist, dyn-dyn-codex-pricing-split
- **Severity**: important
- **Concern**: `_implement_roles` prices every `codex.per_step` bucket with one run-wide effective $/token from `_codex_eff_per_token`. Run-level Codex total stays correct when `BUCKETS_codex_by_model` is present, but coder/reviewer/other splits misallocate whenever steps use different models (e.g. Step 2 all `gpt-5.5`, Step 5 mixed `gpt-5.5` + `gpt-5.4-mini`). Example: 1M Step 2 `gpt-5.5` input + 1M Step 5 `gpt-5.4-mini` input should yield `$5.00`/`$0.75` coder/reviewer costs but reports `$2.875`/`$2.875`. Design already prices per-row via `_design_roles` + ledger; implement still uses the proportional shortcut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: For implement, price from larch-tokens ledger rows by model (like _design_roles) or add per-model dimensions to codex.per_step.
  - From codex-specialist-correctness: Price implement runs from per-row ledger data, or carry the model split into the report and sum each step from its own model buckets
  - From codex-specialist-edge-cases: Price implement runs from ledger rows like _design_roles() does, grouped by raw and per-row model; keep the blended per-step fallback only when no ledger exists
  - From codex-generalist: Carry a per-step, per-model Codex split in `token-report.json`, or read implement ledger rows with timestamp/model attribution. Price each role bucket by its own model. Use the effective-rate fallback only for legacy reports without model detail.
  - From dyn-dyn-codex-pricing-split: For `/implement`, mirror the design ledger path: read the committed `larch-tokens-*.jsonl`, price each Codex row at `entry["model"]`, and attribute by step prefix/`raw` label. Keep `_codex_eff_per_token` only as a fallback when no usable ledger exists.


