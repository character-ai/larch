# scripts/gh-pr-body-update.sh — contract

`scripts/gh-pr-body-update.sh` wraps `gh pr edit --body-file` and emits `UPDATED=true|false` plus an `ERROR=<msg>` line on failure. `--body-file` (not inline `--body`) is required so large PR bodies do not hit shell argument-length limits. Primary caller: `/implement` Step 9b post-create body-update path when `create-pr.sh` returned `PR_STATUS=existing`.

Interface:

```
gh-pr-body-update.sh --pr <number> --body-file <path> [--repo OWNER/REPO]
```

`--repo OWNER/REPO` is optional and is threaded to `gh pr edit`. `/implement --forked` passes the fork repository so body updates target the fork PR.

Harness: `scripts/test-gh-pr-body-update.sh`.
