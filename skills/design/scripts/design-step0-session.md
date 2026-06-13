# design-step0-session.sh

## Purpose

Wrapper for the `/design` Step 0 session Bash block. It runs session setup, writes the durable design env, and emits the degraded-tools gate envelope so `skills/design/SKILL.md` can keep one Step 0a fence.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Runs `agent degraded-tools-gate --skill design` only after `session write-design-env` succeeds, using the reviewer presence keys from session setup.
- Emits `STEP0_STATUS`, `DEGRADED`, `BOTH_DOWN`, and `DEGRADED_PROMPT_REQUIRED=true` only for the interactive both-down decision path.
- Writes `.degraded-tools-gate-prompted` for one-down and non-interactive both-down paths.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
