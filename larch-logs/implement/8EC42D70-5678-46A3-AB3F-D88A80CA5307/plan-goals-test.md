## Goal
Fix reviewer subprocess hang: timed-out Claude generic slot degrades gracefully instead of aborting collect-findings.sh

## Implementation Plan

Goal: Fix reviewer subprocess hang so timed-out/killed Claude generic slot degrades gracefully.

### Files

1. scripts/launch-claude-subprocess.sh — Add PID sidecar (${OUTPUT_CANON}.pid) containing $$; run subprocess in background so SIGTERM trap can kill it; extend EXIT trap to remove .pid.
2. scripts/wait-for-reviewers.sh — On TIMEOUT for any sentinel, read ${sentinel%.done}.pid and send SIGTERM if it exists; log attempt to stderr; exit behavior unchanged (0).
3. skills/review/scripts/collect-findings.sh — Separate stdout/stderr from wait-for-reviewers.sh; parse stdout for TIMEOUT lines; treat timed-out slots as logged failures (append_review_failure) but continue; treat non-zero wait_rc as logged partial-failure rather than abort.
4. scripts/launch-claude-subprocess.md — Document PID sidecar.
5. scripts/wait-for-reviewers.md — Document on-timeout kill.
6. skills/review/scripts/collect-findings.md — Document timeout-degradation.
7. scripts/test-launch-claude-subprocess.sh — Assert .pid file written during execution.
8. skills/review/scripts/test-collect-findings.sh — Assert timed-out slot is logged but collect continues with COLLECT_OK=true.

### Key decisions

- Use $$ (launch-claude-subprocess.sh's own PID) as the PID to record; run subprocess via background + wait so SIGTERM trap fires immediately.
- wait-for-reviewers.sh: PID file is ${sentinel%.done}.pid; kill is best-effort (PID may be gone; ignore errors).
- collect-findings.sh: separate stdout to wait_stdout_log, stderr to wait_stderr_log; redirect collect stderr replay from wait_stderr_log (not wait_stdout_log).
- Non-zero wait_rc treated as partial failure: log it, parse any stdout that was produced, continue.

### Edge cases

- .pid file may not exist (timeout command unavailable path — subprocess already exited naturally): skip kill silently.
- Multiple timed-out slots: parse all TIMEOUT lines, log each one separately.
- wait-for-reviewers.sh killed by external signal (non-zero exit but no TIMEOUT lines in stdout): log the non-zero exit as a failure, treat all non-done sentinels as timed-out.

## Test plan
(no test plan section in plan-file)
