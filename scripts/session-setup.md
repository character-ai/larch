# scripts/session-setup.sh — contract

Shared setup wrapper for larch skills. It creates a fresh session tmpdir, optionally runs preflight and repo discovery, reviewer health probes, and can write a session-env file plus a `.health` sidecar.

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

## Reviewer probe contract

- `--check-reviewers` probes Codex and Cursor. Gemini probe removed in #1720 (Part 1) — it ran with workspace-write access and modified the working tree.
- A non-empty caller-env `CODEX_HEALTHY` or `CURSOR_HEALTHY` (either `true` or `false`) auto-skips the corresponding probe; an empty or absent value runs the probe. `GEMINI_HEALTHY` is always hard-coded to `false` regardless of caller-env.
- `GEMINI_HEALTHY=false` / `GEMINI_AVAILABLE=false` are always emitted unconditionally (both the `--check-reviewers` probe path and the caller-env passthrough path).
- On `WAIT_INFRA_ERROR=`, the stderr banner says: `Probe could not classify tool health; available tools marked unhealthy for fail-closed gating.` This matches `check-reviewers.sh` emitting `*_HEALTHY=false` for every available tool on the wait/preflight/infra-error path while preserving `WAIT_INFRA_ERROR` as the cause diagnostic.

## Session-env contract

Recognized caller-env keys are `REPO`, `REPO_UNAVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`, `GEMINI_HEALTHY`, `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER`. The file is parsed line-by-line and never sourced.

`LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` are pass-through telemetry context for nested skills. `/implement` establishes them from its own session tmpdir, `/review` inherits them when invoked with `--session-env`, and standalone `/review` leaves them absent so token-ledger fallback behavior remains unchanged. `LARCH_TIMING_LEDGER` is validated against the timing-ledger containment roots before `session-setup.sh` forwards it to `write-session-env.sh`.

When `--write-health` is provided, the health sidecar always contains Codex, Cursor, and `GEMINI_HEALTHY=false`. The defaults at the write site are fail-closed: an empty `FINAL_*_HEALTHY` emits `=false` rather than re-masking unhealthy state as `true`. Regression coverage lives in `scripts/test-session-setup-health-defaults.sh` (sibling contract: `scripts/test-session-setup-health-defaults.md`), wired through `make test-session-setup-health-defaults` and `test-harnesses-6`.

## Edit-in-sync

Update `scripts/check-reviewers.sh`, `scripts/write-session-env.sh`, `skills/shared/subskill-invocation.md`, and `skills/shared/external-reviewers.md` when changing session-env keys or reviewer health semantics. Update `scripts/write-session-id.sh` when changing session-id ownership or idempotency.
