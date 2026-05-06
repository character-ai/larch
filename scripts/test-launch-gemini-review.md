# scripts/test-launch-gemini-review.sh — contract

Regression harness for `scripts/launch-gemini-review.sh`.

## Coverage

- Stubs `gemini` on PATH and verifies JSON `.response` is normalized to plain text.
- Verifies a requested 1800-second timeout is clamped to 600 seconds in the raw launcher metadata.
- Verifies reviewer Gemini argv includes `--admin-policy <path-ending-in-gemini-reviewer-policy.toml>` and that the policy path exists and is non-empty.
- Verifies `{"error": ...}` fails closed with empty output, diagnostic text, and non-zero `.done`.
- Verifies the fail-closed process exit code matches `.done` on Gemini `.error`, empty `.response`, and missing-`jq` paths.
- Verifies forced missing-`jq` fails closed with `MISSING_JQ` and exit code 127 in `.done`.
- Verifies unsafe `--output` values containing `=` and LF exit 2 before creating normalized or raw output artifacts.

## Wiring

Target: `make test-harnesses`. Exit 0 on all-pass, exit 1 on any failure.

## Edit-in-sync

Update with `scripts/launch-gemini-review.sh`, `scripts/gemini-reviewer-policy.toml`, `scripts/run-external-agent.sh`, `scripts/lib-validate-meta-path.sh`, and the Gemini CLI JSON schema.
