# write-implement-round-meta.sh

Synthesizes `round-meta.json` in an `/implement` code-review round directory
from the new-format artifacts written by the review pipeline. Called from
`review-and-fix.sh` (`_implement_round_body`) immediately before
`flush_round_log_after_coder` so the file is present when `write-round` copies
round artifacts to the larch-log.

## Why

`render-review-phase-detail.sh` (called by `write-final-report.sh` at Step 17)
gates every round on the presence of `round-meta.json` (line 80). Without it
the Review Phase Detail table is never emitted in the final report, even when
panel code review ran multiple rounds with accepted findings (issue #4038).

## Inputs

All inputs are read from `--round-dir DIR`:

| File | Role |
|---|---|
| `voting-tally.md` | Finding/OOS outcome counts (primary; `## Findings` section header required). Implement rounds use `## Per-finding vote breakdown`, so this always falls back to the TSV. |
| `findings-classification.tsv` | Finding/OOS outcome counts (fallback when tally returns all zeros). Implement rounds always hit this path. |
| `panel-manifest.ndjson` | Reviewer slot count (`summary.panel.total_slot_count`). |

## Output

Writes `round-meta.json` to `--round-dir`:

```json
{
  "tally": {
    "ACCEPTED_COUNT": "5",
    "REJECTED_COUNT": "3",
    "EXONERATED_COUNT": "1",
    "NEUTRAL_COUNT": "0",
    "OOS_ACCEPTED_COUNT": "2",
    "OOS_REJECTED_COUNT": "1"
  },
  "summary": {
    "panel": { "total_slot_count": 12 }
  },
  "collector": ""
}
```

Counts are string-typed to match the format consumed by
`render-review-phase-detail.sh`'s `num()` jq helper. The `collector` field is
left empty; implement rounds do not have a `round-summary.env` equivalent.

## Callers

- `skills/review-and-fix/scripts/review-and-fix.sh` (`_implement_round_body`,
  before `flush_round_log_after_coder`)

## Analog

`scripts/write-design-round-meta.sh` — same output schema for `/design`
plan-review rounds.

## Allow-list

`round-meta.json` is listed in `_ROUND_ARTIFACT_ALLOW` in `python/run_logs.py`
so `python/cli.py run-log write-round` copies it to the larch-log directory.

## Exit behavior

Best-effort: always exits 0. On missing inputs or tool failures, no
`round-meta.json` is written (the caller's `|| true` guard absorbs the exit).
