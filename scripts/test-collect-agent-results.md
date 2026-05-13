# scripts/test-collect-agent-results.sh - contract

`scripts/test-collect-agent-results.sh` is the regression harness for
`scripts/collect-agent-results.sh` transient-network retry routing. It creates
synthetic reviewer outputs, `.done` sentinels, `.diag` diagnostics, and valid
`.meta` retry sidecars, then drives the real collector with PATH-stubbed Cursor
metadata.

Cases:

- **C_T1**: `STATUS=FAILED` plus a transient DNS diagnostic retries once and
  recovers to `STATUS=OK` with `REVIEWER_FILE=*-retry.txt`.
- **C_T2**: the same transient initial failure retries, but a failing retry
  returns `STATUS=EMPTY_OUTPUT|HEALTHY=false` with a `Retry also failed:`
  reason.
- **C_T3**: non-transient `STATUS=FAILED` (`reviewer prompt malformed`) does
  not retry, even with valid `.meta`.
- **C_T4**: `STATUS=SENTINEL_TIMEOUT` plus a transient TLS diagnostic retries
  once and recovers.
- **C_T5**: `STATUS=SENTINEL_TIMEOUT` without a transient diagnostic remains a
  timeout and creates no retry artifact.

The full collector contract lives in `scripts/collect-agent-results.md`. This
harness is wired through the `test-collect-agent-results` Makefile target and a
`test-harnesses` shard. Update this file when changing
`is_transient_net_signature`, the statuses eligible for transient retry, or the
collector's retry-row result semantics.
