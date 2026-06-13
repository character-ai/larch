# design-step3b-sanitize.sh

## Purpose

Wrapper for `/design` Step 3b architecture-diagram sanitizer handling. It validates the candidate, promotes accepted diagrams, handles sanitizer rejection cleanup, appends warning logs, and completes Step 3b.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Emits promoted diagrams between `---LARCH-DIAGRAM-BEGIN---` and `---LARCH-DIAGRAM-END---` markers.
- Deletes rejected or unreadable candidates instead of promoting them.
- Runs FINALIZE and writes `.completed/step-3b` only after handled success or rejection.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
