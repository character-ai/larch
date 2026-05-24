# design-driver.sh

## Purpose

`design-driver.sh` is the `/design` mechanical ACTION dispatcher. `SKILL.md` emits `ACTION=<step> ARGS=...` records for scriptable steps, and this driver invokes the corresponding helper scripts.

## Primary Callers

- `/design` Step 2b for `ACTION=EMIT_PLAN` and `ACTION=VALIDATE_PLAN_COMMANDS` (after `EMIT_PLAN` when `review_budget` is `full`, via `invoke-plan-validator-if-not-quick.sh`)
- `/design` Step 5c for `ACTION=VALIDATE_PLAN_COMMANDS` on `composed-plan.md` before `redact-secrets.sh` (Tier 3 dry-run disabled on composed artifacts; same helper as Step 2b)
- `/design` Step 3 for the second `ACTION=EMIT_PLAN` (plan-review tallying runs in `plan-review-loop.sh`, not via `ACTION=TALLY`)
- `/design` Step 4 for `ACTION=FINALIZE`

## Invariants

- Completion sentinels are written under `$DESIGN_TMPDIR/.completed/<step>` after successful known actions.
- Known actions emit `STEP_STARTED=<name>` and `STEP_COMPLETED=<name>` or `STEP_FAILED=<name> REASON=<token>`.
- Most completed steps are skipped on replay via sentinel. Exception: `EMIT_PLAN` and `VALIDATE_PLAN_COMMANDS` are re-runnable and never skipped by the sentinel — `/design` may re-run them after plan revisions or composed-plan updates, so they must always refresh their outputs (`diff-lines.txt` and `validate-plan-commands.log` respectively).
- `--resume-from STEP` skips earlier actions and resumes at the named step. For `EMIT_PLAN` and `VALIDATE_PLAN_COMMANDS` (no sentinel), the before-resume skip still applies to maintain the resume contract for other steps while these two actions remain re-runnable on replay.
- Unknown or non-`ACTION=` lines are passed through as `ACTION_PASSTHROUGH=...`.
- The driver does not perform model-judgment work; sketch synthesis, plan authoring, discussion rounds, and AskUserQuestion gates stay in `SKILL.md`.
- `ACTION=… ARGS=…` lines carry a shell word sequence produced by mechanical `printf '%q'` emitters; the driver parses `ARGS` with `eval "action_args=( $args_text )"` (not naive whitespace `read -a`).

## Makefile Wiring

The regression harness is `make test-design-driver`, wired into `test-harnesses-12`.

## Harness

`test-design-driver.sh` covers happy-path dispatch, EMIT_PLAN re-runnability (re-runs after plan revision), `VALIDATE_PLAN_COMMANDS` re-runnability, FINALIZE sentinel-guard on replay, `--resume-from`, partial failure, and unknown-action passthrough.

## Edit In Sync

Update this contract, `test-design-driver.sh`, and `skills/design/SKILL.md` together when adding or renaming ACTION records.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.
