# scripts/test-launch-gemini-review.sh — contract

Regression harness for `scripts/launch-gemini-review.sh`.

## Coverage

- Stubs `gemini` on PATH and verifies JSON `.response` is normalized to plain text.
- Verifies a requested 1800-second timeout is clamped to 600 seconds in the raw launcher metadata.
- Verifies `{"error": ...}` fails closed with empty output, diagnostic text, and non-zero `.done`.
- Verifies forced missing-`jq` fails closed with `MISSING_JQ` and exit code 127 in `.done`.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

Update with `scripts/launch-gemini-review.sh`, `scripts/run-external-agent.sh`, and the Gemini CLI JSON schema.
