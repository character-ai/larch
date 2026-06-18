## Goal
Implement issue #4731: [IMPLEMENTING] sh-to-py G3 follow-up: native plan-review step3-state skips direct-review/auto-continuation sentinel clearing.

## Implementation Plan
## Summary

The native `step3_state` ported in #4632 (merged as PR #4729) is a thin stub for `--direct-review-entry`, `--auto-continuation-entry`, and `--direct-review-pause-hygiene`. It emits `STEP3_STATE=<label>` and `REVIEW_ROUND_COUNT` but does NOT replicate the downstream-sentinel clearing/restore that `skills/design/scripts/design-step3-state.sh` performs.

## Missing behavior (vs design-step3-state.sh)

For `--direct-review-entry` / `--auto-continuation-entry`:

- clear `.completed/{step-3,step-3.5,step-3-terminal,step-3b,step-4,step-4b}` and `.step3-terminal-persisted-this-run`
- remove `.gate-b-postapply-ready-*`
- restore `.completed/{step-1e,step-2a,step-2b,step-2b.5}`
- run `cleanup_settled_step3_loop_state` (rm settled `.step3-round-*.phase` / `plan-pre-apply-round-*.txt`)
- (direct-review-entry only) remove `accepted-plan-findings-all.md` / `oos-accepted-design.md` (+ `.prev.md`) and consume `.step3-reentry`

`--direct-review-pause-hygiene` is not handled by the native stub at all.

## Impact

`skills/design/SKILL.md` call sites that invoke the native CLI (`python/cli.py plan-review step3-state --direct-review-entry` / `--auto-continuation-entry`) for direct-review re-entry and auto-continuation do not reset stale downstream sentinels or restore step-2a/2b. The kept shell `design-step3-state.sh` and the wrapper's launch-time terminal-sentinel clear cover the terminal-sentinel pair, so `/design` Step 3 will not hang, but the native re-entry path is functionally incomplete relative to the legacy.

## Origin

Pre-existing in #4632's original native port (committed in PR #4729). NOT introduced by the rebase onto #4688. The existing tests (`test_step3_state_*` in `python/test_plan_review.py`) only assert the emitted `STEP3_STATE` label, so CI does not catch the missing clearing.

## Suggested fix

Complete the native port: replicate `design-step3-state.sh`'s full clearing/restore (including the #4688 `step-3-terminal` pair) in native `step3_state`, add tests asserting the sentinel mutations, then either (a) delete `design-step3-state.sh` and repoint SKILL.md consumers to the native CLI (migration-faithful, no shims), or (b) keep the shell script as the single authority and route consumers there.

## Refs

- PR #4729 (merge commit afbdbd488)
- `python/plan_review.py` (`step3_state`)
- `skills/design/scripts/design-step3-state.sh`
- `skills/design/SKILL.md`

## Test plan
(no test plan section in plan-file)
