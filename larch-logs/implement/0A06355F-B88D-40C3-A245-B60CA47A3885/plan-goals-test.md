## Goal
Implement issue #5418: [IMPLEMENTING] [BUG] review loop: normalize-status emits stdout before terminal sentinel, harness replays notification each turn, no identical-content guard in SKILL.md.

## Implementation Plan
## Summary

`design-step3-review.sh` emits KV output to task stdout (via `normalize-status`) before `.completed/step-3-terminal` is written, so the Claude Code harness fires a `<task-notification>` with non-empty content while the terminal sentinel is absent. The harness then re-delivers the same notification on every subsequent main-agent turn. `design-background-wait.md` has no guard for repeated identical notifications, so the main agent probes once per turn — returning WAIT each time — burning arbitrarily many turns until the review finishes and the sentinel is written.

## Original report

review loop premature task-notifications burn turns: normalize-status stdout fires before sentinel, harness replays identical notification each turn, no SKILL.md guard for repeated identical content

## Reproduction scenario

1. Run `/design <issue-number>` on any issue that triggers plan review with continuation (two or more review rounds).
2. The background task `design-step3-review.sh` launches `plan-review run --mode loop` with its stdout captured to a temp file.
3. After round 1, `plan-review run` decides to auto-continue (round 2). It calls `step3-state --auto-continuation-entry` and loops. Separately or independently, `normalize-status` runs after `wait "$_loop_pid"` returns.
4. `normalize-status` emits KV lines to task stdout (e.g. `LOOP_STATUS=complete`, `FINAL_ROUND_NUM=1`, `STEP3_REVIEW_LOOP_STATUS=complete`, `NEXT_ACTION=step3b`) before the bash EXIT trap writes `.completed/step-3-terminal`.
5. The harness fires a `<task-notification>` with that non-empty content.
6. The main agent probes `.completed/step-3-terminal` — gets WAIT. Yields.
7. On the next turn the harness re-fires the identical notification. Main agent probes again — WAIT. Repeat.
8. Each turn one Bash tool call is burned until the review truly completes and the sentinel is written.

This was observed during a review with two rounds (round-1 directory fully populated, round-2 directory being populated) while ~15 identical notifications fired sequentially.

## Expected behavior

After the main agent probes and gets WAIT, no further probes should be needed until a genuinely new notification arrives with distinct content or the process exits. The harness should not re-fire the same notification content repeatedly; and even if it does, the main agent should yield without probing after the first WAIT from a given content fingerprint.

## Observed behavior

Every premature notification (identical content) caused one Bash tool call (probe) that returned WAIT. With 15+ re-delivered notifications the main agent burned 15+ turns, each containing a probe and a WAIT response, before the review completed.

## Root cause analysis

Two layered causes:

**Cause 1 — sentinel written after stdout emission (primary).**
`normalize-status` (`plan_review.py` line 874: `_step3_emit_normalize_envelope_with_next_action`) prints KV lines to the bash script's stdout channel before the bash EXIT trap runs. The EXIT trap at `_step3_review_guarantee_completed_sentinels` writes `.completed/step-3-terminal` only when `.step3-terminal-persisted-this-run` already exists. This sidecar is written by `step3_loop_write_terminal_step3` inside the Python loop, but the loop may not have written it yet at the time `normalize-status` runs. Result: notification fires; probe returns WAIT; sentinel is written only after the bash process exits and the EXIT trap completes.

**Cause 2 — harness re-delivers identical notifications (amplifier).**
The Claude Code harness appears to re-deliver the last non-empty `<task-notification>` on each main-agent turn while the terminal sentinel is absent. This is probably a "ensure delivery" mechanism in the harness, but it interacts badly with the sentinel-before-stdout ordering gap above.

**Cause 3 — no de-duplication guard in SKILL.md / design-background-wait.md (missing defense).**
`design-background-wait.md` instructs the main agent to probe once per recovery turn on any non-empty notification, with no exception for repeated identical content. There is no rule of the form "if this notification has the same content as the previous notification in this wait sequence, yield without probing."

The possible mechanism for `normalize-status` running while the Python loop is still active: with `set -m` (job control), bash may return early from `wait "$_loop_pid"` when SIGCHLD fires from a child of `$_loop_pid` (a Codex/Cursor subprocess). This is uncertain and needs verification, but the evidence (round-2 artifacts being written after normalize-status output) is consistent with it.

## Evidence

- `design-step3-review.sh` line 439: `{ wait "$_loop_pid"; } 2>"$DESIGN_TMPDIR/bash-job-control.log"` — stderr redirected, but stdout is unconstrained after wait returns.
- `design-step3-review.sh` lines 458–464: `normalize-status` runs and emits to stdout before `exit "$_step3_normalize_rc"` triggers the EXIT trap.
- `plan_review.py` line 874: `_step3_emit_normalize_envelope_with_next_action` — emits KV to stdout. Does NOT call `step3_loop_write_terminal_step3`. Only `step3_loop_emit_envelope` (terminal loop paths) and `_step3_review_write_result_env` (synthesis paths) call that function.
- `plan_review.py` line 382–398: `step3_loop_write_terminal_step3` writes BOTH `.completed/step-3-terminal` AND `.step3-terminal-persisted-this-run` atomically. Neither was present during the premature notifications.
- `design-step3-review.sh` `_step3_review_guarantee_completed_sentinels` (line 343): only writes `.completed/step-3-terminal` when `.step3-terminal-persisted-this-run` exists. If the Python loop never wrote it, the EXIT trap cannot write the terminal sentinel.
- Observed during incident: `plan-review/round-1/` fully populated, `plan-review/round-2/` being populated, `.step3-review-result.env` absent, `.completed/step-3-terminal` absent — all while notifications kept firing with `LOOP_STATUS=complete FINAL_ROUND_NUM=1`.
- `STEP3_RESULT_ENV_WRITTEN=true` in the notification output does not match any larch source code string. It was present in all 15+ notifications. This may be a harness-synthetic field.
- `design-background-wait.md` "Step 3 task notification boundary" section: no identical-content skip rule exists.

## Affected files

- `skills/design/scripts/design-step3-review.sh` — bash wrapper; `normalize-status` stdout emission timing.
- `python/plan_review.py` — `normalize-status` entry point, `step3_loop_write_terminal_step3`, `step3_loop_emit_envelope`, `step3_loop_persist_envelope`.
- `skills/shared/design-background-wait.md` — Step 3 task notification boundary rule; missing de-duplication guard.
- `skills/design/SKILL.md` — Step 3 premature-notification recovery protocol; references `design-background-wait.md`.

## Suggested fix(es)

**Fix A (close the race window — primary fix):**
In `normalize_status_main` (or its delegated function in `plan_review.py`), call `step3_loop_write_terminal_step3(tmpdir)` before `_step3_emit_normalize_envelope_with_next_action`. This ensures the terminal sentinel exists by the time any notification fires. The EXIT trap in the bash script becomes a no-op for the normal path. Guard: only call `step3_loop_write_terminal_step3` when the result env is present and valid (i.e., the loop wrote state successfully). On synthesis paths (`_step3_review_write_result_env`), the function already calls `step3_loop_write_terminal_step3` — this fix would extend that to the normal normalize path.

**Fix B (de-duplication guard — defensive fix):**
Add a rule to `skills/shared/design-background-wait.md` "Step 3 task notification boundary" section: if a non-empty `<task-notification>` arrives with identical content to the immediately preceding non-empty notification in this wait sequence, yield without probing. The main agent should track a fingerprint (e.g., first 200 chars) of the last notification content and skip the probe when content matches.

**Fix C (investigate the set -m wait interruption — root-cause fix):**
Determine whether `wait "$_loop_pid"` can return early due to SIGCHLD from a grandchild process when `set -m` is active on macOS bash 3.2. If so, add a guard loop: re-enter wait when `kill -0 "$_loop_pid"` confirms the process is still alive and `_plan_review_rc` is signal-like.

Fixes A and B are independent and both valuable. Fix A closes the window at the source. Fix B prevents turn-burning even if similar races appear in the future.

## Open questions

1. Can `wait "$_loop_pid"` return early under bash 3.2 with `set -m` when a grandchild (Codex subprocess of the Python loop) exits? This would explain how `normalize-status` runs while the Python loop is in round 2.
2. What is the harness mechanism for re-delivering identical notifications? Is it intentional "ensure delivery" behavior, and can it be bounded (e.g., maximum re-deliveries before the sentinel write)?
3. Should `step3_loop_write_terminal_step3` be idempotent-safe for the normalize path, or does it need a guard to prevent writing on error/synthesis paths?

## Test plan
(no test plan section in plan-file)
