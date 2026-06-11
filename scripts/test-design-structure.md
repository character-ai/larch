# test-design-structure.sh

Structural guard for the `/design` two-tier contract.

The harness asserts that `/design` exposes only SIMPLE/HARD tier routing, uses the `NO_SKETCHES_CLASSIFIED_SIMPLE` sentinel, runs plan validation unconditionally through `invoke-plan-validator.sh`, includes a unified Step 3 review-round cap (cap 5, both tiers), and no longer references quick-review or v1 budget helpers.

It also verifies `plan-review-loop.sh` remains stateless with respect to `review-round-count.txt`; Step 3 in `SKILL.md` owns the counter and passes the computed `--round-num`.

Check 17 also pins the per-turn background-polling NEVER literal in `skills/shared/orchestrator-never.md`.

## Thin-fence region checks

`assert_thin_fence FILE LABEL [START_MARKER END_MARKER]` may now operate on an explicit region. With markers, the harness extracts the inclusive start/exclusive end range and fails if either marker is absent; without markers, it preserves whole-file checks.

Region-only pins forbid fat-fence symlink/result-env shapes, including `phase_driver_read_result_env` and symlink-source warnings. The same region pins the first entry `.pause-requested` pause-save guard before classification to include `${REPO:+--repo "$REPO"}`.

The Step 3b region check slices `<!-- step:3b` through `<!-- step:4` and pins the first entry `.pause-requested` pause-save guard to include `${REPO:+--repo "$REPO"}`.

## Recent contract coverage

- Covers the Step 5c publish gate, clarify fail-closed publish/recovery metadata, clarify sub-step 6 summary outcome branch, pause-check `--repo` forwarding, init `--repo` persistence pins, and the Step 0 degraded-tools gate fence that sources durable design env and passes all four explicit false-defaulted operands.

## Step 3b FINALIZE and SIMPLE sentinel routing

The harness now pins FINALIZE to the Step 3b completion-boundary region for fresh runs. Step 4 may contain only the gated compatibility FINALIZE in its entry fence for old paused sessions where `.completed/finalize` is absent, and both FINALIZE failure branches must exit with the captured non-zero status after printing the repair warning.

SIMPLE sentinel writes are pinned to the Step 2a entry fence behind the `design_classification == SIMPLE` guard. The assertions check branch-scoped sentinel writes, fail-fast `set -e`, and completion markers written only after all three SIMPLE artifacts succeed; the `### SIMPLE branch` subsection must not contain its own sentinel Bash block.

The Step 3b, Step 3/Gate-B-bypass/Gate B, `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `skills/design/references/plan-review.md`, `run-step3-review.sh`, and `run-step3-review.md` routing checks are line-scoped. They reject direct Step 3b-to-Step 4 routes, including comma and spaced-slash shorthand variants, unless the same line names the Step 3b completion boundary.

## Phase 7 folded-sentinel contract

Phase 7 folds absorbed prior-step `.completed` writes into adjacent real-work Bash fences. Check 21 pins the host-fence layout after `skills/design/SKILL.md` adopts the folded contract.

### Fence extraction helpers

- `extract_bash_fence_after_marker FILE MARKER` — whitespace-tolerant first ` ```bash ` … ` ``` ` block after a start marker.
- `extract_bash_fence_containing FILE NEEDLE [AFTER_MARKER]` — first fence after an optional marker whose body contains `NEEDLE`.
- `assert_fence_write_before_pause FENCE STEP LABEL [after_pause]` — verifies `: > "$DESIGN_TMPDIR/.completed/step-X"` ordering relative to `current-design-env` source and `design-pause-save.sh` pause-check (`after_pause=true` only for `step-6` in the cleanup fence).

### Folded host assertions (`assert_folded_sentinel_writes`)

| Host fence | Folded / boundary sentinels |
|------------|----------------------------|
| Step 1d.5 prelude | `step-1c`, `step-1d` |
| Step 2a entry | `step-1c`, `step-1d`, conditional `step-1d.5` (`brainstorm_requested` guard), `step-1d.7`, `step-1e`; `step-2a` / `step-2a.5` inside SIMPLE guard |
| Step 3 entry | `step-1e` |
| Step 2a.5 prelude | `step-2a` |
| zero-sketch degraded branch | `step-2a`, `step-2a.5` |
| Step 2b prelude | `step-2a`, `step-2a.5` |
| Step 3.5 prelude | `step-3` |
| Step 3.6 entry | `step-3.5` |
| Step 5 prelude | `step-4b` |
| Step 6 prelude | `step-5d` |
| Step 6 cleanup fence | `step-6` **after** pause-check, before `cleanup-tmpdir.sh` |
| Step 5c `design-publish.sh` fence | no unconditional `step-5c`; prose gates `step-5c` on `PLAN_WRITE_OK=true` |

### Deleted timing-only preludes (`assert_deleted_prelude_guards`)

Pure-LLM Steps **1c**, **1d**, **1d.7**, and **1e** must not retain standalone `python3 python/cli.py timing` prelude fences between their step markers. Retained preludes: Step **0c** folded discussion block (`design folded discussion block` timing mark) and Step **1d.5** (externals + boundary-local `step-1d.5` prose write).

### Branch and re-entry guards

- `assert_step3b_diagram_branches` — `architecture-diagram.skipped` only on the skip-path fence (`rm -f` before write); architectural entry removes `.skipped`; FINALIZE boundary does not write `.skipped`.
- `assert_backward_reentry_guards` — Gate B(c)/Gate C(b) re-entry clears `step-1e`…`step-4b`; Step 3 entry clears downstream sentinels and restores the direct-review bypass package (`step-2a` / `step-2a.5` / `step-2b` / `step-2b.5`).
- `assert_publish_fence_guards` — `design-publish.sh` fence sources env then pause-check and does not write `step-5b`; Gate C preview fence does not write `step-4`.

### Refactored completion-sentinel scan

`assert_step_completion_sentinels` skips host-absorbed steps (`1c`, `1d`, `1e`, `2a`, `2a.5`, `3`, `3.5`, `4b`, `5d`, `6`) and only section-greps self-writing steps: `0c`, `1d.5`, `2b`, `2b.5`, `3b`, `3.6`, `4`, `5b`, plus `assert_gate_b_bypass_branch_sentinels` for Gate-B-bypass triple writes.

`assert_bash_fences_have_pause_check` starts at `<!-- step:1c` and scans every surviving source-env Bash fence from Step 1c onward (whitespace-tolerant fence open/close). `assert_step2a_entry_simple_guard` requires pause-check after SIMPLE completion markers inside the entry fence.
