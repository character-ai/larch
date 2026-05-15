# emit-plan.sh

## Purpose

`emit-plan.sh` is the mechanical validator for `/design` plan emission. It checks `$DESIGN_TMPDIR/plan.txt`, requires a final non-empty line of the form `diff_lines: <N>`, and writes the integer to `$DESIGN_TMPDIR/diff-lines.txt`.

## Primary Callers

- `skills/design/scripts/design-driver.sh` for `ACTION=EMIT_PLAN`
- `/design` Step 2b after initial plan authoring
- `/design` Step 3 after accepted plan-review findings revise the plan
- `skills/design/references/heavy-worker.md` when the heavy worker runs the same mechanics in a subagent

## Invariants

- `plan.txt` must be non-empty.
- The final non-empty line must be exactly `diff_lines: <N>` where `<N>` is a non-negative integer.
- Missing or malformed diff lines fail closed with `EMIT_PLAN_STATUS=missing-diff-lines` and exit 1.
- Re-running the script is idempotent; it overwrites `diff-lines.txt` atomically.

## Makefile Wiring

The regression harness is `make test-emit-plan`, wired into `test-harnesses-1`.

## Harness

`test-emit-plan.sh` covers valid plans, missing final `diff_lines`, non-integer values, empty plans, and idempotent re-invocation after revision.

## Edit In Sync

Update this contract, `test-emit-plan.sh`, `skills/design/SKILL.md`, and `skills/design/references/heavy-worker.md` together when the plan diff-line grammar changes.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
