# scripts/gh-pr-body-update.sh — contract

`scripts/gh-pr-body-update.sh` wraps `gh pr edit --body-file` and emits `UPDATED=true|false` plus an `ERROR=<msg>` line on failure. `--body-file` (not inline `--body`) is required so large PR bodies do not hit shell argument-length limits. Primary caller: `/implement` Step 9b post-create body-update path when `create-pr.sh` returned `PR_STATUS=existing`. The script always exits 0 — callers branch on `UPDATED`.
