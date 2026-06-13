## Decision 1: Item 2 fix target
- **Question**: Which file(s) need updating to remove the rate-table second authority?
- **Resolution**: Fix `test_display_rates_shipped_defaults_snapshot` in `python/test_report_tokens_cost.py` to reference `DEFAULT_RATE_TABLE_PER_M` instead of hardcoding values. Golden fixture files use hardcoded test costs and don't embed the rate table.
- **Source**: codebase

## Decision 2: Item 6 fix approach
- **Question**: Prose update to SKILL.md or new script?
- **Resolution**: Prose update to `skills/research/references/research-phase.md` — add explicit ingestion steps after the collection step for each successful Codex lane.
- **Source**: codebase + user deferral

## Decision 3: Items 4 and 7 scope overlap
- **Question**: Does Item 7 require a separate ship.py fix beyond the checks.py change?
- **Resolution**: Items 4 and 7 describe the same gap. Fixing `_run_codex` in `python/checks.py` to add NDJSON append covers both.
- **Source**: codebase + user deferral

## Decision 4: Item 3 fix approach
- **Question**: How to surface the NDJSON/active-ledger split for unknown TOOL?
- **Resolution**: Add a stderr warning in `record_vendor_from_sidecar` when vendor is "unknown" (after parse). Minimal, non-data-loss approach.
- **Source**: codebase
