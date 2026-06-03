# cursor-auth-flags.sh

Cursor auth **preflight gate** for runtime skill markdown templates. Sources `scripts/lib-cursor-auth.sh` and runs `cursor_auth_preflight`, exiting 0 (proceed) or 2 (Darwin preflight failure — neither `CURSOR_API_KEY` nor a cursor keychain entry available). It prints **nothing** on stdout.

Historically this script emitted `--api-key <CURSOR_API_KEY>` argv elements for the markdown blocks to splice into the `cursor agent` command line. That leaked the key into `scripts/run-external-agent.sh`'s `.meta` `CMD_JSON`, `ps`, and any captured command line (issue #3375). Cursor now authenticates via the `CURSOR_API_KEY` **environment variable** (see `scripts/lib-cursor-auth.sh`), which the orchestrator already exports and the `cursor agent` child inherits — so no `--api-key` argv element is needed and this script no longer prints one. It is retained purely as the Darwin preflight gate.

## Callers

Runtime skill markdown templates that emit Bash blocks executed verbatim by the orchestrator:

- `skills/shared/voting-protocol.md` — Cursor voter launch.
- `skills/shared/dialectic-protocol.md` — Cursor judge launch.
- `skills/research/references/validation-phase.md` — Cursor research-validation launch.

These markdown blocks invoke the gate (advisory exit) and pass **no** `--api-key`:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/cursor-auth-flags.sh" || true
```

The `cursor agent` child in the same block inherits `CURSOR_API_KEY` from the orchestrator's environment; no auth argv element is added.

## Invariants

- Never echoes the key on any path (including source-failure error paths).
- Prints nothing on stdout on any path; exit 0 = proceed, exit 2 = Darwin preflight failure, exit 1 = `scripts/lib-cursor-auth.sh` could not be sourced (hard fail — degrading silently would reintroduce the keychain bug at exactly the call sites this gate protects).
- Bash 3.2-safe (no `mapfile`/`readarray`/`declare -n`/`local -n`).

## Test harness

Coverage rolls up into `scripts/test-lib-cursor-auth.sh` (which pins `cursor_auth_preflight` and the gate's no-stdout / exit-code behavior) and `scripts/test-launch-review.sh` (which pins the launcher-level env-auth argv shape).

## Edit-in-sync rules

When editing this script:
- Update the runtime markdown blocks above if the invocation contract changes.
- Re-run `bash scripts/test-lib-cursor-auth.sh`.
