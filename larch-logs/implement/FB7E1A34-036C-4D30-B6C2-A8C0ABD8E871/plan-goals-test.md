## Goal
Implement issue #5511: [IMPLEMENTING] [BUG] design-step3-review.sh still emits spurious empty-output task-notifications after #5240 fix — set -m stderr redirect insufficient to suppress notification triggers.

## Implementation Plan
## Summary

`design-step3-review.sh` explicitly enables Bash monitor mode (`set -m`) to support process-group isolation for the `plan-review run` background process. Issue #5240 was closed as fixed with a `{ wait "$_loop_pid"; } 2>"${DESIGN_TMPDIR}/bash-job-control.log"` redirect that routes job-control messages to a log file during the wait. However, during a `/design` plan review run, the background task fired at least 10 empty-output `<task-notification>` events before the final true-completion notification arrived. These notifications each had a task output file with only 1 line (a newline), suggesting `set -m` job-control messages (or another subprocess output event) are still triggering notifications despite the stderr redirect fix.

## Original report

Background review process (`design-step3-review.sh`) fires a task-notification for every child subprocess exit (not just on true completion), many with empty stdout (just a newline). SKILL.md anti-pattern #4 documents this as the expected behavior from `set -m` and says to yield the turn when output is empty, but the underlying root cause (`set -m` firing a notification per subprocess exit) has never been eliminated in the shell script. The fix in #5240 (stderr redirect during wait) was supposed to suppress this behavior, but spurious empty-output notifications are still observed. Need to investigate whether `set -m` is still required and whether the fix is incomplete.

## Reproduction scenario

1. Run `/design` on any issue and allow Step 3 plan review to proceed with a full panel (Cursor + Codex reviewers).
2. The `design-step3-review.sh` script is launched in `run_in_background` mode.
3. Observe task notifications as the panel runs. Multiple notifications arrive with task output files that contain only a newline (1 line, ~0 content bytes).
4. The final real completion notification arrives only after all reviewers and the loop finish.

Cannot be deterministically triggered with a single command — it depends on the number of Codex/Cursor subprocess exits during the review, which vary by plan size and panel composition.

## Expected behavior

- Task notifications should fire only when the background script writes meaningful output to its stdout.
- Empty-output notifications should not fire, or should fire at most once (as a spurious job-control byproduct) rather than 10+ times per review run.
- The `#5240` fix should have eliminated or substantially reduced the frequency.

## Observed behavior

- During a plan review with 11 reviewer slots (5 Cursor + 5 Codex static + 1 Codex generic + 2 dynamic), at least 10 task notifications arrived before the true completion notification.
- Each spurious notification had a task output file with 1 line (a newline or empty string).
- The shell script has `set -m` enabled at line 388 and redirects stderr of `wait` to `${DESIGN_TMPDIR}/bash-job-control.log` at line 439.
- Despite this redirect, spurious notifications still occur.
- SKILL.md anti-pattern #4 documents the workaround: "When task output is empty (just a newline or nothing), end the turn without probing — those are spurious bash job-control notifications from `set -m`."

## Root cause analysis

The `#5240` fix was: `{ wait "$_loop_pid"; } 2>"${DESIGN_TMPDIR}/bash-job-control.log"`. This redirects stderr during the `wait` call, which should prevent Bash job-control messages from reaching the task output stream.

However, the Claude Code `run_in_background` task notification mechanism may fire on ANY write to the process's output stream (stdout or stderr), or on certain process state changes that don't correspond to actual stdout writes. Possible reasons the fix is incomplete:

1. **Stdout output from the Python loop itself**: `python3 ... plan-review run ... >"$_plan_review_stdout_file"` redirects Python's stdout to a file. But if the Python process writes anything to stderr (outside the `wait` redirect scope), that could still trigger a notification.
2. **Notification on process state change, not output**: The `run_in_background` mechanism might fire a notification on any `SIGCHLD` or subprocess exit event, regardless of whether the subprocess wrote any output. In that case, redirecting stderr of `wait` doesn't suppress the notification trigger.
3. **`set -m` messages on a different FD**: Bash `set -m` job-control output may be going to FD 2 before it's redirected, or may bypass the specific `{ wait ...; } 2>...` redirect if it's written at a different point.
4. **Incomplete scope of redirect**: The redirect only covers the `wait` call, not the entire `_step3_review_teardown_loop_group` or other subprocess-spawning code that runs around it.

The uncertainty here is whether the notifications are caused by `set -m` output reaching the task stream, or by some other mechanism in the Claude Code `run_in_background` implementation.

## Evidence

- `skills/design/scripts/design-step3-review.sh` lines 386-408: explicit `set -m` enable with guard requiring monitor mode for process-group isolation. If monitor mode is unavailable, the script fails with `panel-init-failed`.
- `skills/design/scripts/design-step3-review.sh` line 439: `{ wait "$_loop_pid"; } 2>"${DESIGN_TMPDIR}/bash-job-control.log"` — the #5240 fix.
- Comment at line 436: "Redirect stderr during wait so bash job-control messages emitted by `set -m` do not reach the task output file and fire spurious task-notifications (#5240)."
- `${DESIGN_TMPDIR}/bash-job-control.log`: created during the run and contains Bash job-control output — confirms the fix IS routing `set -m` messages there, but notifications still fire.
- SKILL.md Anti-pattern #4, current text: "When task output is empty (just a newline or nothing), end the turn without probing — those are spurious bash job-control notifications from `set -m` in the review script (#5240)." — documents the workaround, suggesting the root cause is still present post-#5240.
- Observed: 10+ empty-output task notifications during a single plan review with 11 reviewer slots.
- Issue #5240 was closed as [DONE] but behavior persists.

## Affected files

- `skills/design/scripts/design-step3-review.sh`: contains `set -m` enable and the partial stderr redirect fix.
- `skills/design/SKILL.md`: Anti-pattern #4 documents the workaround but the underlying trigger is unresolved.
- `skills/design/scripts/design-step3-review.md`: sibling contract for the script.

## Suggested fix(es)

1. **Investigate whether `set -m` is still required**: process-group isolation may be achievable without monitor mode. If the script can be restructured to use `setsid`, `bash --posix`, or an explicit new process group (`set +m` + explicit `kill -- -$PGID`), monitor mode could be removed, eliminating the job-control notification source entirely.

2. **Broader stderr redirect**: instead of redirecting stderr only during `wait`, redirect the entire subprocess-teardown section — `_step3_review_teardown_loop_group`, `_step3_review_kill_tmpdir_processes`, and related calls — to the log file, not just the `wait`.

3. **Investigate Claude Code notification trigger**: determine whether the `run_in_background` notification mechanism fires on stdout writes, stderr writes, or process state changes. If it fires on process state changes, the stderr redirect is fundamentally insufficient and a different approach (e.g., a sentinel-polling model instead of run_in_background) is needed.

4. **Audit `bash-job-control.log` contents**: during a run that produces many spurious notifications, inspect the log to confirm `set -m` messages ARE being captured there. If the log is empty but notifications still fire, the cause is something other than `set -m` job-control messages.

## Open questions

- Does `design-step3-review.sh` actually require `set -m`, or is process-group isolation achievable without it? Lines 399-408 suggest it is a hard requirement (failure = `panel-init-failed`).
- Does the Claude Code `run_in_background` notification mechanism fire on subprocess output vs process state changes? The answer determines whether stderr redirection can ever fully suppress spurious notifications.
- Is `bash-job-control.log` non-empty during a run that produces many spurious notifications? If yes, the fix captures the messages but doesn't prevent the notification trigger. If no, the cause is something other than `set -m`.
- Is issue #5478 (`[BUG] Orchestrator probes step-3-terminal sentinel on every spurious task-notification even when output is empty`) a downstream symptom of this same root cause?

## Test plan
(no test plan section in plan-file)
