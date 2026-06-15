# design-step2b-postplan.sh

## Purpose

Wrapper for the `/design` Step 2b postplan Bash block.

## Primary callers

- `skills/design/SKILL.md`
- `skills/design/scripts/design-step2b-drafter.sh` on the drafter-success path

## Invariants

- This wrapper remains the single authority for Step 2b postplan rc handling.
- rc 11 pause-save remains owned here.
- Every rc 11 pause-save path emits `POSTPLAN_RC=11` and `POSTPLAN_STATUS=pause-save` before delegating to pause-save.
- Inline retry sentinels remain owned here.
- Prompt-side routing consumes wrapper-owned `POSTPLAN_RC=` and `POSTPLAN_STATUS=` rows, not arbitrary plan-preview text.
- Prompt-side `_postplan_out` for internal postplan routing is the delegated postplan stdout segment after `DRAFTER_STATUS=succeeded`, not the full merged drafter output.
- Absence of postplan rows after drafter success is incomplete output and must not route to Step 3.
- Accepts `--session-env-path` from the prompt-side Bash call.
- Accepts `--claude-pid` when the wrapped logic must refresh session state.
- Completion-only modes validate `DESIGN_TMPDIR`, write their markers, honor pause-save, and exit without running `design-postplan-emit.sh`.
- `--write-step2b-completion-only` writes `.completed/step-2b` only.
- `--write-completion-only` writes `.completed/step-2b.5`; `--include-step2b` additionally writes `.completed/step-2b`. This mode does not run `design-postplan-emit.sh`, so its `step-2b.5` write is non-authoritative for the drafter missing-row fail-safe; that branch requires `POSTPLAN_EMIT_STATUS=ok` in `.design-postplan-emit-result.env`.
- The normal postplan emit path still honors the existing pause gate before `design-postplan-emit.sh`.
- Clean rc 0 writes `.completed/step-2b.5` for every site and `.completed/step-2b` only for the initial Step 2b site.
- Does not derive the root Claude PID from `$PPID` internally.

## Harness

Covered by `scripts/test-design-structure.sh`, `skills/design/scripts/test-design-step2b-drafter.sh`, and relevant `/design` script checks.
