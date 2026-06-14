# design-step2b-postplan.sh

## Purpose

Wrapper for a `/design` Bash block that keeps `skills/design/SKILL.md` free of inline Bash.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Completion-only modes validate `DESIGN_TMPDIR`, write their markers, honor pause-save, and exit without running `design-postplan-emit.sh`.
- `--write-step2b-completion-only` writes `.completed/step-2b` only.
- `--write-completion-only` writes `.completed/step-2b.5`; `--include-step2b` additionally writes `.completed/step-2b`.
- The normal postplan emit path still honors the existing pause gate before `design-postplan-emit.sh`.
- Clean rc 0 writes `.completed/step-2b.5` for every site and `.completed/step-2b` only for the initial Step 2b site.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh` and relevant `/design` script checks.
