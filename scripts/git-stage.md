# scripts/git-stage.sh — contract

`scripts/git-stage.sh` wraps `git add -- <files>` (stage only, no commit). Used by `/implement`'s Conflict Resolution Procedure to stage resolved files before continuing the rebase via `scripts/rebase-push.sh --continue`. Distinct from `scripts/git-commit.sh` (stage + commit) and `scripts/git-amend-add.sh` (stage + amend).
