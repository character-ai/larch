# design-step5c.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` after publish preconditions and pause-save checks, then removes it on exit so hook enforcement covers publish/result parsing.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
