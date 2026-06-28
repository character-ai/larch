## Goal
Implement issue #5677: [IMPLEMENTING] [BUG] /design Claude plan-voter emits empty output (exit 124) on ~14% of runs.

## Implementation Plan
## Summary

The `/design` Step-3 plan-review Claude voter still emits empty output (exit 124 / "No messages returned from query", or a subprocess timeout) on ~14% of recent runs, degrading the review panel. The panel was hardened by #5637 to tolerate one failed voter (degrade to 2/3), but the voter's own root-cause failure was filed as #5636 and closed NOT_PLANNED, so the recurrence is untracked and the proposed hardenings were never built.

## Evidence (last 50 /design run logs)

- **7/50** of the most-recent runs (6 of them the newest v52.1.4) have an empty `claude-vote-output.txt` with `.step3-report-panel-failed.recorded` set.
- The `claude-vote-output.txt.failure-diag` sidecar shows `Error: No messages returned from query` (3 runs) or `claude subprocess timed out` (1 run).
- Affected v52.1.4 runs: `68A29E55`, `64D32C85`, `1EA7A598`, `129900E4`, `F08310E2`, `58D235D7` (flushed via PRs #5650/#5649/#5652/#5651/#5634/#5633).
- The `claude.ai connectors are disabled…` warning prints on *successful* votes too (41/50 succeed with that same warning on stderr), so it is a red herring, not the failure cause.

## Root cause (likely shared with the Step-7a code-flow timeout lane)

The nested `claude` subprocess returns no usable output, surfaced as exit 124 + "No messages returned from query". Possibly aggravated by `--permission-mode plan` interacting with an active `ANTHROPIC_API_KEY` auth source. Treated as environmental by #5636.

## Suggested fix (the hardenings #5636/#5637 deferred)

- Add a bounded voter retry on empty-output / exit 124 in `python/larch/review/plan_review_panel.py::dispatch_voters`.
- Investigate the `--permission-mode plan` vs `ANTHROPIC_API_KEY` precedence path in the shared launcher (`python/larch/agents/agents.py`).
- Surface the failed voter in the reviewer-status table for observability.

## References

- #5637 (closed, commit `9174b1856`) fixed panel resilience (degrade to 2/3), not the voter. #5636 (closed NOT_PLANNED, dup of #5637) is the voter root cause, with hardenings dropped.
- Reopening as a tracked hardening per operator direction. Surfaced by a post-merge audit of the last 50 `/design` run logs.

## Test plan
(no test plan section in plan-file)
