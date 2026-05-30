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
  returns `STATUS=EMPTY_OUTPUT  reason.
- **C_T3**: non-transient `STATUS=FAILED` (`reviewer prompt malformed`) does
  not retry, even with valid `.meta`.
- **C_T4**: `STATUS=SENTINEL_TIMEOUT` plus a transient TLS diagnostic retries
  once and recovers.
- **C_T5**: `STATUS=SENTINEL_TIMEOUT` without a transient diagnostic remains a
  timeout and creates no retry artifact.
- **C_NSR**: narrative-only output (detected as `STATUS=NOT_SUBSTANTIVE` by the
  substantive validator) with a valid `.meta` triggers a section 3.7 retry
  attempt; the test verifies `STATUS=NOT_SUBSTANTIVE` is emitted and the retry
  sentinel is written (when the outer launcher executes in the test environment).
- **C_NSS**: a section 3.6 structured-reviewer downgrade retries even when the
  collector is running the structured validator path, and restores
  `STATUS=OK` only after the retry re-emits a valid structured sidecar.

The full collector contract lives in `scripts/collect-agent-results.md`. This
harness is wired through the `test-collect-agent-results` Makefile target and a
`test-harnesses` shard. Update this file when changing
`is_transient_net_signature`, the statuses eligible for transient retry, or the
collector's retry-row result semantics.

Additional cases exercise `--paths-file`: stdout parity with positional args, mutual exclusion with positionals, empty / whitespace-only file rejection, missing file rejection, and the legacy zero-argument guard.

The harness unsets inherited session tempdir variables and points
`LARCH_EXECUTION_ISSUES_LOG` at its tempdir so failures cannot append to a
parent `/implement` run's log.

**WAIT_STDERR relay sanitize case**: builds a minimal `SCRIPT_DIR` tree (real
`collect-agent-results.sh` copy plus stub sibling `wait-for-reviewers.sh`, not
PATH-only), captures merged `2>&1`, and asserts printable text preserved with
BEL/ESC absent on the relay path.
