## Goal
Fix PR title derivation in ship-pr.sh to skip larch-log flush commits

## Implementation Plan

### Objective
Fix `scripts/ship-pr.sh` so the PR title is derived from the feature commit, not the auto-generated larch-log flush commit that sits on top of it.

### Root Cause
`run_pr_create_phase` at line 607 uses `git log -1 --format=%s` which always reads HEAD — the larch-log flush commit added by `git-commit.sh`'s tail call to `larch-log-flush.sh`.

### Files to Modify
1. **`scripts/ship-pr.sh`** — line 607 in `run_pr_create_phase`
2. **`scripts/ship-pr.md`** — add invariant note about PR title derivation

### Change 1: scripts/ship-pr.sh

Replace (line 607):
```bash
title=$(git log -1 --format=%s 2>/dev/null || echo "Implement requested changes")
```

With:
```bash
title=$(git log --format=%s HEAD 2>/dev/null | grep -v '^chore(larch-logs): flush ' | head -1)
title=${title:-"Implement requested changes"}
```

Notes:
- `grep -v` uses BRE — parentheses in `chore(larch-logs)` are literal (no escaping needed)
- Pattern `^chore(larch-logs): flush ` exactly matches larch-log.sh's commit message template
- `head -1` picks the first non-flush commit subject
- `${title:-...}` fallback for the degenerate case where all commits are flush commits

### Change 2: scripts/ship-pr.md

Add to the Invariants section:
> `run_pr_create_phase` derives the PR title by scanning `git log --format=%s HEAD` and skipping subjects matching `^chore(larch-logs): flush ` (larch-log flush commits). The first non-matching subject becomes the title; fallback is `"Implement requested changes"` when all commits are flush commits.

### Edge Cases
- No commits beyond flush commits: falls back to "Implement requested changes"
- Existing PR resume (create-pr.sh idempotent path): no impact — title is re-derived on each `run_pr_create_phase` call but create-pr.sh handles existing PRs gracefully


## Test plan
1. Run `make lint` / `/relevant-checks` to verify no harness regressions
2. Inspect git log in a PR branch to confirm the pattern works
