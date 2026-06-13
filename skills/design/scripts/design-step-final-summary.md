# design-step-final-summary.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Writes `$DESIGN_TMPDIR/.bg-wait-active` around final summary rendering and removes it on exit so hook enforcement covers the immediate-background wait.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Called from an immediate-background Bash fence; callers wait for `<task-notification>` before reading `final-summary.md`.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
