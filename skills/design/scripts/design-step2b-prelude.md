# design-step2b-prelude.sh

## Purpose

Legacy wrapper retained for compatibility with older Step 2b entry contracts.

## Primary callers

- Compatibility callers only. Initial Step 2b no longer calls this wrapper directly.

## Invariants

- Active Step 2b entry behavior lives in `design-step2b-drafter.sh`.
- `design-step2b-drafter.sh` must preserve the same exact sentinel helper semantics.
- `design-step2b-drafter.sh` must not source this script because this script has top-level execution and may exit when sourced.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
