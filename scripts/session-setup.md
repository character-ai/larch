# scripts/session-setup.sh — contract

Shared setup wrapper for larch skills. It creates a fresh session tmpdir, optionally runs preflight, Slack and repo discovery, reviewer health probes, and can write a session-env file plus a `.health` sidecar.

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

## Reviewer probe contract

- `--check-reviewers` probes the legacy Codex+Cursor set.
- `--check-gemini-reviewer` is opt-in and only meaningful with `--check-reviewers` for the probe workflow; it passes `--include-gemini` to `check-reviewers.sh`. The flag also gates `GEMINI_HEALTHY` emission in the `--write-health` sidecar on the passthrough path: when set with empty `FINAL_GEMINI_HEALTHY`, the sidecar emits `GEMINI_HEALTHY=false` (fail-closed) rather than omitting the key. See `scripts/test-session-setup-health-defaults.sh` scenario 2 for the regression fixture.
- Caller-env `CODEX_HEALTHY=false`, `CURSOR_HEALTHY=false`, or `GEMINI_HEALTHY=false` auto-skips the corresponding probe.
- Gemini health failures use skip-style wording: Gemini is omitted for the session rather than replaced by Claude.
- When Gemini probing is enabled, `session-setup.sh` passes `--artifact-dir "$SESSION_TMPDIR"` to `check-reviewers.sh` so `gemini-tool-drift.txt` persists for the session lifetime instead of disappearing with the probe tmpdir.
- `GEMINI_TOOL_DRIFT_WARNING=` keys are re-emitted on stdout and summarized as a stderr banner. `GEMINI_TOOL_DRIFT_ARTIFACT=` is passed through when present.
- On `WAIT_INFRA_ERROR=`, the stderr banner says: `Probe could not classify tool health; available tools marked unhealthy for fail-closed gating.` This matches `check-reviewers.sh` emitting `*_HEALTHY=false` for every available tool on the wait/preflight/infra-error path while preserving `WAIT_INFRA_ERROR` as the cause diagnostic.

## Session-env contract

Recognized caller-env keys are `SLACK_OK`, `SLACK_MISSING`, `REPO`, `REPO_UNAVAILABLE`, `CODEX_HEALTHY`, `CURSOR_HEALTHY`, `GEMINI_HEALTHY`, `LARCH_TOKEN_SESSION_ID`, and `LARCH_CLAUDE_SOURCE_FILE`. The file is parsed line-by-line and never sourced.

`LARCH_TOKEN_SESSION_ID` and `LARCH_CLAUDE_SOURCE_FILE` are pass-through telemetry context for nested skills. `/implement` establishes them from its own session tmpdir, `/review` inherits them when invoked with `--session-env`, and standalone `/review` leaves them absent so token-ledger fallback behavior remains unchanged.

When `--write-health` is provided, the health sidecar contains Codex and Cursor health, plus Gemini health when Gemini probing is requested or inherited from caller-env. The defaults at the write site are fail-closed: an empty `FINAL_*_HEALTHY` (e.g., `check-reviewers.sh` did not emit the key, or the passthrough caller-env omitted it) emits `=false` rather than re-masking unhealthy state as `true`. Regression coverage lives in `scripts/test-session-setup-health-defaults.sh` (sibling contract: `scripts/test-session-setup-health-defaults.md`), wired through `make test-session-setup-health-defaults` and `test-harnesses-6`.

## Edit-in-sync

Update `scripts/check-reviewers.sh`, `scripts/write-session-env.sh`, `skills/shared/subskill-invocation.md`, and `skills/shared/external-reviewers.md` when changing session-env keys or reviewer health semantics. Update `scripts/write-session-id.sh` when changing session-id ownership or idempotency. Update `scripts/lib-gemini-tool-drift.sh` and `scripts/check-reviewers.md` when changing Gemini drift warning or artifact keys.
