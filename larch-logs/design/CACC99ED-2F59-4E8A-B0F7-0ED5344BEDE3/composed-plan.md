## Plan

## Approach

Use the minimum fix in `design-step3-review.sh`: keep the atomic post-loop `trap` replacement, but replace the sentinel-only handler with a small wrapper that removes `$DESIGN_TMPDIR/.bg-wait-active` and then calls `_step3_review_guarantee_completed_sentinels`.

This preserves the #4724 intent: no gap with no `EXIT` trap. It also restores the cleanup contract lost when the original `_step3_review_cleanup` trap was replaced after the review loop exits.

## Files to modify/create

### UPDATED: skills/design/scripts/design-step3-review.sh

- Add a post-loop exit helper `_step3_review_guarantee_post_loop_exit`:
  - `local _exit_rc=$?`
  - `trap - EXIT TERM HUP INT` — disarm all signal traps before cleanup (mirrors `_step3_review_cleanup`; prevents recursive trap re-entry on nested `exit`)
  - `rm -f "$DESIGN_TMPDIR/.bg-wait-active" 2>/dev/null || true`
  - `_step3_review_guarantee_completed_sentinels`
  - `exit "$_exit_rc"`
- Change the post-loop trap from `_step3_review_guarantee_completed_sentinels` to `_step3_review_guarantee_post_loop_exit`.
- Update the nearby #4489 / #4724 comment to state that the replacement trap now owns both marker removal and sentinel guarantee.

### UPDATED: skills/design/scripts/test-design-step3-review.sh

- Extend the existing normal post-loop sentinel harness around `D_SENTINEL`.
- After the wrapper exits, assert that `$D_SENTINEL/.bg-wait-active` is absent.
- Keep the existing assertions that stale terminal state is cleared and `step-3-terminal` is minted.
- Optionally add a static guard that the replacement `trap` names the new cleanup-plus-guarantee helper, not `_step3_review_guarantee_completed_sentinels` directly.

### UPDATED: skills/design/scripts/design-step3-review.md

- Update the invariant that describes the post-loop `EXIT` trap.
- State that both the original cleanup trap and the atomic post-loop replacement trap remove `.bg-wait-active`.
- Keep the split-sentinel explanation unchanged: `.completed/step-3-terminal` remains the hook-release target, and `.completed/step-3` remains the Gate B milestone.

## Edge cases

- Preserve the exit status from `normalize-status`, including nonzero `postplan-failed` and `panel-init-failed`.
- Do not move marker removal into `_step3_review_guarantee_completed_sentinels` unless needed. That helper is about sentinels, and making it remove the marker would broaden its side effects.
- Do not change `scripts/hook-bg-poll-guard.sh` for this fix. Its sentinel and dead-PID release paths are not the root cause.

## Failure modes

- If the new trap helper forgets to preserve `$?`, Step 3 can report the wrong terminal status.
- If the helper is not used in the post-loop trap, the regression remains.
- If marker cleanup runs before detach handling in the main cleanup trap, external TERM/HUP/INT behavior could change. Keep detach behavior in `_step3_review_cleanup` intact.

## Testing strategy

- Run `bash skills/design/scripts/test-design-step3-review.sh`.
- Run `bash scripts/test-hook-bg-poll-guard.sh` to confirm existing hook-release behavior still passes.
- Run `bash scripts/test-design-structure.sh` if the script doc or Step 3 contract prose changes trigger structure guards.
- Run `shellcheck skills/design/scripts/design-step3-review.sh skills/design/scripts/test-design-step3-review.sh` or the repo's scoped relevant checks if available.

confidence: high

## Acceptance

- Run `bash skills/design/scripts/test-design-step3-review.sh`.
- Run `bash scripts/test-hook-bg-poll-guard.sh` to confirm existing hook-release behavior still passes.
- Run `bash scripts/test-design-structure.sh` if the script doc or Step 3 contract prose changes trigger structure guards.
- Run `shellcheck skills/design/scripts/design-step3-review.sh skills/design/scripts/test-design-step3-review.sh` or the repo's scoped relevant checks if available.

confidence: high

review_status: ok
rounds_completed: 2
difficulty: MODERATE
diff_lines: 35
