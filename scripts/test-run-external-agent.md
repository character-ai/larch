# scripts/test-run-external-agent.sh - contract

Regression harness for `scripts/run-external-agent.sh`; the primary behavioral contract lives in `scripts/run-external-agent.md`.

## Coverage

- Verifies a normal `--capture-stdout` run writes output, `.done`, and `.meta` with the expected `OUTPUT_FILE=`.
- Verifies unsafe `--output` values containing `=`, LF, CR, TAB, DEL, spaces, and UTF-8 bytes exit 1 before creating `<output>`, `<output>.done`, `<output>.meta`, or `<output>.diag`.
- Verifies safe nested paths and dot/dash/underscore path components are accepted.
- Verifies empty `--output` is rejected by wrapper argv validation.
- Verifies `scripts/lib-validate-meta-path.sh` is sourced-only, non-executable, silent when sourced, and idempotent when sourced twice.

## Wiring

Target: `make test-run-external-agent`. Included in `make lint` via the `test-harnesses-5` shard. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

Update with `scripts/run-external-agent.sh`, `scripts/run-external-agent.md`, `scripts/lib-validate-meta-path.sh`, `scripts/lib-validate-meta-path.md`, and `scripts/launch-gemini-review.sh` when the `.meta` output-path validation contract changes.
