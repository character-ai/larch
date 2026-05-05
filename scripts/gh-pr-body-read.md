# scripts/gh-pr-body-read.sh — contract

`scripts/gh-pr-body-read.sh` wraps `gh pr view --json body` and writes the body to a caller-specified file rather than stdout. File-output is required because PR bodies can contain arbitrary text — including `KEY=value`-shaped lines — that would collide with the repo-wide `KEY=value` stdout-parsing convention. Stdout emits only `BODY_FILE=<path>`. Primary caller: `scripts/extract-closes-issue-from-pr.sh` (used by `/implement` Step 0.5 Branch 3 PR-body recovery).
