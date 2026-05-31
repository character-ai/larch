# scripts/write-session-env.sh — contract

Writes a `KEY=value` session-env file atomically for child skills. The file is not escaped and is not safe to source; consumers must parse it through `session-setup.sh --caller-env` or `read-session-env-key.sh`.

## Keys

Always writes `REPO`, `REPO_UNAVAILABLE`, and `FORKED_TARGET` (default `false`; set from `--forked-target true|false`). Optionally writes reviewer presence booleans and their compatibility aliases:

- `CODEX_PRESENT`
- `CURSOR_PRESENT`
- `CODEX_AVAILABLE`
- `CURSOR_AVAILABLE`

It may also write `LARCH_TIMING_LEDGER` when the caller passes `--timing-ledger <path>`. `/implement` uses this durable key so nested `/design` and `/review` invocations continue appending to the parent timing ledger after session-env rewrites.

It may also write `LARCH_TOKEN_SESSION_ID` when the caller passes `--token-session-id <id>` and `LARCH_CLAUDE_SOURCE_FILE` when the caller passes `--claude-source-file <path>`. `/implement` writes both keys so every orchestrator-side token-ledger / token-report Bash block can rehydrate the parent run's token context, and `/review` can forward that context to nested review launchers. `/fix-issue` does not pass these keys; `/implement` always establishes its own token session id and Claude source snapshot.

It may also write `PREV_IMPLEMENT_TMPDIR` when the caller passes
`--prev-implement-tmpdir <path>`. `/implement` uses this to let the next
session setup copy the previous session's `larch-logs` subtree into the fresh
tmpdir before additional batches are written.

It may also write `LARCH_CLAUDE_PLUGIN_ROOT` when `CLAUDE_PLUGIN_ROOT` is set in
the writer's environment. `/implement` uses this durable key so later Bash
blocks can recover `${CLAUDE_PLUGIN_ROOT}` from `$IMPLEMENT_TMPDIR/session-env.sh`
without sourcing the file.

When `CLAUDE_PLUGIN_ROOT` is set and `--output` is not `/dev/null`, the writer
also emits a sourceable sibling `plugin-root.env` in `dirname(--output)`:

```bash
CLAUDE_PLUGIN_ROOT=<value>
export CLAUDE_PLUGIN_ROOT
```

Written atomically via temp+mv. Skipped when `CLAUDE_PLUGIN_ROOT` is empty or
`--output` is `/dev/null`. Unlike `session-env.sh`, `plugin-root.env` is safe
to source (only the one export). This output is additive for every
`write-session-env.sh` caller; only `/implement`'s `SKILL.md` consumes it today.

`emit_plugin_root_env <path> <value>` is defined before the `BASH_SOURCE` argv0
guard so `implement-bootstrap.sh` can source this script for resume-tail sync
without enabling errexit or running argv parsing in the parent (`set -uo pipefail`
in bootstrap). Skip or invalid values use `return 0` inside the helper; `exit` is
argv0-only.

It may also write `LARCH_DYNAMIC_ARCHETYPES_MAX` when the caller passes
`--dynamic-archetypes <N>` (integer 0–8). `/implement` uses this to propagate
`--dynamic-archetypes`/`--no-dynamic-archetypes` operator flags to
`review-and-fix.sh`'s `DYNAMIC_ARCHETYPES` resolution logic, which reads
`LARCH_DYNAMIC_ARCHETYPES_MAX` from session-env via `session_get`.

Values must stay narrow and caller-controlled (`true|false` for presence booleans and `--forked-target`; validated repo strings for repo identity; caller-owned tmp paths for timing ledgers). `--token-session-id` must match `^[A-Za-z0-9_.-]{1,128}$`; `--claude-source-file` and `--timing-ledger` must match `^[A-Za-z0-9_./~+-]{1,512}$`; `--prev-implement-tmpdir` and `CLAUDE_PLUGIN_ROOT` must be absolute paths of 512 characters or fewer using the same path character set; `--dynamic-archetypes` must be an integer from 0 to 8. Empty optional values are omitted from the file.

## Invariants

- Atomic temp+mv for regular paths.
- `/dev/null` is a no-op sink.
- Do not add arbitrary user text fields without adding escaping and read-side regression coverage.
- The output remains raw `KEY=value`, not shell-quoted shell syntax.

## Edit-in-sync

Update `scripts/session-setup.sh`, `skills/shared/subskill-invocation.md`, and every producer/consumer skill when adding session-env keys.
