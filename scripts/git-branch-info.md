# scripts/git-branch-info.sh — contract

`scripts/git-branch-info.sh` returns the current short HEAD SHA and branch name as `KEY=value` lines (`HEAD_SHA=<short>`, `BRANCH=<name>`). Wraps `git rev-parse --short HEAD` + `git branch --show-current` into a single call so skill orchestrators invoke a pre-approved script rather than two raw `git` commands (avoids per-invocation permission prompts in Claude Code sessions). For just the branch name, use `scripts/git-current-branch.sh`.
