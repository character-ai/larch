# design-step0-init.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Writes `feature-description.txt` for both normal `ROUTE=proceed` and the already-planned replacement flow (`ROUTE=already-planned`) before `design-init-runparams.sh` runs.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
