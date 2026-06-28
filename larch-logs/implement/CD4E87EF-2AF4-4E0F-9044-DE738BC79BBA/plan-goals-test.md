## Goal
Implement issue #5676: [IMPLEMENTING] [BUG] Committed final-summary mislabels stalled-then-shipped runs as "stalled".

## Implementation Plan
## Summary

The committed `final-summary.md` mislabels stalled-then-shipped `/implement` runs as `stalled`, even though the run recovered and shipped a merged PR. This is the companion to #5646, which fixed the analogous `bailed` mislabel but guarded only the `bailed` catch-all, leaving the `stalled` path unaddressed.

## Evidence (last 50 /implement run logs)

- **10/50** of the most-recent runs have committed `Outcome: stalled` despite shipping merged PRs. (Another 38/50 were the `bailed` variant fixed by #5646; 0/50 carry a success label.)
- Examples (stalled-then-merged): `BC6EFF24` (#5637, merged PR #5665); `2931787A` (#5563, merged PR #5613).

## Root cause

Same pre-ship-snapshot timing as #5646: the committed final-summary is written at the Step-7a flush, before ship-state is seeded. `python/larch/state/stall_recovery.py::normalized_outcome_values` sets `outcome = "stalled"` when `any_stall or phase_stalled` is true at snapshot time. The `shipping` neutral-label branch added by #5646 sits *after* the stalled check, so a run that stalled mid-flight then recovered and shipped freezes at `stalled` in the committed log. The stale-stall-overlay downgrade (`_phase_counts_as_stalled`, #5169) only covers ship phases ci-initial / rebase / pr-create.

## Suggested fix

Extend the #5646 approach so a stalled snapshot that lacks failure signals and is still in-flight reconciles to the neutral `shipping` label (or is re-evaluated post-ship), mirroring the bailed→shipping guard. Files: `python/larch/state/stall_recovery.py` (`normalized_outcome_values`), `python/larch/report/final_report.py`.

## References

- #5646 (closed, commit `5b491fd46`) fixed the bailed catch-all only. #4900, #2524 (closed) are prior facets of the same mislabel class.
- Observability only: merges always succeeded. Surfaced by a post-merge audit of the last 50 `/implement` run logs.

## Test plan
(no test plan section in plan-file)
