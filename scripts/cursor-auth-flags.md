# cursor-auth-flags.sh

Stdout flag emitter consumed by runtime skill markdown templates. Sources `scripts/lib-cursor-auth.sh`, populates `CURSOR_AUTH_ARGS`, and prints the conditional `--api-key` argv elements one per line on stdout. Empty array (CURSOR_API_KEY unset/empty) → zero lines. Non-empty → exactly two lines (`--api-key`, then the trimmed key value).

## Callers

Runtime skill markdown templates that emit Bash blocks executed verbatim by the orchestrator:

- `skills/shared/voting-protocol.md` — Cursor voter launch.
- `skills/shared/dialectic-protocol.md` — Cursor judge launch.
- `skills/research/references/validation-phase.md` — Cursor research-validation launch.

These markdown blocks read this script's stdout into a local array via:

```bash
CURSOR_AUTH_FLAGS=()
while IFS= read -r line; do CURSOR_AUTH_FLAGS+=("$line"); done < <("${CLAUDE_PLUGIN_ROOT}/scripts/cursor-auth-flags.sh")
```

…then expand `"${CURSOR_AUTH_FLAGS[@]}"` inline in the cursor agent argv between `$AGENT_MODEL_ARGS` and `--workspace`.

## Invariants

- Never echoes the key on any path (including source-failure error paths).
- Hard fails (exit 1) if `scripts/lib-cursor-auth.sh` cannot be sourced — the runtime markdown blocks rely on this argv being correct, and degrading silently would reintroduce the keychain bug at exactly the call sites this script was added to fix.
- Bash 3.2-safe (no `mapfile`/`readarray`/`declare -n`/`local -n`).

## Test harness

Coverage rolls up into `scripts/test-lib-cursor-auth.sh` (which pins the underlying `cursor_auth_argv` behavior) and `scripts/test-launch-cursor-review.sh` (which pins the launcher-level argv shape). Direct stub-driven coverage of `cursor-auth-flags.sh`'s line-per-element output is exercised by `scripts/test-lib-cursor-auth.sh` `test_cursor_auth_flags_*` cases.

## Edit-in-sync rules

When editing this script:
- Update the runtime markdown blocks above if the line-per-element protocol changes.
- Re-run `bash scripts/test-lib-cursor-auth.sh`.
