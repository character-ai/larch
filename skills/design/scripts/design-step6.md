# design-step6.sh

## Purpose

Combines adjacent `/design` script-call blocks so `skills/design/SKILL.md` keeps a single Bash call across this prompt-side boundary.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Forwards `--session-env-path` and `--claude-pid` to the internal wrappers.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh`.
