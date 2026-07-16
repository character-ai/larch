## Goal
Implement issue #7487: [IMPLEMENTING] contract-unification [DEDUP] Centralize report-token vendor bucket descriptors.

## Implementation Plan
#### Problem

Report-token scanning, cost calculation, and difficulty calibration separately maintain vendor token-bucket names and legacy fallback totals. Claude input, output, cache-read, and cache-creation fields appear in several modules, so a new bucket or fallback rule can change cost reports without changing calibration totals.

#### Goal

Define canonical per-vendor bucket descriptors and effective-total helpers beside `VendorTotals`. Migrate `report_tokens_scan`, `report_tokens_cost`, and difficulty calibration without changing supported input formats or rate environment variables. Preserve legacy cache fallback behavior through explicit tests. Do not combine unrelated pricing policy with scan schema ownership.

#### Required implementation

- Define descriptors for `claude`, `claude_sub`, `codex`, and `cursor` in `report_tokens_models.py` or a cycle-free sibling. Preserve vendor order from `VENDORS`.
- Claude and `claude_sub` components are `input`, `cache_read`, `cache_create`, `cache_create_5m`, `cache_create_1h`, and `output`; Codex uses `input`, `cached_input`, and `output`; Cursor uses `input`, `cache_read`, and `output`.
- Centralize `BUCKETS_<vendor>` versus `<vendor>.totals` fallback. A present totals field wins; a missing totals field may fall back to buckets as today.
- Centralize effective total: prefer nonzero bucket components; for Claude use split cache-create values when either split is present, otherwise legacy `cache_create`; fall back to explicit `total` only when components are zero.
- Keep price multiplication in the cost module, but feed it canonical effective components. Preserve Claude legacy `cache_create` pricing at the 5m rate and `claude_sub` pricing at Claude rates.
- Migrate `report_tokens_scan.py`, `report_tokens_cost.py`, and `calibration/difficulty_calibration.py`. Remove local key tuples and duplicated fallback arithmetic.
- Do not change rate env names, report JSON schema, rounding, model-specific Codex splits, or issue/report presentation.

#### Verification

Use shared fixtures for bucket-only, totals-only, partial totals with bucket fallback, split and legacy Claude cache creation, explicit total fallback, zero and malformed values, `claude_sub`, Codex cached input, and Cursor cache read. Assert scan, displayed cost, and calibration token totals agree.

#### Size and acceptance

Expected change: 700-1,100 lines. Table-driven fixtures must prove scan, cost, and calibration use the same bucket membership and fallback totals for Claude, Codex, Cursor, missing fields, and mixed legacy records.

## Test plan
(no test plan section in plan-file)
