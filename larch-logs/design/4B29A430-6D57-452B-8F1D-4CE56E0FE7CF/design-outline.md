## Proposed Design Outline

### Goals
- Add a read-only `token measure-cache-efficiency` subcommand that ranks cache_create/cache_read outliers from committed token reports.
- Emit two ranked tables: per-run (whole-run ratio) and per-step (aggregated by skill + step name across all runs).
- Document the new command in `docs/run-logs.md`.

### Non-goals
- No changes to token capture, the ledger writer, or `token-report.json` / `token-report-final.json` shape.
- No fix for the underlying prompt-prefix instability. Measurement only; fixes are follow-up issues.
- No new CI lint or ratchet gate. Sibling `measure-*` commands are on-demand tools, not CI-enforced.

### Approach sketch
- New `measure_cache_efficiency()` in `python/larch/report/tokens.py`, mirroring `measure_realized_cost()` / `measure_references_heatmap()`.
- Reuse `report_tokens_scan.scan()` per discovered skill directory to read committed `token-report{,-final}.json` (with its existing ledger fallback), then read per-step `cache_read` / `cache_create_5m` / `cache_create_1h` from `RunRecord.raw_report["claude"]["per_step"]` and the `"claude_sub"` lane.
- Rank by cache_create : cache_read ratio, descending. Guard divide-by-zero (no cache_read yet nonzero cache_create ranks first; no cache activity at all is excluded).
- Wire as `("token", "measure-cache-efficiency")` in the `cli.py` registry, matching sibling `measure_*_main()` wrappers.
- Write a dated TSV to `larch-logs/measure-cache-efficiency/<date>.tsv`; print `WROTE\t<relpath>`, matching sibling commands.

### Surfaces in scope
- `python/larch/report/tokens.py`
- `python/larch/cli.py`
- `python/tests/report/test_tokens.py`
- `docs/run-logs.md`

### Open questions
- None.
