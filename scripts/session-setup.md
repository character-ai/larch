# scripts/session-setup.sh — contract

Shared setup wrapper for larch skills. It creates a fresh session tmpdir, optionally runs preflight and repo discovery, checks reviewer binary presence, and can write a session-env file.

Session tmpdirs are named `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/<prefix>-<clone-tag>-XXXXXX`, where
`<clone-tag>` is the current working directory basename with every character
outside `[A-Za-z0-9_-]` replaced by `_`, truncated to 32 characters, and
defaulted to `_` when empty. If the cache sessions root cannot be created or
written, the script falls back to the legacy `/tmp/<prefix>-<clone-tag>-XXXXXX`
template with a stderr warning. This keeps concurrent clone runs
distinguishable while preserving `mktemp`'s random suffix.

Immediately after `mktemp -d`, the script writes `session-id` and emits
`SESSION_ID=<value>` on stdout. It prefers `uuidgen` and falls back to
`hostname-pid-epoch` when `uuidgen` is unavailable. It also writes
`.larch-keepalive` with `PID=`, `PPID=`, `CLONE_PATH=`, `SESSION_ID=`,
`PREFIX=`, `CREATED=`, and `NOTE=ext-cleaners-please-skip`. The sentinel is
advisory; write failures warn on stderr and do not abort setup.

The script also emits `LARCH_RENDER_CACHE_DIR=$SESSION_TMPDIR/render-cache`.
Callers that evaluate the session-env output inherit a session-scoped cache for
`scripts/render-specialist-prompt.sh`; the renderer creates the directory
lazily and falls back to uncached rendering if the directory cannot be created.

## Reviewer Presence Contract

When `--check-reviewers` is passed, setup invokes `scripts/check-reviewers.sh` and emits `CODEX_PRESENT`, `CURSOR_PRESENT`, and backward-compatible `CODEX_AVAILABLE` / `CURSOR_AVAILABLE` aliases. Presence is static binary detection for the session; runtime launch failures are handled by per-slot waterfall fallback.

## Session-env contract

`LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` are pass-through telemetry context for nested skills. `/implement` establishes them from its own session tmpdir, `/review` inherits them when invoked with `--session-env`, and standalone `/review` leaves them absent so token-ledger fallback behavior remains unchanged. `LARCH_TIMING_LEDGER` is validated against the timing-ledger containment roots before `session-setup.sh` forwards it to `write-session-env.sh`.

`LARCH_CLAUDE_PLUGIN_ROOT` is persisted by `write-session-env.sh` from the
writer's `CLAUDE_PLUGIN_ROOT` environment. It is consumed directly by
orchestrator Bash-block rehydration guards, not as a `session-setup.sh`
caller-env passthrough.

`PREV_IMPLEMENT_TMPDIR` is a cross-session handoff pointer. When it is present
and `<prev>/larch-logs` exists, setup best-effort copies that subtree into the
fresh `$SESSION_TMPDIR/larch-logs` before later skill steps write additional
run-log batches. Missing paths and copy failures are ignored.

## Edit-in-sync

Update `scripts/check-reviewers.sh`, `scripts/write-session-env.sh`, `skills/shared/subskill-invocation.md`, and `skills/shared/external-reviewers.md` when changing session-env keys or reviewer presence semantics. Update `scripts/write-session-id.sh` when changing session-id ownership or idempotency.
