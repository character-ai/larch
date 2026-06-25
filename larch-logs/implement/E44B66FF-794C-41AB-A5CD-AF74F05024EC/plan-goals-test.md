## Goal
Implement issue #5386: [IMPLEMENTING] [BUG] Codex cost ignores model: gpt-5.4-mini priced at gpt-5.5, overstated 6.67x.

## Implementation Plan
Codex cost is priced at `gpt-5.5` rates for every role. The new `gpt-5.4-mini` reviewer/voter/fixer tokens are overstated by exactly **6.67x**. Pricing keys on **vendor only**; it must key on **(vendor, model)**.

## Summary

- `/design` and `/implement` recently moved their mirrored static/dynamic reviewers (plus voters and fixers) to Codex running **`gpt-5.4-mini`**, which is far cheaper than `gpt-5.5`.
- A **generic-profile Codex reviewer on `gpt-5.5`** was then added for the **first 2 review rounds**, so the Codex lane now runs **both models at once** within the same phase.
- The cost machinery ignores the model and prices **all** Codex tokens at `gpt-5.5`.
- Result: every cost surface (final report line, PR body, `/report-tokens`, role-cost analysis) overstates Codex spend for mini tokens by **6.67x**.

## Symptoms

- Cost reports since the mini-reviewer rollout read **much higher** than actual spend.
- The inflation is uniform 6.67x on the mini portion (same ratio on input, cache_read, output), and Codex spend is dominated by `cache_read`, so the headline Codex figure is ~6.7x too high wherever mini tokens dominate.

Concrete, from a real committed mini row (`2026-06-25`, `raw=codex_review`, `model=gpt-5.4-mini`):

```
input=64089  cache_read=903552  output=19339
priced at gpt-5.5  (current/WRONG): $1.3524   <- what reports show
priced at gpt-5.4-mini (correct):   $0.2029
overcharge: 6.67x
```

Rate gap (`python/report_tokens_cost.py` `DEFAULT_RATE_TABLE_PER_M`, per 1M tokens):

| bucket | gpt-5.5 | gpt-5.4-mini | ratio |
| --- | ---: | ---: | ---: |
| input | 5.00 | 0.75 | 6.67x |
| cache_read | 0.50 | 0.075 | 6.67x |
| output | 30.00 | 4.50 | 6.67x |

## Root cause

`python/report_tokens_cost.py`. The rate table **already** keys on `(vendor, model)` and **already contains** the mini row, but selection collapses to one model per vendor:

```python
DEFAULT_VENDOR_MODEL = {"codex": "gpt-5.5", ...}
def _default_row(vendor):
    return DEFAULT_RATE_TABLE_PER_M[(vendor, DEFAULT_VENDOR_MODEL[vendor])]
```

`display_rates()` calls `_default_row("codex")`, which **always** resolves to `("codex", "gpt-5.5")`. The `("codex", "gpt-5.4-mini")` row is dead code. The tuple key the fix needs already exists; the lookup just discards the model half.

Per-role model intent is real (`python/config.py`):

```
CODEX_DEFAULT_MODEL       = "gpt-5.5"      # coder (Step 2 / plan draft)
CODEX_REVIEW_MODEL_DEFAULT = "gpt-5.4-mini"
CODEX_VOTE_MODEL_DEFAULT   = "gpt-5.4-mini"
CODEX_FIX_MODEL_DEFAULT    = "gpt-5.4-mini"
```

## Models co-occur within the Codex lane (hard constraint)

The generic-profile Codex reviewer on `gpt-5.5` runs in the **first 2 review rounds** alongside the mirrored `gpt-5.4-mini` reviewers. So rounds 1-2 emit Codex reviewer tokens on **both** models simultaneously. The Codex lane is genuinely mixed-model **within a single phase, and within a single round**.

**Consequence: model must be read from the per-row ledger `model` field, never inferred from role, step, or round.** The shortcut "review == mini" is now false. Any per-role or per-step rate assumption misprices rounds 1-2. The per-model split must group rows **purely by their `model` value**, independent of step/round/`raw` label.

Committed data already shows a single run mixing models (coder vs review):

```
larch-logs/design/458D5D01-...  codex rows: 1x gpt-5.5 (codex_plan_draft) + 24x gpt-5.4-mini (codex_review)
larch-logs/design/F00F4F52-...  codex rows: 1x gpt-5.5 (codex_plan_draft) + 24x gpt-5.4-mini (codex_review)
```

Going forward, the review lane itself mixes both models, not just coder-vs-review.

## What already works (do not rebuild)

- **Ledger records the real per-row model.** `python/tokens.py` `record_vendor(model=...)` writes `"model"` per vendor row; `_vendor_rows` preserves it. Committed ledgers confirm: of 6775 codex rows, the 48 newest (`2026-06-25`) carry `"model":"gpt-5.4-mini"`; older rows are gpt-5.5-era.

## The blocker: the report drops the model

The canonical `token-report.json` collapses Codex across models. `build_report_from_ledgers` / `_summary_json` aggregate all codex rows into one bucket (`vt("codex")`); the live `token report --full` emits `BUCKETS_codex` and `codex.per_step` with **no model field**. Verified structure:

```
codex keys: ['per_step', 'totals']
BUCKETS_codex: {'input': ..., 'cached_input': ..., 'output': ..., 'total': ...}   # single bucket
any model field anywhere in codex: False
```

So pricing cannot re-split a committed report by model. The report builder must carry the model dimension, or pricing must read the ledger (per-row model) the way `python/analysis/codex_role_costs.py` already does for role attribution.

## Affected surfaces (all flow through `display_rates()` -> gpt-5.5)

1. `python/report_tokens_cost.py` `_emit_cost_line` -> the `💰 Cost:` line (`token render-cost-line`, `/report-tokens`).
2. `python/final_report.py` `_final_report_token_fields` -> `token_cost_from_args` -> final-summary cost fields.
3. `python/pr_body.py` `render_run_summary` (line ~461) -> the **final report cost line** `💰 TOTAL ~$X — Claude .., Codex .., Cursor ..`, baked into `final-summary.md` and the PR body.
4. `python/analysis/codex_role_costs.py` `_codex_cost` -> uses `rates.codex_*`, all gpt-5.5.
5. Env overrides (`LARCH_CODEX_INPUT_RATE_PER_M`, etc.) are **vendor-scoped**, so they cannot distinguish models either.

## Decided design

1. **Final cost line splits Codex by model:** show `Codex-5.5 $X` and `Codex-mini $Y` separately (summing to the Codex total). The split is **by model, not role**: `Codex-5.5` folds in the coder plus the generic-profile reviewer (rounds 1-2); `Codex-mini` folds in the mirrored reviewers, voters, and fixers. Applies to both `_emit_cost_line` and `pr_body.render_run_summary`.
2. **Extend `token-report.json`** with a per-model codex split (new key, backward compatible). Keep `BUCKETS_codex` as the model-summed total.
3. **Retrofit** the affected committed `final-summary.md` files.

## Fix plan (direction; `/design` to anchor)

1. **Model-aware pricing.** Add a `rate_row(vendor, model)` lookup over `DEFAULT_RATE_TABLE_PER_M` with fallback to `DEFAULT_VENDOR_MODEL[vendor]` when the model is absent or unknown (model-less legacy rows default to gpt-5.5, which is correct for that era). Rework `DisplayRates` / `display_rates()` so Codex rates are model-keyed rather than a single flat trio.
2. **Carry model into the report.** In `python/tokens.py` report building, group codex rows **strictly by their per-row `model` value** (independent of step, round, or `raw` label) and emit a per-model codex split (e.g. `BUCKETS_codex_by_model: {"gpt-5.5": {...}, "gpt-5.4-mini": {...}}`), defaulting model-less rows to `gpt-5.5`. Keep `BUCKETS_codex` as the model-summed total for back-compat.
3. **Price per (vendor, model) and sum** in every consumer: `_pricing_from_counts` / `token_cost_argv` (`report_tokens_cost.py`), `final_report._token_argv_from_report`, `pr_body`, and `analysis/codex_role_costs.py`. For `codex_role_costs.py`, keep role grouping but price each role's rows at **each row's own model rate**, since a single role (and a single round) can now contain both models.
4. **Cost KV + render.** Emit per-model Codex cost keys (e.g. `CODEX_GPT_5_5_COST`, `CODEX_GPT_5_4_MINI_COST`) alongside the existing `CODEX_COST` sum; render `Codex-5.5` / `Codex-mini` in both cost lines.
5. **Env overrides.** Existing `LARCH_CODEX_*` vars continue to mean gpt-5.5; add mini-specific override vars. (Confirm naming during design.)
6. **Retrofit the 2 affected runs.** Re-derive their Codex split from each run's ledger (per-row model) and rewrite the baked `💰 TOTAL` line in `final-summary.md`.

## Retrofit scope (small)

- Committed dollar figures live **only** in `final-summary.md` (the `💰 TOTAL` line). `token-report.json` stores **tokens only** (no dollars), so re-pricing is just re-running the math.
- **869** `final-summary.md` files carry a baked dollar line, but **only 2 committed runs contain any `gpt-5.4-mini` tokens**:
  - `larch-logs/design/458D5D01-6485-4491-A552-1CCAFB564675`
  - `larch-logs/design/F00F4F52-2EEE-42D6-90EE-9AB87D9C94CC`
- Every other run was genuinely all-gpt-5.5 and its figures are already correct. The retrofit is those 2; re-derive from their ledgers (which carry per-row model), since their `token-report.json` has no per-model data.
- PR bodies already posted to GitHub carry the same line; rewriting historical PRs is out of scope.

## Acceptance criteria

- Pricing resolves rates by `(vendor, model)`; mini Codex tokens price at mini rates; unknown/legacy model defaults to gpt-5.5.
- `token-report.json` carries a per-model codex split; `BUCKETS_codex` remains as the model-summed total (back-compat).
- Final cost line and PR body show `Codex-5.5` and `Codex-mini` separately, summing to the Codex total and the grand total.
- A run whose Codex lane mixes `gpt-5.5` and `gpt-5.4-mini` prices each row at its own model. Verified against `458D5D01` and `F00F4F52` (each: 1x gpt-5.5 coder + 24x gpt-5.4-mini review). A test fixture covers a mixed-model **review round** (generic 5.5 + mirrored mini in the same round).
- `analysis/codex_role_costs.py` prices per model, including a single role/round that contains both models.
- The 2 affected `final-summary.md` files are retrofitted; their Codex/total figures drop for the mini portion (~6.7x on those tokens).
- Unit tests cover the `(vendor, model)` lookup, the per-model report split, and per-model cost-line rendering; fixtures updated.
- `make lint`, `make py-lint`, `make py-test` pass.

## Files involved

- `python/report_tokens_cost.py`: `DEFAULT_VENDOR_MODEL`, `_default_row`, `display_rates`, `_pricing_from_counts`, `token_cost_argv`, `_emit_cost_line`
- `python/report_tokens_models.py`: `DisplayRates`
- `python/tokens.py`: report building (`build_report_from_ledgers`, `_summary_json`, `_vendor_rows`, BUCKETS construction); `record_vendor` already records model
- `python/final_report.py`: `_final_report_token_fields`, `_token_argv_from_report`
- `python/pr_body.py`: `render_run_summary` (the `💰 TOTAL` final line)
- `python/analysis/codex_role_costs.py`: `_codex_cost`
- `python/config.py`: `CODEX_*_MODEL_DEFAULT` (reference)
- Tests/harnesses: `python/test_report_tokens_cost.py`, `python/test_report_tokens_models.py`, `python/test_report_tokens_render.py`, `skills/implement/scripts/test-write-final-report.sh`, `scripts/test-render-cost-line*.sh`

## Related issues

- **#4053** built the single pricing authority and the `(vendor, model)` rate table plus `DEFAULT_VENDOR_MODEL`, but wired pricing to the **vendor default row** (correct when each vendor ran one model). This issue is the direct follow-up now that Codex runs multiple models. Its architecture diagram already names the intended `VENDOR_RATE_TABLE keyed by (vendor, model)`.
- **#5311** routed Codex reviews/votes/fixes to `gpt-5.4-mini` and kept the implementer on `gpt-5.5` (introduced the cheaper model).
- **#5321** added the generic-profile Codex `gpt-5.5` reviewer for rounds 1-2 (introduced concurrent models within the review lane).
- **#5174** (open) is a packaging refactor that moves `report/tokens` code into `larch.report`; it edits the same files. Sequence the two to avoid merge conflicts.

## Notes

- No security-surface change; `SECURITY.md` update not expected.
- Older committed cost figures (pre-rollout) are correct and must not be rewritten.

## Test plan
(no test plan section in plan-file)
