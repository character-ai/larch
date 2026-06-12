# design-step5b-annotate.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Does not derive the root Claude PID from `$PPID` internally.
- Exits non-zero and emits `STEP5B_STATUS=annotate-failed` when `file-design-oos.sh annotate` exits non-zero. The `.completed/step-5b` sentinel is NOT written on failure, preventing downstream steps from treating a failed annotate as a completed Step 5b.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
