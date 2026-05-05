# scripts/git-current-branch.sh — contract

`scripts/git-current-branch.sh` prints the current branch name as `BRANCH=<name>`. Wraps `git symbolic-ref --short HEAD` so skill orchestrators invoke a pre-approved script instead of a raw `git` call (avoids per-invocation permission prompts). Used by `/implement` Step 1 to capture `BRANCH_NAME` after `/design` returns, by Step 4 / 14 / 18 status messages, and anywhere a skill needs to confirm or report the current branch. For HEAD SHA + branch in one call, use `scripts/git-branch-info.sh`.
