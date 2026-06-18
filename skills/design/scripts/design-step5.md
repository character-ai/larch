# design-step5.sh

## Purpose

Deprecated compatibility wrapper for older paused `/design` sessions.

## Primary callers

- Legacy sessions that still enter Step 5 through `design-step5.sh`

## Invariants

- Live `/design` Step 5 delegates directly to `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design step5b-prepare`.
- Reconstructs explicit `--session-env-path` and `--claude-pid` flags before delegation instead of forwarding consumed argv.
- `design-step5b-prepare.sh` remains a thin launcher-compat wrapper for `skills/design/SKILL.md` fences.
- Step 5b behavior lives in `python/cli.py design step5b-prepare`.
- Sources the optional session env and validates `CLAUDE_PLUGIN_ROOT` before delegation.
- Accepts `--session-env-path` from legacy prompt-side Bash calls.
- Accepts `--claude-pid` when the delegated logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
