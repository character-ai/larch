# .claude/skills/audit-runs/scripts/audit-pacific-timestamp.sh — contract

Emits the current Pacific time as an ISO 8601 timestamp with explicit UTC offset.

## Output KV (stdout)

```
PACIFIC_TIMESTAMP=2026-05-20T21:59-07:00
PACIFIC_TIMESTAMP_SOURCE=tz_america_los_angeles
```

`PACIFIC_TIMESTAMP_SOURCE` is `tz_america_los_angeles` when `TZ=America/Los_Angeles` succeeds, otherwise `utc_fallback` (timestamp is then UTC `Z` minute-precision — **not** Pacific wall time; treat as a last-resort clock for titling/metadata only).

## Unknown argv

Extra arguments exit `1` with stderr only — **no** `PACIFIC_TIMESTAMP=` line on stdout (parse failure, not a usable timestamp).

## Edit-in-sync

No external behavior dependencies; no test suite entry needed unless offset detection changes significantly.
