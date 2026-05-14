# design-driver.sh

## Purpose

`design-driver.sh` is the `/design` mechanical ACTION dispatcher. `SKILL.md` emits `ACTION=<step> ARGS=...` records for scriptable steps, and this driver invokes the corresponding helper scripts.

## Primary Callers

- `/design` Step 0 tail for `ACTION=CLASSIFY`
- `/design` Step 2b for `ACTION=EMIT_PLAN`
- `/design` Step 3 for `ACTION=TALLY` and the second `ACTION=EMIT_PLAN`
- `/design` Step 4 for `ACTION=FINALIZE`
- `skills/design/references/heavy-worker.md` when the heavy worker follows the same scriptable mechanics

## Invariants

- Completion sentinels are written under `$DESIGN_TMPDIR/.completed/<step>` after successful known actions.
- Known actions emit `STEP_STARTED=<name>` and `STEP_COMPLETED=<name>` or `STEP_FAILED=<name> REASON=<token>`.
- Completed steps are skipped on replay.
- `--resume-from STEP` skips earlier actions and resumes at the named step.
- Unknown or non-`ACTION=` lines are passed through as `ACTION_PASSTHROUGH=...`.
- The driver does not perform model-judgment work; sketch synthesis, plan authoring, discussion rounds, and AskUserQuestion gates stay in `SKILL.md` or the heavy worker.

## Makefile Wiring

The regression harness is `make test-design-driver`, wired into `test-harnesses-1`.

## Harness

`test-design-driver.sh` covers happy-path dispatch, completion-sentinel replay, `--resume-from`, partial failure, and unknown-action passthrough.

## Edit In Sync

Update this contract, `test-design-driver.sh`, and `skills/design/SKILL.md` together when adding or renaming ACTION records.
