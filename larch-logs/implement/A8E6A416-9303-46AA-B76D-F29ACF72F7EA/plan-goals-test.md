## Goal
Implement issue #5240: [IMPLEMENTING] [BUG] Background review process emits spurious task-notifications on every subprocess exit (set -m job-control output).

## Implementation Plan
## Summary

Background review processes (`design-step3-review.sh`, `step-5-review.sh`) emit dozens of spurious `<task-notification>` events during a typical review run — one per child subprocess exit — rather than a single notification at true completion or error. Each spurious event triggers a Claude Code orchestrator response turn, burning model tokens for no useful work. The `/design` orchestrator's "one foreground probe per recovery turn" protocol amplifies this into 50+ wasted turns per design run.

## Original report

Background review process emits spurious task-completion notifications on every subprocess exit (via bash job-control / set -m output), not only on actual completion or error. In both /design and /implement, design-step3-review.sh (and equivalent implement review launchers) use set -m monitor mode. When each internal child process (Codex reviewer, Cursor reviewer, voter, aggregator, etc.) exits, bash sends a job-control status line to the script's stdout. Claude Code's run_in_background task framework treats every stdout flush as a completion event and fires a task-notification. Result: dozens of spurious task-notification events fire during a typical 5-10 minute review run. Each one triggers a Claude Code response turn, each turn costs model tokens, and none carry useful information.

## Reproduction scenario

1. Run `/design <issue-number>` on any non-trivial issue.
2. When Step 3 plan review launches (`design-step3-review.sh` with `run_in_background: true`), observe the `<task-notification>` events.
3. Expect: one notification at completion.
4. Observe: one notification per subprocess exit (each Codex/Cursor reviewer, voter, aggregator) — typically 10–30 notifications during a single round.

## Expected behavior

- Background review tasks fire exactly one `<task-notification>` when the script exits (completion or error).
- Intermediate subprocess exits inside the review process do not produce notifications visible to the Claude Code orchestrator.
- The orchestrator receives either a completion notification (containing normalize-status output) or an error notification, with no spurious intermediate events.

## Observed behavior

- Dozens of `<task-notification>` events fire during a single plan review round — one per internal child subprocess exit.
- Most events have empty task output (the task output file contains only a newline or is empty).
- The bash wrapper script (PID confirmed still running) has not yet exited when these events fire.
- Each event causes the `/design` orchestrator to generate a new response turn (probe + yield), costing ~150–200 tokens per turn.
- In a recent run: 50+ spurious turns fired during one ~10-minute review, consuming thousands of tokens for no useful work.

## Root cause analysis

**Mechanism**: `design-step3-review.sh` enables bash monitor mode (`set -m`) to support process-group isolation — killing reviewer subprocesses requires a process group. With monitor mode active, bash sends job-control status messages (e.g., `[1] Done python3 ...`) to its stderr whenever a tracked background job exits. The Claude Code `run_in_background` task framework captures both stdout and stderr of the script, so these messages appear in the task output file. Each flush triggers a `<task-notification>`.

**Contributing factor in `/design`**: The `/design` SKILL.md "one foreground probe per recovery turn" protocol was added to detect completion faster (#4489, #4725). This protocol probes the sentinel on every notification — turning each spurious notification into a wasted response turn. The `/implement` SKILL.md correctly says "end the turn" on premature empty notifications (no probe), but `/design` probes on every one.

**Why monitor mode is present**: Process group isolation is required to kill reviewer subprocesses when the wrapper exits or receives SIGTERM. Removing `set -m` would break the subprocess kill mechanism.

## Evidence

- `design-step3-review.sh` lines 386–397: conditionally enables `set -m`; line 388 explicitly enables it when not already set.
- `design-step3-review.sh` lines 355–384: `_step3_review_teardown_loop_group` uses `kill -- -"$_pid"` (negative PID = process group), requiring monitor mode.
- `design-step3-review.sh` lines 423–434: the Python plan-review subprocess is launched with `&` and its stdout redirected to `"$_plan_review_stdout_file"`, so Python stdout does not reach the task output. Job-control messages (bash internal) do, however.
- `/implement` SKILL.md NEVER #8: confirms the "end the turn" approach for premature empty notifications — no probing.
- `/design` SKILL.md Step 3 recovery: "one foreground probe of `.completed/step-3-terminal` per recovery turn **may** confirm completion" — optional but being treated as mandatory in practice.
- `scripts/hook-bg-poll-guard.sh` line 74, 261, 431: documents the premature-notification problem and blocks sleep-loop recovery waiters.

## Affected files

- `skills/design/scripts/design-step3-review.sh` — primary source of spurious output; uses `set -m`
- `skills/implement/scripts/step-5-review.sh` — implement equivalent; likely has the same issue
- `skills/design/SKILL.md` Step 3 recovery protocol — "may probe" treated as mandatory
- `skills/implement/SKILL.md` NEVER #8 — already has correct "end the turn" guidance

## Suggested fix(es)

**Fix A (suppress spurious output — preferred):** Redirect bash job-control messages away from the task output stream without removing monitor mode. One approach:

```bash
# Before backgrounding the Python subprocess:
exec 2>/dev/null   # suppress stderr job-control output for the wait phase
_loop_pid=$!
wait "$_loop_pid"
exec 2>&1          # restore stderr for normalize-status output
```

Or redirect job notifications to a log file:
```bash
exec 2>"$DESIGN_TMPDIR/bash-job-control.log"
```

The normalize-status output goes to stdout (not stderr), so it still reaches the task output file. This fix prevents spurious notifications at the source.

**Fix B (orchestrator — /design):** Align the `/design` recovery protocol with `/implement`: when a premature empty notification fires, **end the turn immediately** with no tool calls, no probe. Do not probe `.completed/step-3-terminal` per notification. Reserve the probe for turns where there is positive evidence the review may have finished (e.g., non-empty task output).

**Fix C (orchestrator — /design):** Check whether the task output is empty before probing. If the task output file is empty (just a newline), skip the probe and end the turn. Only probe when there is actual content in the task output (indicating the bash script has written its normalize-status output).

Fix A is the right systemic fix. Fixes B/C are orchestrator-level mitigations that reduce token waste independently.

## Open questions

- Does `step-5-review.sh` also use `set -m`? Investigation suggests yes (same process-group kill pattern), but needs confirmation.
- Is there a way to suppress bash job-control output without disabling monitor mode entirely? (`set +m` would break the kill mechanism.)
- Should the `/design` SKILL.md change "may confirm completion" to explicitly say "do not probe if task output is empty"?
- Are there other background bash scripts that use `set -m` with similar spurious-notification behavior?

## Test plan
(no test plan section in plan-file)
