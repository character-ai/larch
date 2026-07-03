# scripts/deny-edit-write.sh — contract

`scripts/deny-edit-write.sh` is a token-gated PreToolUse hook used by `/research` and `/bug`. Consumers invoke it with a recognized first argument: `research` from `skills/research/SKILL.md` and `bug` from `skills/bug/SKILL.md`.

## Activation gate

Before reading stdin or checking `jq`, the hook checks `${XDG_CACHE_HOME:-${HOME:-}/.cache}/larch/deny-edit-write-active` for a fresh sentinel named `<token>-*`. Recognized token prefixes are `research` and `bug`. The TTL is 360 minutes. The filename embeds the writer's `$PPID` for debugging and per-run overwrite only.

A missing activation directory, unreadable directory, stale sentinel, missing token, or unrecognized token is inactive. Inactive hooks exit 0 with empty stdout. There is no any-sentinel fallback, so a stale tokenless registration cannot be re-armed by another skill's fresh sentinel. The hook performs no `$PPID` correlation because production PreToolUse parent PIDs can diverge from orchestrator Bash parent PIDs.

## Active `/tmp` enforcement

When activation is live, the hook permits the call only when the tool's target path resolves to an absolute path under canonical `/tmp`. Every other active outcome denies: missing path, relative path, traversal outside `/tmp`, symlink cycle, canonicalization failure, or `jq` runtime failure.

The script reads stdin JSON and extracts the target via `jq -r '[.tool_input.file_path, .tool_input.notebook_path] | map(select(type == "string" and length > 0)) | .[0] // empty'`. `map(select(length > 0))` is required because `jq`'s `//` treats the empty string as present, so a naïve `// empty` would let an empty `file_path` shadow a valid `notebook_path`. NotebookEdit uses `notebook_path`; the length-aware fallback prevents fail-open on that shape.

Path resolution mirrors `scripts/block-submodule-edit.sh`: bounded symlink walk (max depth 40; cycle means deny), nearest-existing-ancestor probe via `dirname`, then canonicalization via `cd … && pwd -P` to handle macOS `/tmp` to `/private/tmp` aliasing. The allowed root is pre-computed once as `$(cd /tmp && pwd -P)`. The decision is exact equality or `$ALLOWED_ROOT/` prefix.

On allow the script emits empty stdout and exits 0. On deny it emits a fixed-literal `hookSpecificOutput` JSON envelope through local `hook_emit` and exits 0. The deny envelope is composed only from fixed ASCII literals (single fixed reason string, no runtime interpolation into the deny JSON) and is byte-identical across the active `jq`-absent static path, the `block()` helper's `jq -cn` path, and `block()`'s inner static fallback. The hook writes deny JSON through a local FD-3 `hook_emit` path.

The hook is the sole mechanical enforcer of the active `/tmp`-only policy for the matched Claude tool surface. `allowed-tools` declares each orchestrator's surface but does not confine writes to `/tmp`; see `SECURITY.md` for the residual-risk framing. `/research` must keep matcher `Edit|Write|NotebookEdit`. `/bug` must keep matcher `Write`. Adding `Skill` would deny `/issue` delegations and break child-invocation flows.

Stale or leaked registrations no longer deny by themselves. A fresh activation sentinel is required for each consumer token.

`scripts/test-deny-edit-write.sh` is the table-driven regression harness. It isolates the larch cache home and covers inactive, active, stale, cross-token, tokenless-inactive, foreign-PID, unset-`HOME`, NotebookEdit, path-canonicalization, idempotency, and `jq`-absent-active behavior. It is wired into `make lint` via the `test-deny-edit-write` target. The harness fails when its own `jq` is missing because the assertions need a JSON parser. Edits to the hook must stay in sync with the harness. The test script is added to `agent-lint.toml`'s exclude list because agent-lint's dead-script rule does not follow Makefile-only references.
