# skills/implement/scripts/test-implement-review-token-propagation.sh — contract

Offline harness for token telemetry propagation across `/implement` Step 5's `review-and-fix.sh` boundary.

## Coverage

- Builds a parent `/implement`-style session-env containing `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE`.
- Runs `scripts/session-setup.sh --caller-env ... --write-session-env ...` and asserts both keys survive the bounded caller-env allow-list.
- Asserts `LARCH_TIMING_LEDGER` survives the same caller-env to writer round-trip only when it is under an accepted root.
- Asserts `LARCH_TIMING_LEDGER` does not appear on `session-setup.sh` stdout.
- Rehydrates the keys with `scripts/read-session-env-key.sh`, runs `skills/review-and-fix/scripts/review-and-fix.sh --implement-tmpdir` with a stubbed `review-core.sh`, and asserts the review-core subprocess sees the parent token session id, Claude source file, timing ledger, and implement session-env path.

## Edit-in-sync

Update with `scripts/session-setup.sh`, `scripts/session-setup.md`, `scripts/write-session-env.sh`, `skills/review-and-fix/scripts/review-and-fix.sh`, `skills/review/scripts/review-core.sh`, and `skills/shared/subskill-invocation.md` when changing nested review session-env propagation.
