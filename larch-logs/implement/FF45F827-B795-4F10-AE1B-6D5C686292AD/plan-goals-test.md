## Goal
Implement issue #6508: [IMPLEMENTING] [BUG] Step 5 spurious notification loop: stdout banner fires premature task-notification; no-progress circuit breaker never arms for implement steps.

## Implementation Plan
## Summary

During a `/implement` run on issue #6476 (HARD difficulty, 2050 diff lines), Step 5 code review produced a spurious `<task-notification>` with `exitCode=0` immediately after the wrapper printed its banner to stdout. The `bg-wait-active` marker (`implement-step5-review`) was correctly written, so the hook guard blocked every subsequent Bash call. However, the no-progress circuit breaker that would stop the loop was never armed for `implement-step5-review` — it is hard-coded to `design-step*` steps only. The orchestrator received the same premature notification at the start of every new turn and could make no progress for 15+ turns until the review genuinely completed.

## Original report

User observed the orchestrator responding identically to repeated spurious `<task-notification>` entries for task `bcz26amf9` (Step 5 review). Each turn the hook blocked the output read with:

```
An immediate-background wait is active. End the turn and wait for <task-notification>;
do not poll progress artifacts. marker=.../.bg-wait-active STEP=implement-step5-review
```

Every probe attempt was denied. The loop continued for 15+ turns with no forward progress.

## Reproduction scenario

1. Run `/implement --merge <HARD-difficulty-issue>` on a repo where Codex is the coder.
2. After Step 3 passes, Step 5 launches `step-5-review.sh` with `run_in_background: true`.
3. `step-5-review.sh` writes `.bg-wait-active`, then prints the Step 5 banner to **stdout** before `wait "$_loop_pid"`.
4. The harness fires a `<task-notification>` on the banner stdout flush — the process is still alive and blocking on `wait`.
5. The orchestrator reads the task output (only the banner line, no `STEP5_REVIEW_STATUS`), correctly identifies the notification as premature, and ends the turn.
6. The notification is re-delivered at the start of every subsequent turn.
7. Every Bash probe is blocked by the hook guard.
8. The no-progress `task_output_read_clamp` is called but immediately `continue`s for `implement-step5-review` because the inner `case` only allows `design-step*`.
9. `arm_no_progress_task_output_clamp` is never called; the Stop-hook circuit breaker is never armed.
10. The loop continues indefinitely until Step 5 genuinely finishes and the `bg-wait-active` marker is removed.

## Expected behavior

After 2–3 turns of unchanged premature output for `implement-step5-review`, the no-progress circuit breaker fires (same behavior as `design-step*` steps), emits a Stop-hook block, and halts notification-driven re-entry until the review completes.

## Observed behavior

The orchestrator loops ~15+ turns with no progress. No circuit breaker fires. The only escape is for the review to finish on its own.

## Root cause analysis

Two independent defects combine to produce the loop:

**Defect 1 — stdout-triggered premature notification** (`step-5-review.sh`):
`_step5_bg_wait_marker_start()` writes `.bg-wait-active` before the banner printf. The banner is then printed to **stdout** (not stderr) before `python3 review-and-fix step5 ... &` is launched and before `wait "$_loop_pid"`. The harness fires a `<task-notification>` on stdout activity, not process exit. This delivers a premature notification while the wrapper is still alive and blocking on `wait`. The notification carries `exitCode=0` because the harness provisionally reports exit 0 until the process actually terminates.

**Defect 2 — no-progress circuit breaker never arms for implement steps** (`hook-bg-poll-guard.sh` `task_output_read_clamp`, line ~663):
```bash
case "$step" in
  design-step*) ;;
  *) continue ;;
esac
```
The `task_output_read_clamp` function filters to `design-step*` only. For `implement-step5-review` (and all other implement bg-wait steps), the function returns without calling `arm_no_progress_task_output_clamp`. This means the Stop-hook circuit breaker is never armed regardless of how many consecutive unchanged reads occur.

Issue #6493 / PR #6501 ("Bridge task-output clamp to no-progress Stop guard") fixed this gap but scoped the fix to `/design` steps only. The implement steps were not covered.

## Evidence

- `step-5-review.sh` lines ~260–278: `_step5_bg_wait_marker_start()` runs, then `printf '> **🔶 ...**\n'` prints to stdout before the `python3 ... &` launch and `wait "$_loop_pid"`.
- `hook-bg-poll-guard.sh` `task_output_read_clamp` (line ~663): `case "$step" in design-step*) ;; *) continue ;; esac` — skips all non-design steps.
- PR #6501 commit message: "Bridge task-output clamp to no-progress Stop guard … When the /design tasks/*.output classification Read clamp denies unchanged or empty output, arm a no-progress bridge sidecar…" — scoped to `/design`.
- Session transcript: 15+ consecutive turns with `STEP=implement-step5-review` blocking message; no circuit breaker emitted; `bcz26amf9.output` stayed at 1 line (banner only) throughout.

## Affected files

- `skills/implement/scripts/step-5-review.sh` — banner `printf` to stdout triggers the premature notification.
- `scripts/hook-bg-poll-guard.sh` — `task_output_read_clamp` filter excludes implement steps; `arm_no_progress_task_output_clamp` never called for them.

## Suggested fix(es)

**Fix 1 (lowest risk, eliminates root cause of spurious notification):**
Move the Step 5 banner `printf` to stderr:
```bash
printf '> **🔶 /implement 5: ...**\n' "$dynamic_archetypes_cap" >&2
```
The wrapper already funnels the review loop's real KV output through `_step5_stdout_file`; the banner never needs to be on stdout. This prevents the premature notification entirely.

**Fix 2 (defense-in-depth, closes the no-progress gap):**
Extend `task_output_read_clamp` to cover `implement-step*` steps alongside `design-step*`:
```bash
case "$step" in
  design-step*|implement-step*) ;;
  *) continue ;;
esac
```
Or, more precisely, enumerate the specific implement bg-wait step names (`implement-step3-checks`, `implement-step5-review`, `implement-step5-resume`, `implement-step5-self-review`, `implement-step6-checks`, `implement-step8-ship`) to match how they appear in the `.bg-wait-active` file. This limits the loop to ≤2 turns for any implement bg-wait step, matching the existing design-step behavior.

Both fixes are independent. Fix 2 alone reduces 15+ turns to ≤2–3; Fix 1 alone eliminates the premature notification so Fix 2 is never needed. Together they close both the symptom and the safety net gap.

The same `task_output_read_clamp` gap likely affects `implement-step3-checks` and `implement-step8-ship` as well, since neither matches `design-step*`.

## Open questions

- Should the fix for Fix 1 also check `step-8-ship.sh` and `step-3-checks` wrappers for similar stdout-before-wait banner patterns?
- The `implement-step3-checks` premature notification was also observed in the same session (tasks `bycfdwg0k`, `b6a3x1cp5`). Does it also have a stdout banner before `wait`? If so, the same two-fix approach applies.

## Test plan
(no test plan section in plan-file)
