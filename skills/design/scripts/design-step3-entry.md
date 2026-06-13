# design-step3-entry.sh

## Purpose

Combines adjacent `/design` script-call blocks so `skills/design/SKILL.md` keeps a single Bash call across this prompt-side boundary.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Forwards `--session-env-path` and `--claude-pid` to the internal wrappers.
- Accepts `--reentry` for Gate A / Gate C routed review re-entry and writes `$DESIGN_TMPDIR/.step3-reentry` after validating `DESIGN_TMPDIR`.
- `--reentry` does not clear `$DESIGN_TMPDIR/.step3-entry-plan-printed`; legacy continuation preview cleanup belongs to `design-step3-continuation-entry.sh`.
- Keeps the combined entry order: clear `.pause-save-complete`, call `design-step3-entry-state.sh`, exit on `.pause-save-complete`, then call preview.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and `skills/design/scripts/test-design-pause-resume.sh`.
