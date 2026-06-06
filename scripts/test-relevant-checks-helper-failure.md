# test-relevant-checks-helper-failure.sh

Purpose: regression-test the red path and `LARCH_QUIET_*` scrub of `scripts/run-relevant-checks-captured.sh`.

The harness builds a failing project-local `run-checks.sh`, asserts the helper preserves the underlying non-zero exit code, emits the structured failure envelope, writes both raw and redacted logs, redacts tmpdir and token-shaped content from the redacted artifact, and fail-closes without `LOG_FILE=` when the redaction utility is unavailable. It also contains a regression pin that exports the full `LARCH_QUIET_*` family and asserts the helper returns green (the central scrub removes the vars before the checks script runs, so harnesses are not affected).

Primary callers: `make test-relevant-checks-helper-failure` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/run-relevant-checks-captured.sh` and `scripts/run-relevant-checks-captured.md` whenever failure stdout grammar, redaction order, phase detection, or fail-closed behavior changes.
