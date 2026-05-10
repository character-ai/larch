# scripts/test-run-external-agent.sh - contract

Regression harness for `scripts/run-external-agent.sh`; the primary behavioral contract lives in `scripts/run-external-agent.md`.

## Coverage

- Verifies a normal `--capture-stdout` run writes output, `.done`, and `.meta` with the expected `OUTPUT_FILE=`.
- Verifies unsafe `--output` values containing `=`, LF, CR, TAB, DEL, spaces, and UTF-8 bytes exit 1 before creating `<output>`, `<output>.done`, `<output>.meta`, or `<output>.diag`.
- Verifies safe nested paths and dot/dash/underscore path components are accepted.
- Verifies empty `--output` is rejected by wrapper argv validation.
- Verifies `scripts/lib-validate-meta-path.sh` is sourced-only, non-executable, silent when sourced, and idempotent when sourced twice.
- Verifies the `jq` `CMD_JSON` serialization-failure path: with a `PATH`-prefixed stub `jq` that exits non-zero, the wrapper exits `1`, stderr contains `ERROR: jq failed to serialize argv to CMD_JSON`, `<output>.done` records `1` (not the pre-launch default `99`), and `<output>.meta` is not written. Pins the `EXIT_CODE=1` assignment that synchronizes the trap-written sentinel with the real exit status on this branch.
- Verifies `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done` writes `<output>.inner.done` without publishing `<output>.done`, default mode still publishes `<output>.done`, stale cleanup removes both sentinel flavors, and unsupported suffixes fail before side effects.

## Wiring

Target: `make test-run-external-agent`. Included in `make lint` via the `the test-harnesses-N shard partition` shard. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

Update with `scripts/run-external-agent.sh`, `scripts/run-external-agent.md`, `scripts/lib-validate-meta-path.sh`, `scripts/lib-validate-meta-path.md`, `scripts/launch-review.sh --tool cursor`, and `scripts/launch-review.sh --tool gemini` when the `.meta` output-path validation or sentinel contract changes.
