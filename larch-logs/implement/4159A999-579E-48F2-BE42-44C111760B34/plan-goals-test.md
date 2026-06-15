## Goal
Implement issue #4450: [IMPLEMENTING] [BUG] hook-bg-poll-guard: marker_step_completed missing design-step5c and design-step-final-summary cases — same-turn premature notification blocks session-dir reads indefinitely.

## Implementation Plan
## Summary

`hook-bg-poll-guard.sh` blocks reads of the design session directory while an immediate-background task is live. The fix in #4441 (Part A) released the guard for `design-step3-review` once `.completed/step-3` exists. The same fix was NOT applied to `design-step5c` or `design-step-final-summary`. When the same-turn premature notification race fires for either of those steps, the guard stays active indefinitely — blocking every Bash and Read tool call on the session dir until the operator manually kills the background process or the PID timeout expires.

## Reproduction

Observed live during a `/design` run on 2026-06-15 (issue #4430):

1. `design-step5c.sh` was launched as an immediate-background Bash task.
2. The task notification fired in the same turn as the launch ack (same-turn race).
3. The underlying PID (91912) was still running.
4. The hook blocked every subsequent read of the session dir: `cat .design-publish-result.env`, `ls`, `cat final-summary.md` — all returned the blocking error.
5. A PID-waiter (`until ! kill -0 <PID>`) was needed to detect actual process exit before reads were unblocked.

## Root Cause

`marker_step_completed` in `scripts/hook-bg-poll-guard.sh` only handles the one step covered by #4441:

```bash
marker_step_completed() {
  local dir="$1" step="$2" sentinel=""
  [ -n "$dir" ] || return 1
  case "$step" in
    design-step3-review) sentinel="$dir/.completed/step-3" ;;
    *) return 1 ;;   # <-- design-step5c and design-step-final-summary fall through here
  esac
  [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
}
```

When `STEP=design-step5c` or `STEP=design-step-final-summary` is in `.bg-wait-active`, `marker_step_completed` returns 1. `marker_is_live` then checks the PID with `kill -0`. If the process completed but the EXIT trap hasn't removed `.bg-wait-active` yet (the exact same-turn race that #4441 fixed for step3), the guard stays live and blocks all reads.

The `bash_segment_is_wrapper_routed` allowlist at line 220 already covers both steps for strict-wrapper-only calls:
```bash
*design-run-*.sh*design-step3-review.sh*|*design-run-*.sh*design-step5c.sh*|*design-run-*.sh*design-step-final-summary.sh*) return 0 ;;
```
But that allowance only covers re-launching the wrapper, not reading result files or any other session-dir paths.

## Suggested Fix

Add the two missing sentinel cases to `marker_step_completed`:

```bash
marker_step_completed() {
  local dir="$1" step="$2" sentinel=""
  [ -n "$dir" ] || return 1
  case "$step" in
    design-step3-review)      sentinel="$dir/.completed/step-3"   ;;
    design-step5c)            sentinel="$dir/.completed/step-5c"  ;;
    design-step-final-summary) sentinel="$dir/.completed/step-5d" ;;
    *) return 1 ;;
  esac
  [ -f "$sentinel" ] && [ ! -L "$sentinel" ]
}
```

The `.completed/step-5c` sentinel is already written by `design-step5c.sh` at line 292–293 (`PLAN_WRITE_OK=true` path) before the wrapper's EXIT trap removes `.bg-wait-active`. The `.completed/step-5d` sentinel is written by the Step 6 prelude fence for `design-step-final-summary`.

## Files to change

- `scripts/hook-bg-poll-guard.sh` — add the two `case` entries above.
- `scripts/test-hook-bg-poll-guard.sh` — add two test cases mirroring the existing `design-step3-review` coverage: one for `design-step5c` (sentinel present → guard released) and one for `design-step-final-summary` (sentinel present → guard released).
- `scripts/hook-bg-poll-guard.md` — update the "Scoped to design-step3-review" comment in the `marker_step_completed` docblock.

## Secondary issue (separate bug, for awareness)

On the same run, `final-summary.md` was never written and the `LARCH_FINAL_SUMMARY_BEGIN/END` markers never appeared in the task output. Root cause: `python/cli.py design render-final-summary` is called only in `abort_failed_publish_tail` (failure path) in `design-step5c.sh`. On the success path, `emit_final_summary_marked_from_disk` is called (line 320) but silently returns 0 because `final-summary.md` doesn't exist. This is a separate bug and should be tracked separately.

## Test plan
(no test plan section in plan-file)
