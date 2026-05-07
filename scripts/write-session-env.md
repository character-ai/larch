# scripts/write-session-env.sh — contract

Writes a shell-readable `KEY=value` session-env file atomically for child skills. The file is not escaped for shell sourcing and must be consumed through `session-setup.sh --caller-env`, which parses line-by-line.

## Keys

Always writes `SLACK_OK`, `SLACK_MISSING`, `REPO`, and `REPO_UNAVAILABLE`. Optionally writes reviewer health booleans:

- `CODEX_HEALTHY`
- `CURSOR_HEALTHY`
- `GEMINI_HEALTHY`

It may also write `LARCH_TIMING_LEDGER` when the caller passes `--timing-ledger <path>`. `/implement` uses this durable key so nested `/design` and `/review` invocations continue appending to the parent timing ledger after session-env rewrites.

Values must stay narrow and caller-controlled (`true|false` for health and Slack booleans; validated repo strings for repo identity; caller-owned tmp paths for timing ledgers).

## Invariants

- Atomic temp+mv for regular paths.
- `/dev/null` is a no-op sink.
- Do not add arbitrary user text fields without adding escaping and read-side regression coverage.

## Edit-in-sync

Update `scripts/session-setup.sh`, `skills/shared/subskill-invocation.md`, and every producer/consumer skill when adding session-env keys.
