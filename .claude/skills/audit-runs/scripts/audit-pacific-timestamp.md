# .claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh — contract

Emits the current Pacific time as an ISO 8601 timestamp with explicit UTC offset.

## Output KV (stdout)

```
PACIFIC_TIMESTAMP=2026-05-20T21:59-07:00
```

Offset is `-07:00` (PDT, Apr–Oct) or `-08:00` (PST, Nov–Mar). Uses `TZ=America/Los_Angeles` when available; falls back to a simplified month-based heuristic; last resort is UTC.

## Edit-in-sync

No external behavior dependencies; no test suite entry needed unless offset detection changes significantly.
