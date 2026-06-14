# design-step5b-prepare.sh

## Purpose

Wrapper for the `/design` Step 5b prepare Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`
- `skills/design/scripts/design-step5.sh` for deprecated compatibility delegation

## Invariants

- Hosts the Step 5 prelude before OOS prepare work.
- Writes `$DESIGN_TMPDIR/.completed/step-4b` before the pause check.
- Marks `design Step 5 — finalize` timing after the pause check.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
