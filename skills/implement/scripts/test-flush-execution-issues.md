# test-flush-execution-issues.sh

Offline harness for `skills/implement/scripts/flush-execution-issues.sh`.

It runs the helper in a temporary plugin/repo sandbox with stubbed
`run-log` and `run-log append-failure`, then verifies empty-input skip,
single-section and multi-section NDJSON composition, idempotent rerun behavior,
and the append-failure path that records `run-log` output back into
`execution-issues.md`.
