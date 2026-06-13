## Decision 1: Fix location
- **Question**: Where exactly does the reclassification bug live?
- **Resolution**: `_maybe_review_required` in `python/merge.py`. When both admin and plain merges fail (`MERGE_RESULT_ADMIN_FAILED`) and `pr_review_decision` returns `REVIEW_REQUIRED`, the function unconditionally reclassifies as `MERGE_RESULT_REVIEW_REQUIRED` without checking whether the actual failure was a merge conflict.
- **Source**: codebase

## Decision 2: Return value for conflict-race case
- **Question**: Should we return a new constant or reuse an existing result code?
- **Resolution**: Return `MERGE_RESULT_MAIN_ADVANCED` when conflict signals are detected. Ship.py already handles `MAIN_ADVANCED` at line 1643 by looping back to the CI monitor, which detects the behind/dirty state and triggers a rebase. No new constant or changes to ship.py or config.py required.
- **Source**: codebase

## Decision 3: Conflict-signal keywords
- **Question**: Which error substrings indicate a merge-conflict race?
- **Resolution**: Check for "merge conflicts", "not mergeable", and "cannot be cleanly created" in `outcome.error`. All three appear in the actual GitHub API error reported in the bug.
- **Source**: issue body

## Decision 4: Rebase budget check
- **Question**: Should `_maybe_review_required` check whether the rebase budget is exhausted before returning MAIN_ADVANCED instead of REVIEW_REQUIRED?
- **Resolution**: No — `_maybe_review_required` does not have `rebase_count`. The CI monitor's existing `if rebase_count >= config.CI_MONITOR_MAX_REBASES:` bail (ci_monitor.py:156) handles exhaustion. If the budget is spent, the CI monitor bails as `too-many-rebases` (STALLED), which is still better than `review-required` (NEEDS_USER_INPUT with wrong diagnosis).
- **Source**: codebase

## Decision 5: Bash parity
- **Question**: Should ship-pr.sh / merge-pr.sh also receive a fix?
- **Resolution**: Python path only. The bash path is legacy; the reported incident hit the Python path. bash ship-pr.sh already has partial handling (line 2992: "Base branch was modified" → rebase).
- **Source**: user
