# test-design-structure.sh

Structural guard for the `/design` two-tier contract.

The harness asserts that `/design` exposes only SIMPLE/HARD tier routing, uses the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, runs plan validation unconditionally through `invoke-plan-validator.sh`, includes per-tier Step 3 review-round caps, and no longer references quick-review or v1 budget helpers.

It also verifies `plan-review-loop.sh` remains stateless with respect to `review-round-count.txt`; Step 3 in `SKILL.md` owns the counter and passes the computed `--round-num`.

Check 17 also pins the per-turn background-polling NEVER literal in `skills/shared/orchestrator-never.md`.

## Step 3.6 region fence

`assert_thin_fence FILE LABEL [START_MARKER END_MARKER]` may now operate on an explicit region. With markers, the harness extracts the inclusive start/exclusive end range and fails if either marker is absent; without markers, it preserves whole-file checks.

The `skills/design/SKILL.md` check is scoped to `<!-- step:3.6` through `<!-- step:3b`. Region-only pins forbid fat-fence symlink/result-env shapes, including `phase_driver_read_result_env`, symlink-source warnings, and file-first `.step3.6-assessor.env` while/read loops. The same region pins the first entry `.pause-requested` pause-save guard before classification to include `${REPO:+--repo "$REPO"}`.

The harness also pins every Gate-B-bypass branch (`cap-reached`, `tally-error`, `panel-failed`, `skipped-cap-reached`, `degraded-empty-collector`, `plan-validator-defects`, and `plan-size-trigger`) to contain a literal sentinel-write line with the `.completed` mkdir plus all three `step-3`, `step-3.5`, and `step-3.6` sentinel writes. Its self-tests prove the assertion fails when non-`plan-size-trigger` branches drop a sentinel.

The Step 3b region check slices `<!-- step:3b` through `<!-- step:4` and pins the first entry `.pause-requested` pause-save guard to include `${REPO:+--repo "$REPO"}` so the Step 3.6 occurrence cannot satisfy the check by accident.

## Recent contract coverage

- Covers the Step 5c publish gate, clarify fail-closed publish/recovery metadata, clarify sub-step 6 summary outcome branch, pause-check `--repo` forwarding, init `--repo` persistence pins, and the Step 0 degraded-tools gate fence that sources durable design env and passes all four explicit false-defaulted operands.

## Step 3b FINALIZE and SIMPLE sentinel routing

The harness now pins FINALIZE to the Step 3b completion-boundary region for fresh runs. Step 4 may contain only the gated compatibility FINALIZE in its entry fence for old paused sessions where `.completed/finalize` is absent, and both FINALIZE failure branches must exit with the captured non-zero status after printing the repair warning.

SIMPLE sentinel writes are pinned to the Step 2a entry fence behind the `design_classification == SIMPLE` guard. The assertions check branch-scoped sentinel writes, fail-fast `set -e`, and completion markers written only after all three SIMPLE artifacts succeed; the `### SIMPLE branch` subsection must not contain its own sentinel Bash block.

The Step 3b, Step 3/Gate-B-bypass/Gate B, `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `skills/design/references/plan-review.md`, `run-step3-review.sh`, and `run-step3-review.md` routing checks are line-scoped. They reject direct Step 3b-to-Step 4 routes, including comma and spaced-slash shorthand variants, unless the same line names the Step 3b completion boundary.
