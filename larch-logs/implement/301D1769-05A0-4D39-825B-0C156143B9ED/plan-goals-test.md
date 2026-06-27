## Goal
Implement issue #5602: [IMPLEMENTING] [BUG] Claude cost always priced at Opus 4.8 rates regardless of actual main-agent model.

## Implementation Plan
## Plan

## Approach

- Add current Claude model ids and the historical `claude_sub` raw-role mapping in config.
- Price the main `claude` lane with `RunRecord.main_model`, live manifest `model_roster.main`, or CLI `--main-model` / `--claude-model`.
- Add Claude rate rows for:
  - `claude-sonnet-4-6`
  - `claude-haiku-4-5`
  - `claude-fable-5`
- Each new row must match the Opus schema: `input`, `cache_read`, `cache_create_5m`, `cache_create_1h`, `output`.
- Preserve `claude-opus-4-8` as the default fallback.
- Mirror the existing Codex main-vs-mini split for `claude_sub`:
  - record model for new spawned-Claude usage
  - build `BUCKETS_claude_sub_by_model`
  - enrich old token reports from committed ledgers when possible
  - map model-less historical raw roles to defaults using exact ledger `raw=` strings from `agents.py`
- **Main-lane vs subprocess pricing isolation (Codex pattern):**
  - `--claude-model` and `display_rates(claude_model=...)` apply **only** to main-lane `c_*` counts.
  - Aggregate legacy `--claude-sub-*` flags price at Opus rates (or blended fallback when only aggregate totals exist).
  - Model-specific subprocess buckets use dedicated `--claude-sub-<model-family>-*` flag families, each priced via `rate_row("claude", model=<family id>)`.
- Parse and consume `--claude-model` and new subprocess model flags **before** `_parse_count_args()` so they never hit the count-flag validator.
- In `render_run_summary_main()`, resolve the pricing model with the same `_resolve_run_identity()` path used for display (`manifest_path` + optional `--main-model` override) before building `token_argv`.
- Do not add a new `/report-tokens` per-model aggregate section.

## Files to modify/create

### UPDATED: python/larch/core/config.py

- Add Claude model constants:
  - `CLAUDE_OPUS_4_8_MODEL`
  - `CLAUDE_SONNET_4_6_MODEL`
  - `CLAUDE_HAIKU_4_5_MODEL`
  - `CLAUDE_FABLE_5_MODEL`
- Repoint `CLAUDE_CI_FIX_MODEL` to `CLAUDE_OPUS_4_8_MODEL`.
- Add `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` keyed by **exact** ledger `raw=` strings already emitted by `agents.py`:
  - `claude_review`, `claude_vote`, `claude_scout`, `claude_draft` → `claude-sonnet-4-6`
  - `claude_ci_fix`, `claude_lint_fix` → `claude-opus-4-8`
- Add a small helper or constant fallback rule for unknown raw labels:
  - default to `claude-opus-4-8`
  - keep legacy fallback behavior explicit.
- Do not use shortened keys like `review` or `scout`; only the full `claude_*` tokens above (plus any other `_claude_token_raw` / `_drafter_token_raw` outputs discovered during implementation).

### UPDATED: python/report_tokens_models.py

- Add `main_model: str = ""` to `RunRecord`.
- Keep the default at the end of the dataclass so existing tests and callers stay compatible.
- No report body schema change.

### UPDATED: python/report_tokens_scan.py

- Read `manifest.model_roster.main` in `_record()`.
- Store it in `RunRecord.main_model`.
- When canonical token reports lack `BUCKETS_claude_sub_by_model`, call a new token enrichment helper that mirrors `enrich_codex_by_model`.
- Keep existing skip and warning behavior for malformed reports.

### UPDATED: python/tokens.py

- In `_full_json()`, build `BUCKETS_claude_sub_by_model` next to `BUCKETS_claude_sub`.
- For each `claude_sub` ledger row:
  - use row `model` when present
  - otherwise derive model from `raw` using `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` with exact `claude_*` keys
  - use the Opus fallback for unknown/model-less rows
- Preserve `BUCKETS_claude_sub` as the summed legacy bucket.
- Add `enrich_claude_sub_by_model(report, run_dir=...)`, matching `enrich_codex_by_model`.
- Ensure sidecar parsing and ledger writing continue to round-trip `MODEL`.

### UPDATED: python/larch/agents/agents.py

- Change `_record_claude_sub_usage()` to accept `model: str`.
- Pass the active `--model` from `launch_claude_subprocess_main()`.
- Pass the drafter/scout/voter/reviewer model where `_record_claude_sub_usage()` is called directly.
- Change `_record_claude_ci_usage()` to accept `model: str`.
- Include `MODEL=<model>` in CI token sidecars.
- Pass `args.model` from Claude CI and lint-fix launch paths.
- Keep validation that model is one non-empty token.

### UPDATED: python/report_tokens_cost.py

- Import config Claude model constants.
- Add rate rows for Sonnet 4.6, Haiku 4.5, and Fable 5 using verified Anthropic list prices.
- Each row must include the full Opus-equivalent key set:
  - `input`, `cache_read`, `cache_create_5m`, `cache_create_1h`, `output`
- Add `claude_model: str | None = None` to `display_rates()`.
- Resolve **main-lane** Claude rates with `rate_row("claude", model=claude_model)` for the `claude_*` DisplayRates fields only.
- Keep env override names unchanged; they override the selected main-lane Claude model rate.
- Add `_parse_pricing_argv(argv)` (or equivalent) that:
  - strips and returns `--claude-model MODEL` before count parsing
  - strips any new model-specific `claude_sub` flags that are not count keys
  - leaves only recognized count flags for `_parse_count_args()`
- Extend `_FLAG_NAMES` with model-specific `claude_sub` count families mirroring the Codex mini split:
  - keep existing `--claude-sub-*` as the Opus/default aggregate family
  - add Sonnet, Haiku, and Fable families with parallel input/cache/output flag names
- Add `_claude_sub_rates_for_model(model: str)` helper using `rate_row("claude", model=...)`.
- Add `_claude_sub_argv()` that mirrors `_codex_argv()`:
  - read `BUCKETS_claude_sub_by_model`
  - route each model bucket to the matching flag family
  - fold unknown/model-less rows into the Opus `--claude-sub-*` family
  - fall back to aggregate `BUCKETS_claude_sub` when no by-model split exists
- Change `_pricing_from_counts()` signature to accept `claude_model: str | None = None`.
- In `_pricing_from_counts()`:
  - call `display_rates(environ=env, claude_model=claude_model)` for **main-lane `c_*` math only**
  - price aggregate `--claude-sub-*` (`cs_*`) with Opus/default subprocess rates, **not** the main-lane `claude_model`
  - price each new model-specific subprocess flag family with `rate_row("claude", model=<family model>)`, summing into `CLAUDE_SUB_COST`
  - preserve blended fallback for aggregate-only `claude_sub_t` rows
- Change `token_cost_from_args()` to:
  - call `_parse_pricing_argv()` first
  - pass parsed `claude_model` into `_pricing_from_counts()`
  - never pass `--claude-model` into `_parse_count_args()`
- In `token_cost_argv()`:
  - emit `--claude-model <record.main_model>` when set
  - use `_claude_sub_argv()` / `BUCKETS_claude_sub_by_model` when present
  - fall back to existing `BUCKETS_claude_sub` behavior when absent
- In `price_run()` and fallback paths:
  - preserve blended fallback behavior for aggregate-only rows
  - use model-specific pricing when bucket data is available
- Keep output keys unchanged:
  - `CLAUDE_COST`
  - `CLAUDE_SUB_COST`
  - `TOTAL_COST`
  - existing Codex split keys

### UPDATED: python/larch/git/pr_body.py

- In `render_run_summary_main()`, **before** assembling `token_argv`, resolve pricing identity with the same helper used for display:
  - `_version, pricing_model, _effort = _resolve_run_identity({"manifest_path": args.manifest_path, "main_model": args.main_model})`
- Prepend `--claude-model <pricing_model>` to `token_argv` when `pricing_model` is non-empty and not `unknown`.
- Do not rely on `args.main_model` alone; design/implement callers pass `--manifest-path` without `--main-model`.
- Keep the rendered "Main agent model" line unchanged (`_identity_lines()` already uses `_resolve_run_identity()`).
- Keep the PR body cost line shape unchanged.

### UPDATED: python/final_report.py

- Read the run manifest from the live run log directory.
- Extract `model_roster.main`.
- Prepend `--claude-model <main>` to `_token_argv_from_report()` output when manifest main is non-empty.
- Enrich both Codex and Claude subprocess by-model buckets before pricing.
- Extend `_token_argv_from_report()` (or add a sibling helper) to emit model-specific `claude_sub` flags from `BUCKETS_claude_sub_by_model`, mirroring `_codex_token_argv()`.
- Add a local helper only if needed to avoid duplicating unsafe JSON access.

### UPDATED: python/progress_report.py

- Update `_round_vendor_cost()` so `claude_sub` ledger rows are bucketed by model, not only by vendor.
- Emit model-specific `claude_sub` flag families via the same routing rules as `_claude_sub_argv()`.
- Use row `model` when present and `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` (exact `claude_*` raw keys) when absent.
- Prepend `--claude-model` when round pricing has access to manifest/run main model context.
- Keep the displayed progress cost format unchanged.

### MAY_UPDATE: python/report_tokens_cli.py

- Leave `display_rates()` calls unchanged if the new `claude_model` parameter defaults safely.
- Update only if type checks or tests need an explicit default-rate display call.

### MAY_UPDATE: python/report_tokens_render.py

- Leave report rendering unchanged unless tests require documenting that displayed rates are default-rate estimates.
- Do not add a new per-model aggregate section.

### MAY_UPDATE: python/analysis/codex_role_costs.py

- Leave unchanged if the optional `display_rates()` signature remains compatible.
- Update only for type-check compatibility.

### UPDATED: python/test_report_tokens_cost.py

- Assert the new Claude rate rows include all cache-tier keys and default Opus fallback.
- Add a test that `display_rates(claude_model="claude-sonnet-4-6")` returns Sonnet main-lane rates.
- Add a test that `--claude-model claude-sonnet-4-6` prices main Claude input/output at Sonnet rates.
- Add a test that `token_cost_from_args(["--claude-model", "claude-sonnet-4-6", ...])` does **not** raise `ValueError: unknown or incomplete flag`.
- Add a regression test that Sonnet main-lane pricing does **not** reprice aggregate `--claude-sub-*` tokens at Sonnet rates (Opus subprocess rates remain).
- Add a test that mixed model-specific `claude_sub` flag families price Opus/Sonnet/Haiku/Fable subprocess tokens at their respective rates.
- Add a test that `token_cost_argv()` emits `--claude-model` from `RunRecord.main_model`.
- Keep existing Codex mini tests intact.

### UPDATED: python/test_report_tokens_models.py

- Assert `RunRecord.main_model` defaults to `""`.
- Update any field-set expectations if present.

### UPDATED: python/test_report_tokens_scan.py

- Add a manifest with `model_roster.main`.
- Assert scanned records carry `main_model`.
- Add a canonical report lacking `BUCKETS_claude_sub_by_model` plus a ledger carrying model data.
- Assert scan enrichment recovers `BUCKETS_claude_sub_by_model`.

### UPDATED: python/test_tokens.py

- Add tests for `BUCKETS_claude_sub_by_model`.
- Cover:
  - explicit ledger row model
  - model-less `claude_review` raw mapping to Sonnet
  - model-less `claude_ci_fix` raw mapping to Opus
  - model-less `claude_lint_fix` raw mapping to Opus
  - unknown raw fallback to Opus
- Assert `CLAUDE_SUB_DEFAULT_MODEL_BY_RAW` keys match exact `claude_*` raw strings from `agents.py`.
- Add an enrichment test matching the Codex enrichment pattern.

### UPDATED: python/test_agents.py

- Update Claude subprocess tests to assert model recording in the token-record path when usage exists.
- Add or extend a fake successful Claude JSON response with usage data.
- Assert CI/lint-fix token sidecars include `MODEL=<args.model>`.

### UPDATED: python/test_pr_body.py

- Add coverage that `render_run_summary_main()` with `--manifest-path` only (no `--main-model`) forwards manifest `model_roster.main` into pricing via `--claude-model`.
- Add coverage that explicit `--main-model` override still wins over manifest for pricing.
- Keep PR body rendering assertions unchanged except expected costs when model-specific pricing is visible.

### UPDATED: python/test_final_report.py

- Add coverage for manifest `model_roster.main`.
- Assert final report pricing uses Sonnet rates for main Claude when the manifest says Sonnet.
- Add coverage for `BUCKETS_claude_sub_by_model` enrichment and model-specific subprocess argv when final report reads a committed ledger.

### UPDATED: python/test_progress_report.py

- Add coverage for `_round_vendor_cost()` with mixed `claude_sub` ledger rows by model.
- Add coverage for model-less raw-role fallback using exact `claude_*` raw strings.
- Keep rendered progress output shape unchanged.

### UPDATED: python/test_run_logs.py

- Update existing manifest fixture expectations only if added config constants affect model defaults.
- Add no new run-log schema behavior unless needed by scanner tests.

## Edge cases

- Unknown `main_model` must fall back to Opus rates through `rate_row()`.
- Empty `main_model` must preserve current Opus fallback.
- `render_run_summary_main()` callers that pass `--manifest-path` without `--main-model` must still price from manifest via `_resolve_run_identity()`.
- `--claude-model` must never reach `_parse_count_args()`; unknown-flag failures mark costs N/A today.
- Main-lane Sonnet pricing must not bleed into aggregate `--claude-sub-*` subprocess pricing.
- Legacy aggregate-only token rows must still use blended fallback warnings.
- Legacy `claude_sub` rows without `model` must use exact `claude_*` raw-role mapping when `raw` is present.
- Legacy `claude_sub` rows without both `model` and useful `raw` must price as Opus.
- Canonical reports without by-model buckets should still price, even when ledger enrichment is unavailable.
- New Claude model rows missing `cache_create_5m` / `cache_create_1h` must not KeyError when cache-write counts are present.
- Env rate overrides should continue to apply through existing `LARCH_CLAUDE_*` names.
- Output keys and PR/report prose should stay stable.

## Failure modes

- A missing model in the live manifest can still overprice Sonnet as Opus, but only when the manifest lacks recoverable model data.
- Historical env-overridden subprocess models cannot be recovered; raw-role mapping assumes defaults by design.
- If `claude_sub` by-model flags drift from `_parse_count_args()`, pricing may silently omit a bucket. Add tests for every new flag family.
- If `display_rates(claude_model=...)` is reused for subprocess buckets, Sonnet-main runs will misprice Opus CI/lint-fix subprocess tokens.
- If new model constants are duplicated outside config, future model updates can drift. Keep ids centralized.

## Testing strategy

- Run targeted unit tests:
  - `python3 -m pytest python/test_report_tokens_cost.py`
  - `python3 -m pytest python/test_report_tokens_models.py`
  - `python3 -m pytest python/test_report_tokens_scan.py`
  - `python3 -m pytest python/test_tokens.py`
  - `python3 -m pytest python/test_agents.py`
  - `python3 -m pytest python/test_pr_body.py`
  - `python3 -m pytest python/test_final_report.py`
  - `python3 -m pytest python/test_progress_report.py`
  - `python3 -m pytest python/test_run_logs.py`
- Run focused lint/type checks for changed Python files through the repo's standard local targets if available.
- Manually sanity-check one synthetic Sonnet main-lane argv:
  - `python3 python/cli.py token cost --claude-model claude-sonnet-4-6 --claude-input-tokens 1000000 --claude-output-tokens 1000000`
  - Expected Claude cost: `$18.00`.
- Manually sanity-check Sonnet main + Opus aggregate subprocess argv does not cross-price subprocess tokens at Sonnet rates.
- Manually sanity-check mixed `claude_sub` model-family argv after implementing exact flag names.

## Acceptance

- `DEFAULT_RATE_TABLE_PER_M` carries rows for `claude-opus-4-8`, `claude-sonnet-4-6`, `claude-haiku-4-5`, and `claude-fable-5`, each with `input`, `cache_read`, `cache_create_5m`, `cache_create_1h`, and `output`.
- `display_rates(claude_model="claude-sonnet-4-6")` returns Sonnet main-lane rates; empty or unknown `main_model` falls back to Opus rates.
- `python3 python/cli.py token cost --claude-model claude-sonnet-4-6 --claude-input-tokens 1000000 --claude-output-tokens 1000000` reports Claude cost `$18.00` and does not raise `ValueError`.
- Main-lane `--claude-model` never reprices aggregate `--claude-sub-*` tokens; model-specific `claude_sub` flag families price Opus, Sonnet, Haiku, and Fable subprocess buckets at their own rates.
- `agents.py` records the subprocess model in `_record_claude_sub_usage()` and `_record_claude_ci_usage()`; `tokens.py` builds `BUCKETS_claude_sub_by_model`; model-less rows map by exact `claude_*` raw role (`claude_review` / `claude_vote` / `claude_scout` / `claude_draft` to Sonnet, `claude_ci_fix` / `claude_lint_fix` to Opus, unknown to Opus).
- `report_tokens_scan` surfaces `model_roster.main` into `RunRecord.main_model` and enriches `BUCKETS_claude_sub_by_model` from committed ledgers; `/report-tokens` historical repricing uses the recovered model.
- `pr_body.render_run_summary_main`, `final_report.py`, and `progress_report.py` thread the main model into pricing via `--claude-model`.
- Backward compatibility holds: legacy model-less reports and ledgers still price (Opus default or blended fallback), output keys `CLAUDE_COST` / `CLAUDE_SUB_COST` / `TOTAL_COST` and the Codex split keys stay unchanged, and no new `/report-tokens` aggregate section is added.
- Targeted unit tests pass: `test_report_tokens_cost.py`, `test_report_tokens_models.py`, `test_report_tokens_scan.py`, `test_tokens.py`, `test_agents.py`, `test_pr_body.py`, `test_final_report.py`, `test_progress_report.py`, `test_run_logs.py`.

diff_added: 680
diff_deleted: 90
mechanical_churn: false
diff_lines: 770

## Test plan
(no test plan section in plan-file)
