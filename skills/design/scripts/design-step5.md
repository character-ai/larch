# design-step5.sh

## Purpose

Deprecated compatibility wrapper for older paused `/design` sessions.

## Primary callers

- Legacy sessions that still enter Step 5 through `design-step5.sh`

## Invariants

- Live `/design` Step 5 enters through `design-step5b-prepare.sh`.
- Sources the optional session env and validates `CLAUDE_PLUGIN_ROOT` before delegation.
- Reconstructs explicit `--session-env-path` and `--claude-pid` flags for `design-step5b-prepare.sh` instead of forwarding consumed argv.
- Accepts `--session-env-path` from legacy prompt-side Bash calls.
- Accepts `--claude-pid` when the delegated logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
