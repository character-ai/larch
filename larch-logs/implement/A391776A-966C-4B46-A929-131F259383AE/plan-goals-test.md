## Goal
Implement issue #5922: [IMPLEMENTING] [BUG] /implement Step 4: commit wrapper false-stalls when main agent commits ad hoc mid-session.

## Implementation Plan
## Summary

`/implement` Step 4's implementation-commit wrapper (`_run_step4_commit_leg` in `python/larch/implement/dispatch_commit_route.py`) only treats "changes are already committed" as a no-op when `DISPATCHER_COMMITTED=true` in `ship-seed-input.env`. That flag is set exclusively by `step2_post_dispatch_main` in `python/larch/implement/dispatch_ship_seed.py`, which runs only after an **external** Codex/Cursor Step 2 dispatch. There is no equivalent guard for the case where the **main agent itself** commits changes ad hoc, outside the tracked `implementation-commit-message.txt` / `implementation-commit-paths.nul` flow.

## Observed failure (run 992FFBB6, issue #5891, PR #5913, 2026-07-01)

Under `--force` (`coder=claude`, main agent does Step 2 implementation directly — see issue #5921), main Claude hit a `skill-closure-growth` doc-size lint failure while iterating on Step 3 checks, and fixed it with a direct `git commit` (sha `b494dfae7`) that also happened to cover a stray regenerated `python/skill-closure-baseline.json`. When Step 4's commit wrapper then ran its own commit attempt against its own pathspec, it found nothing left to commit (`COMMITTED=false`, "nothing to commit, working tree clean"), which `_run_step4_commit_leg` misclassified as `implementation-commit-failed`, seeding a false `STALL_TRACKING=true`. The run's own execution-issues log confirms this was benign (the changes were genuinely already committed) and required a manual `stall-recovery clear-stall` plus a manual rebase checkpoint to recover.

## Why this matters now

Issue #5921 proposes making `--self-implement` an explicit, default-false opt-in flag so "main agent does the coding" becomes a normal, intentionally-chosen flow rather than a rare `--force` side effect. Once that ships, this failure mode will recur more often: any `--self-implement` run where the main agent commits ad hoc mid-loop (e.g. to fix a lint/check failure it discovers along the way) will hit the same false stall, costing a retry cycle and an unnecessary `STALL_TRACKING` recovery.

## Suggested fix direction

Extend the "already committed, treat as no-op" detection in `_run_step4_commit_leg` beyond the `DISPATCHER_COMMITTED` flag — e.g., before attempting the wrapper's own commit, check whether the expected pathspec is already clean relative to the current `HEAD` (via `git status --porcelain -- <pathspec>` or an equivalent diff check), and short-circuit to the same `"noop"` outcome used for the dispatcher-committed case, regardless of which coder produced the commit.

## References

- `python/larch/implement/dispatch_commit_route.py::_run_step4_commit_leg` (the gap)
- `python/larch/implement/dispatch_ship_seed.py::step2_post_dispatch_main` / `_mark_dispatcher_committed` (the existing dispatcher-only guard)
- `larch-logs/implement/992FFBB6-7847-4095-9EA9-AEAB2BEF0677/execution-issues.ndjson` (observed incident)
- Related: #5921 (`--self-implement` flag proposal)

## Test plan
(no test plan section in plan-file)
