# scripts/git-rebase-abort.sh — contract

`scripts/git-rebase-abort.sh` wraps `git rebase --abort` and is idempotent — safe to call when no rebase is in progress (the underlying `git` reports "No rebase in progress" and exits 0). Used by `/implement`'s Conflict Resolution Procedure on the abort path (Phase 2 user-decline, Phase 3 reviewer-rejection, Phase 4 hard failure) and by Step 12d's bail tail. Idempotency is load-bearing because the bail path may run when the rebase has already been aborted by a prior step in the same control flow.
