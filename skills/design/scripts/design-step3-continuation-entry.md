# design-step3-continuation-entry.sh

## Purpose

Wrapper for the legacy heuristic Step 3 continuation entry path.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Validates `DESIGN_TMPDIR` after sourcing env.
- Clears `$DESIGN_TMPDIR/.step3-entry-plan-printed` before pause-save so legacy heuristic continuation owns preview cleanup.
- Delegates state hygiene to `python/cli.py plan-review step3-state --auto-continuation-entry` after pause-save.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `make test-design-structure` and relevant `/design` script checks.
