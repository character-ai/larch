## Goal
Implement issue #5854: [IMPLEMENTING] Extend cost computation machinery to support "auto" model for Cursor and to account for cache read surcharge in non-auto mode.

## Implementation Plan
## Summary

larch under-prices the Cursor lane by ~2x because the cost machinery applies Cursor's **published composer-2.5 list rates** ($0.50 input / $0.20 cache-read / $2.50 output per M) while Cursor actually bills larch's usage on a **Teams plan at list + a flat $0.25/M "Cursor Token Rate"** on every token (input, output, and cached). Extend the cost machinery to (a) account for the Teams cache-read/per-token surcharge in **non-auto** mode (pinned `composer-2.5`, which is what larch does today), and (b) support pricing for **Auto** mode (different, flat rate card, exempt from the surcharge) so a future switch (#5855) can be measured.

## Evidence (reconciles to the dollar)

Source: Cursor team usage export `team-usage-events-…-2026-06-29.csv` (single user, 2026-05-31 → 2026-06-28, 32,966 events, all `composer-2.5`, Max Mode "No", almost all "On-Demand"). Total billed = **$14,898.36** over **31.49B tokens** (91% cache read).

- larch standard-rate estimate for the same window = **$6,320**.
- Bridge: `$6,320 × 1.98 (rate) × 1.19 (token capture) = $14,898` — closes exactly.
- Implied flat surcharge = `(14,898 − base-rate 7,555) ÷ 31.49B = $0.233/M` ≈ the documented **$0.25/M** Cursor Token Rate. Per-event least-squares regression (R²=0.998, no per-request fee) gives effective cache-read **~$0.45/M** = base $0.20 + $0.25, and input **~$0.73/M** = base $0.50 + $0.23.

Cursor docs confirm the mechanism: the **$0.25/M Cursor Token Rate applies to all non-Auto agent requests, on all tokens including cached, for Teams plans** (`cursor.com/docs/account/teams/pricing`). larch invokes Cursor with `--model composer-2.5` (a non-Auto request via `resolve_model_args` in `python/larch/agents/_launch_failure.py`), so the surcharge applies to every Cursor token larch spends.

## The two pricing models to support

| Mode | Input | Cache read | Output | Teams $0.25/M surcharge? |
|---|---|---|---|---|
| **Non-auto** `composer-2.5` (today) | $0.50 + $0.25 = **$0.75** | $0.20 + $0.25 = **$0.45** | $2.50 + $0.25 = **$2.75** | yes (per token) |
| **Auto** (flat rate card) | **$1.25** (incl. cache write) | **$0.25** | **$6.00** | no (exempt) |

## Current behavior / defect

- `python/larch/report/report_tokens_cost.py` `DEFAULT_RATE_TABLE_PER_M[("cursor","composer-2.5")]` = `{input:0.50, cache_read:0.20, output:2.50}` — base list only, no Teams surcharge. Because cache reads are ~91% of Cursor tokens, the missing $0.25/M on cache reads alone more than doubles the real cost; the lane is reported at ~half actual.
- Cursor token rows carry **no model/mode field** (see `BUCKETS_cursor` in `python/larch/report/tokens.py`; no `BUCKETS_cursor_by_model`), so the report cannot tell auto from a pinned model and always prices at the cheapest base tier.

## Proposed work

1. **Account for the Teams Cursor Token Rate in non-auto pricing.** Add a configurable per-token surcharge (default $0.25/M, env-overridable) applied to input, cache-read, and output for non-auto Cursor models. Net effective composer-2.5 = $0.75 / $0.45 / $2.75. Keep it a named constant with a comment citing the empirical derivation and the docs URL, since it is plan-tier-specific and may drift.
2. **Add an Auto rate card.** Introduce an `("cursor","auto")` rate row (or equivalent) = $1.25 / $0.25 / $6.00, **not** subject to the Token Rate surcharge. Auto bills input+cache-write together; model that bucket accordingly.
3. **Record the Cursor mode/model per invocation** so the report can price per mode. Emit the resolved model (or `auto`) into the Cursor token sidecar/ledger row in the launcher, mirror it into `BUCKETS_cursor_by_model` in the report builder, and key pricing on it (parallel to the existing `BUCKETS_codex_by_model` path).
4. **Env overrides** already exist (`LARCH_CURSOR_INPUT_RATE_PER_M`, `LARCH_CURSOR_CACHE_READ_RATE_PER_M`, `LARCH_CURSOR_OUTPUT_RATE_PER_M`); ensure the surcharge and auto path respect them, and add an override for the Teams surcharge itself.

## Affected files

- `python/larch/report/report_tokens_cost.py` — rate table, surcharge application, auto rate card, `display_rates`/`rate_row`.
- `python/larch/report/tokens.py` — capture and propagate Cursor mode/model; add `BUCKETS_cursor_by_model`.
- `python/larch/agents/_launch_failure.py` (`resolve_model_args`) and the Cursor launcher / sidecar writer — emit the resolved model/mode into the token record.
- `python/larch/core/config.py` — `CURSOR_DEFAULT_MODEL`, new Teams-surcharge and auto-rate constants.
- Pricing/report tests under `python/` (rate-table, per-bucket, and mode-split coverage).

## Acceptance criteria

- Pricing composer-2.5 (non-auto) Cursor tokens yields the surcharged effective rates ($0.75 / $0.45 / $2.75); re-pricing the June token totals reproduces ~$12.5K for the lane (vs ~$6.3K today), and the windowed reconciliation lands within a few percent of the $14,898 bill after accounting for the ~16% capture gap (tracked separately).
- Auto-mode Cursor tokens price at $1.25 / $0.25 / $6.00 with no surcharge.
- A run's committed report can distinguish auto vs pinned-model Cursor usage.
- Env overrides and the documented defaults are unit-tested.

## Open questions

- Is the $0.25/M surcharge applied identically to cache-write (Auto bundles input+cache-write) — confirm the Auto bucket mapping against a future Auto usage export.
- Should the surcharge be modeled as a flat additive constant per token, or folded into each category rate? Additive is closer to the docs ("list price + Cursor Token Rate").
- Output effective rate from regression was noisy ($2.75 expected vs ~$3.26 fit, on 0.66% of tokens); treat $2.75 (base + surcharge) as authoritative unless a cleaner fit emerges.

## Related

- #5853 — retro-fix the dollar figures already embedded in committed run logs (depends on the corrected rates from this issue).
- #5855 — operational decision to switch the Cursor lane to Auto (needs this issue's auto pricing to measure the savings).
- #5852 — separate but adjacent bug in the same machinery (`<vendor>.totals.cache_read` serialized as null).

## Test plan
(no test plan section in plan-file)
