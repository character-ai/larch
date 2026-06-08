# render-findings-view.sh

Renders a dropped markdown findings view from `review-findings-full.jsonl` on demand.

## Usage

```
render-findings-view.sh <larch-logs/implement/RUN_ID/> [accepted|rejected|oos|all]
```

Outputs one `### FINDING` block per matching record to stdout.
Exits 1 when `review-findings-full.jsonl` is absent (legacy runs that predate the jsonl retain their original markdown files).

## Why this exists

Phase 3a of the logs-size-reduction series drops `round-N/findings.md`, `round-N/accepted-findings.md`, `round-N/oos.md`, and `round-N/rejected-findings-full.md` from committed run logs; `review-findings-full.jsonl` is the canonical store from which all views are projections. This helper reconstructs any dropped view on demand so browsing convenience survives the deletion.

## Callers

Ad-hoc operator use only. Not invoked by any larch script.

## Edit-in-sync

Update this file when the CLI interface or output format of `render-findings-view.sh` changes.
