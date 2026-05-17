# test-flush-execution-issues.sh

Offline harness for `skills/implement/scripts/flush-execution-issues.sh`.

It runs the helper in a temporary plugin/repo sandbox with stubbed
`larch-log.sh` and `append-tool-failure.sh`, then verifies empty-input skip,
single-section and multi-section NDJSON composition, idempotent rerun behavior,
and the append-failure path that records `larch-log.sh` output back into
`execution-issues.md`.
