## Goal
Implement issue #5133: [IMPLEMENTING] [BUG] Design runs missing from cost reports: token-report-final.json absent on un-finalized runs.

## Implementation Plan
## Summary

`/report-tokens --skill design` (and any cost analysis over `larch-logs/design/`) silently omits most recent design runs. The cost scanner reads **only** `token-report-final.json` for a design run and skips the directory when that file is absent. Design produces `token-report-final.json` solely at the final-summary render step, so any design run that commits its log tree before finalizing (the interim "flush" path) lands with `plan.txt` + `token-report.ndjson` + `larch-tokens-*.jsonl` but **no** `token-report-final.json`, making it invisible to cost reporting even though the token data is committed and the cost is recoverable.

## Original report

why design run logs are missing cost reports and how to fix

## Reproduction scenario

1. Scan committed design logs for cost: build a `RunRecord` per `larch-logs/design/<RUN_ID>/` via `python/report_tokens_scan.py` (the path `/report-tokens --skill design` uses), or run the equivalent of `python3 python/cli.py report-tokens analyze --skill design --no-issue --no-plot`.
2. Observe that runs whose directory lacks `token-report-final.json` are skipped with `… has no token-report-final.json; skipping`.
3. Inspect those skipped directories: they contain `plan.txt`, `token-report.ndjson`, and `larch-tokens-<hash>.jsonl` (real token data) but no `token-report-final.json` and no `final-summary.md`.

Measured on the current `main` working tree:
- Design runs started on/after 2026-06-15: **121**; exactly **1** has `token-report-final.json`. The other 120 committed `token-report.ndjson` instead.
- Across all design dirs: **177 of 472** are priceable (have `token-report-final.json`); **295 skipped**.
- Implement is far less affected: **873 of 1009** priceable.

## Expected behavior

Cost reporting should account for every design run that has committed token data, regardless of whether the run reached final-summary finalization. A design run that produced a plan and recorded tokens should contribute its cost to `/report-tokens` and any cost-over-time analysis.

## Observed behavior

Design runs that did not finalize are dropped entirely from cost reports. The design cost line in cost-over-time analysis flatlines to near-zero for the last ~2 weeks (1 priceable run since 2026-06-15), and is only ~37% covered historically. The token data exists in the committed tree but is never read.

## Root cause analysis

Two coupled causes:

1. **Reader reads only the finalized file (primary, and the reason the data is invisible).** `python/report_tokens_scan.py::_token_basename` returns `token-report-final.json` for `--skill=design`. `_record` skips the directory when that file is missing or non-numeric, with no fallback to the other committed token artifacts (`token-report.ndjson`, `larch-tokens-*.jsonl`). The skipped runs *do* carry committed token data, so this is a recoverable reporting gap, not lost data.

2. **The finalized file is produced late, only on the finalize path (the reason it is so often absent).** `token-report-final.json` is written exclusively by the design final-summary renderer (`python/design_summary.py`, the `cli.py token report --full --format json --output …/token-report-final.json` call inside `render_final_summary_main`). It is rendered together with `final-summary.md` — confirmed empirically: of recent design runs, every dir with `final-summary.md` has `token-report-final.json`, and **0** have one without the other. Design runs that commit logs before/without finalizing (the `design_publish.py` `flush=True` interim/recovery path, visible as standalone `chore(larch-logs): flush <UUID>` commits) therefore carry `plan.txt` + `token-report.ndjson` but never the finalized report.

This is asymmetric with `/implement`, which writes `token-report.json` at the Step 7a pre-ship flush — much earlier in the lifecycle — so it survives most bail points. Design only materializes its canonical token report at the very end (step5c), so any earlier flush loses it from cost reporting.

A secondary open question is *why* so many design runs since ~2026-06-15 flush without finalizing (status `None`/`partial`, plan present, no final summary). That may be a separate bail/finalization regression worth its own investigation, but it is not required to fix the reporting gap.

## Evidence

- `python/report_tokens_scan.py`: `_token_basename(skill)` → `"token-report-final.json"` for design; `_record` emits `… has no token-report-final.json; skipping` and returns `None` when absent (no fallback).
- `python/design_summary.py`: `token-report-final.json` is referenced only at the final-summary render (`_read_token_report` reads it; `render_final_summary_main` writes it via `cli.py token report --full --format json --output …`). No earlier writer exists in `python/design_*.py`.
- Recent skipped design dir contents, e.g. `larch-logs/design/51ECB46E-…/`: `larch-tokens-<hash>.jsonl`, `timing-ledger.tsv`, `token-report.ndjson` (status `partial`), no `token-report-final.json`. `token-report.ndjson` holds real per-tool token rows, e.g. `{"tool":"codex","input":69824,"output":7203,"cache_read":278656,"total":355683,"model":"gpt-5.5"}`.
- Completeness check over 14 most-recent design dirs: every dir with `final-summary.md` has `token-report-final.json` (YES); every dir with only `plan.txt` lacks both and has `token-report.ndjson`.
- Counts (current `main`): design priceable 177/472; design runs since 2026-06-15 with `token-report-final.json` = 1/121; implement priceable 873/1009.
- The committed `chore(larch-logs): flush <UUID>` commits correspond to these partial design dirs (e.g. `51ECB46E`, `77FF6898`, `EBBE7A6B`).

## Affected files

- `python/report_tokens_scan.py` — design token-report resolution (`_token_basename`, `_record`); add a fallback source so runs with `token-report.ndjson`/`larch-tokens-*.jsonl` but no `token-report-final.json` are priced.
- `python/design_summary.py` — design final-token-report rendering; only writer of `token-report-final.json`, and only on the finalize path.
- `python/design_publish.py` — the `flush=True` interim/recovery commit path that ships design logs without the finalized token report.
- `docs/run-logs.md` — design consumer-core keep set lists `token-report-final.json`; should reflect the chosen fallback / durability behavior.
- `python/report_tokens_models.py` / `python/report_tokens_cost.py` — aggregation shape the fallback must produce (`totals` / `BUCKETS_*` per vendor) for pricing.

## Suggested fix(es)

1. **Reader-side fallback (recovers historical and future data; highest value).** In `report_tokens_scan`, when `token-report-final.json` is absent for a design run, derive the per-vendor `totals`/`BUCKETS` from the committed `token-report.ndjson` (per-tool rows) or the `larch-tokens-*.jsonl` ledger, then price as usual. This recovers all skipped design runs that have committed token data without re-running anything.
2. **Writer-side durability (prevents future gaps).** Ensure the design flush/finalize path always materializes and commits `token-report-final.json` from the token ledger before committing the log tree — including the `design_publish.py` `flush=True` interim/recovery path — so the canonical file is present even when a run does not reach normal finalization. Mirror `/implement`'s earlier pre-ship token-report flush.
3. **Optional symmetry/robustness.** Apply the same fallback for implement (`token-report.json` → `token-report.ndjson`/ledger) so early-bail implement runs are likewise recovered.

## Open questions

- Why have so many design runs since ~2026-06-15 flushed without finalizing (status `None`/`partial`, plan present, no final summary)? Is this a separate design bail/finalization regression, or expected volume of interrupted/design-only runs?
- Canonical fallback source: `token-report.ndjson` (per-tool raw rows) vs `larch-tokens-*.jsonl` (token ledger) — which is authoritative and complete enough to reproduce `token-report-final.json` aggregation?
- Should the GC consumer-core keep set for design also retain the fallback source (`token-report.ndjson` / ledger) so slimming does not destroy recoverable cost data?

## Test plan
(no test plan section in plan-file)
