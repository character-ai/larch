# Review Round 4

- Mode: `diff`
- 1 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: dropped-reviewer-attempts.env not reset on `_run_round` re-entry
- **Reviewer(s)**: dyn-dyn-retry-warnings
- **Severity**: important
- **Concern**: `_run_round` clears `degraded-retry.flag` / `degraded-retry.done` at the start of each invocation but never resets `round_dir / "dropped-reviewer-attempts.env"`. `_merge_dropped_reviewer_attempt` uses monotonic `max()` over that file, so a Step 5 stall-recovery or same-round re-entry reuses prior `DYNAMIC_FAILED_SLOTS` / `DYNAMIC_DROPPED_SLOTS` even when the new `review_core_capture` has clean threshold output. `_surface_dropped_reviewer_warning` then fires again (and `review_tally.surface_warning` appends another execution-issues entry), producing false `Warnings:` inflation unrelated to the current panel run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-retry-warnings: unlink or truncate `dropped-reviewer-attempts.env` at `_run_round` entry alongside the degraded-retry sentinels; keep accumulation only within the degraded-retry loop in the same invocation. Add a test that runs `_run_round` twice on the same `round_dir` where attempt 1 has `DYNAMIC_DROPPED_SLOTS=1` and attempt 2 has zero dynamic counters, and assert `warn_count` stays 0 on the second pass.


