# scripts/write-session-env.sh — contract

Writes a `KEY=value` session-env file atomically for child skills. The file is not escaped and is not safe to source; consumers must parse it through `session-setup.sh --caller-env` or `read-session-env-key.sh`.

## Keys

Always writes `SLACK_OK`, `SLACK_MISSING`, `REPO`, and `REPO_UNAVAILABLE`. Optionally writes reviewer health booleans:

- `CODEX_HEALTHY`
- `CURSOR_HEALTHY`
- `GEMINI_HEALTHY`

It may also write `LARCH_TIMING_LEDGER` when the caller passes `--timing-ledger <path>`. `/implement` uses this durable key so nested `/design` and `/review` invocations continue appending to the parent timing ledger after session-env rewrites.

It may also write `LARCH_TOKEN_SESSION_ID` when the caller passes `--token-session-id <id>` and `LARCH_CLAUDE_SOURCE_FILE` when the caller passes `--claude-source-file <path>`. `/implement` writes both keys so every orchestrator-side token-ledger / token-report Bash block can rehydrate the parent run's token context, and `/review` can forward that context to nested review launchers. `/fix-issue` does not pass these keys; `/implement` always establishes its own token session id and Claude source snapshot.

Values must stay narrow and caller-controlled (`true|false` for health and Slack booleans; validated repo strings for repo identity; caller-owned tmp paths for timing ledgers). `--token-session-id` must match `^[A-Za-z0-9_.-]{1,128}$`; `--claude-source-file` must match `^[A-Za-z0-9_./~+-]{1,512}$`. Empty optional values are omitted from the file.

## Invariants

- Atomic temp+mv for regular paths.
- `/dev/null` is a no-op sink.
- Do not add arbitrary user text fields without adding escaping and read-side regression coverage.
- The output remains raw `KEY=value`, not shell-quoted shell syntax.

## Edit-in-sync

Update `scripts/session-setup.sh`, `skills/shared/subskill-invocation.md`, and every producer/consumer skill when adding session-env keys.
