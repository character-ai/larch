# scripts/git-rebase-skip.sh — contract

`scripts/git-rebase-skip.sh` wraps `git rebase --skip`. Used inside `/implement`'s Rebase + Re-bump Sub-procedure Phase 4 Exit-3 path when a rebased commit has nothing new to apply against the new base (e.g., the upstream commit already contains the same change). Distinct from `scripts/git-rebase-abort.sh` (which terminates the entire rebase): `--skip` advances to the next commit in the in-progress rebase.
