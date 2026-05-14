## Goal
Fix false STALL_TRACKING in ship-pr.sh when version_already_published after PR already merged

## Implementation Plan

Fix two independent gaps in ship-pr.sh / git-force-push.sh that cause a false
STALL_TRACKING=true when version_already_published is returned after a PR is
already squash-merged.

### Gap 1 — merged-PR check before re-bump (scripts/ship-pr.sh)

**Location**: `version_already_published` case in `run_ci_phase()`, ~line 958-961.

**Change**: Before calling `run_rebase_rebump`, query `gh pr view` to check
whether the PR is already MERGED. If MERGED, treat it as `already_merged`
(advance to postmerge without re-bumping). If not MERGED (or query fails),
fall through to the existing `run_rebase_rebump` call.

```bash
version_already_published)
    pr_state=$(gh pr view "$(read_state PR_NUMBER)" --repo "$(read_state REPO)" \
        --json state --jq '.state' 2>/dev/null || true)
    if [[ "$pr_state" == "MERGED" ]]; then
        state_set_many PR_CLOSED true MERGE_RESULT already_merged
        rename_done_best_effort
        advance_phase postmerge
    else
        run_rebase_rebump "$phase"
    fi
    return 0
    ;;
```

**Edge cases**:
- `gh pr view` failure (network, missing PR_NUMBER) → fall back to
  `run_rebase_rebump` (safe: existing behavior)
- PR_NUMBER empty → same fallback
- state != MERGED (OPEN, CLOSED) → fall back to `run_rebase_rebump` (correct)

### Gap 2 — pre-push fetch in git-force-push.sh (scripts/git-force-push.sh)

**Location**: before the first `git push --force-with-lease` in git-force-push.sh.

**Change**: Add `git fetch origin "$BRANCH" 2>/dev/null || true` immediately
before the first push attempt so the local tracking ref is fresh and the
lease check passes.

The existing post-failure fetch + compare + retry logic remains intact as
defense-in-depth.

**Affected files**:
1. `scripts/ship-pr.sh` — version_already_published handler in run_ci_phase()
2. `scripts/git-force-push.sh` — add pre-push fetch before first push
3. `scripts/git-force-push.md` — update header comment to reflect pre-push fetch
4. `scripts/ship-pr.md` — update if it describes the version_already_published path (check first)


## Test plan
- `pre-commit` hooks (markdownlint, shellcheck, agent-lint)
- Verify the gap-1 change does not break the no-PR-number path
- Verify git-force-push.sh still exits with same STATUS codes
