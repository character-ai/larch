# skills/implement/scripts/test-implement-review-token-propagation.sh — contract

Offline harness for token telemetry propagation across the nested `/implement` → `/review` boundary.

## Coverage

- Builds a parent `/implement`-style session-env containing `LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE`.
- Runs `scripts/session-setup.sh --caller-env ... --write-session-env ...` in `/review` mode and asserts both keys survive the bounded caller-env allow-list.
- Rehydrates the keys with `scripts/read-session-env-key.sh`, launches `scripts/launch-cursor-review.sh` with a PATH-stubbed Cursor binary, and asserts the launcher subprocess sees the parent token session id.

## Edit-in-sync

Update with `scripts/session-setup.sh`, `scripts/write-session-env.sh`, `scripts/launch-cursor-review.sh`, `skills/review/SKILL.md`, and `skills/shared/subskill-invocation.md` when changing nested review session-env propagation.
