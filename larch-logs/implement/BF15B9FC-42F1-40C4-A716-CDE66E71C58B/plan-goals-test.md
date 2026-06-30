## Goal
Implement issue #5852: [IMPLEMENTING] [BUG] Vendor totals.cache_read serialized as null in token-report.json….

## Implementation Plan
## Summary

In committed `token-report.json` files, the per-vendor `totals.cache_read` field is serialized as JSON `null` for the externally-spawned vendor lanes (`cursor`, `codex`, `claude_sub`) in a sizable minority of runs, even though the same object's `total` is correct and the parallel `BUCKETS_<vendor>` block carries the real `cache_read` value. Consumers that read `report["<vendor>"]["totals"]["cache_read"]` coerce `null` to `0` and therefore under-count cache-read tokens for those lanes. Cost/pricing dollars are not affected because the pricer reads `BUCKETS_<vendor>` when present, but any consumer of the `totals` object under-reports.

## Original report

"One real bug to fix regardless": the canonical report's `cursor.totals.cache_read` (19.03B summed across June `/design` + `/implement`) disagrees with `BUCKETS_cursor.cache_read` (23.58B) by ~4.55B tokens — `totals.total` carries cache-read tokens that the component `cache_read` field does not. Pricing uses `BUCKETS`, so the dollar figure is unaffected, but `cursor.totals` is internally inconsistent and will mislead anything that reads it. Surfaced while reconciling a Cursor bill against larch cost reports.

## Reproduction scenario

Read-only inspection of committed run logs in this repo (no mutation required):

1. For each `larch-logs/implement/*/token-report.json` whose `manifest.json` `started_at` is in `2026-06`, parse the JSON.
2. For each vendor in `claude`, `codex`, `cursor`, `claude_sub`, read `report[vendor]["totals"]`.
3. Compare `totals["cache_read"]` against `BUCKETS_<vendor>["cache_read"]`, and check whether `totals["cache_read"]` is `null`.

Observed across 752 June `/implement` canonical reports:

- `cursor`: 109 runs with `totals.cache_read == null`
- `codex`: 98 runs with `totals.cache_read == null`
- `claude_sub`: 88 runs with `totals.cache_read == null`
- `claude`: 0 (main-agent transcript lane is unaffected)
- `totals.total` is never `null` for any vendor.

Aggregate effect for `cursor` alone: `sum(BUCKETS_cursor.cache_read) - sum(cursor.totals.cache_read)` over June `/implement` ≈ 4.12B tokens (≈4.55B including `/design`).

## Expected behavior

`report[vendor]["totals"]["cache_read"]` is a non-null integer for every vendor lane, and `totals.input + totals.cache_read + totals.output == totals.total` (cursor/codex shape). The `totals` view and the `BUCKETS_<vendor>` view agree on `cache_read`.

## Observed behavior

For `cursor`, `codex`, and `claude_sub`, `totals.cache_read` (and in the same records `cache_create` / `cached_input`) is serialized as `null` in ~13-19% of runs, while `input`, `output`, and `total` are correct integers. Because `total` still includes the cache-read tokens, `input + cache_read + output < total` by the dropped cache-read amount when `cache_read` is read as `0`.

Example records (canonical `larch-logs/implement/<RUN_ID>/token-report.json`):

- `7DBF6E99-8AC8-4BBF-BDE3-577D5A610C34`: `BUCKETS_cursor = {input: 7274822, cache_read: 80816722, output: 446446, total: 88537990}` vs `cursor.totals = {input: 7274822, cache_read: null, cache_create: null, cached_input: null, output: 446446, total: 88537990}`.
- `D8212A9C-8D3F-4CDE-AC1C-EB353908F4F9`: `BUCKETS_cursor.cache_read = 23944048` vs `cursor.totals.cache_read = null` (total 26966948 correct).

## Root cause analysis

Not fully pinned; stated as a hypothesis with supporting evidence.

The live in-run report builders produce correct integers: `_totals()` (python/larch/report/tokens.py) returns `TokenLedgerTally.to_dict()` with an integer `cache_read` (0 when empty), and `_per_step_json()` / `_full_json()` build both `<vendor>.totals` and `BUCKETS_<vendor>` from that same `_totals()` output. A freshly built report from those functions cannot have `cache_read == null`.

Therefore the `null` is introduced after the live build — most likely a re-render/refresh/merge of the canonical `token-report.json` (e.g., the ship driver re-rendering canonical batches from the in-loop `token-report-refresh.json` sidecar, or a JSON merge of a partial report) where the external-vendor `totals.cache_read` is sourced from a key that returns `None` (a field-name mismatch such as `cache_read` vs `cache_read_tokens`, or a partial-overwrite that omits `cache_read`) while `input`/`output`/`total` map correctly. The fact that only the externally-spawned lanes (`cursor`/`codex`/`claude_sub`) are affected and the `claude` transcript lane is not is consistent with a shared external-lane serialization path distinct from the claude path.

## Evidence

- Per-vendor null counts over 752 June `/implement` canonical reports: cursor 109, codex 98, claude_sub 88, claude 0; `total` null count 0 for all.
- Two concrete example run dirs above show `BUCKETS_<vendor>.cache_read` populated while `<vendor>.totals.cache_read` is `null` with a correct `total`.
- `python/larch/report/tokens.py`: `_totals()` (around the `TokenLedgerTally` aggregation) and `_per_step_json()` always emit integer `cache_read`; `BUCKETS_cursor` is built as `{input, cache_read, output, total}` from `_totals()` and is correct in the same files.
- Consumer coercion: `python/larch/report/report_tokens_scan.py` `_totals()` reads `safe_int(value=totals.get("cache_read"))`, and `safe_int(None) == 0`, so the null silently becomes a 0 cache-read for that lane when the `totals` view is used.
- Pricing is shielded: `python/larch/report/report_tokens_cost.py` `token_cost_argv()` prefers `BUCKETS_<vendor>` when present, so per-run dollar figures computed by `/report-tokens` are not affected by this bug; the harm is to any consumer of the `totals` object.

## Affected files

- `python/larch/report/tokens.py` — report serialization; the suspected re-render/refresh/merge path that writes `<vendor>.totals` with a null `cache_read`. Primary fix site.
- `python/larch/report/run_logs.py` — flush/refresh lifecycle for `token-report.json` (`flush_logs_pre` and the pre-ship/refresh re-render that consumes `token-report-refresh.json`); likely where the re-render is invoked.
- `python/larch/report/report_tokens_scan.py` — consumer; `_totals()` turns the null into 0, masking the defect and under-counting when `BUCKETS` is absent.

## Suggested fix(es)

- Fix the writer so external-vendor `totals.cache_read` (and `cache_create` / `cached_input`) serialize as integers, not `null`. Source them from the same `_totals()` result used for `BUCKETS_<vendor>`, or re-derive `cache_read = total - input - output` for the cursor/codex shape when re-rendering.
- Add an invariant/regression test on built and re-rendered reports: for every vendor, `totals` numeric fields are non-null ints and `input + cache_read + output == total` (cursor/codex) / the claude-shape equivalent. Cover the refresh re-render path specifically, since the live build path already passes.
- Defense-in-depth in consumers: when `totals.cache_read` is null/missing, fall back to `BUCKETS_<vendor>.cache_read` (or `total - input - output`) rather than coercing to 0.
- Historical backfill of committed reports is optional and not required for correctness, because `BUCKETS_<vendor>` already carries the right value; prefer fixing the writer and the consumer fallback over rewriting committed logs.

## Open questions

- Which exact writer introduces the null — the in-loop refresh re-render (`token-report-refresh.json` to `token-report.json`), a JSON merge of a partial report, or another path? Pin the line.
- Are `cache_create` and `cached_input` nulls in the same records a separate symptom or the same root cause (they appear together for the external lanes)?
- Should consumers (`report_tokens_scan._totals`, final-summary token totals, markdown token report) adopt the BUCKETS-first fallback regardless of the writer fix, to harden against null totals in already-committed logs?

## Test plan
(no test plan section in plan-file)
