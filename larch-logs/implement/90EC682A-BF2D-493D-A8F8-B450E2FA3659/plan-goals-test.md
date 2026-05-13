## Goal
Replace fragile git pull with git fetch + reset --hard in local-cleanup.sh so pull failures don't leave local main stale.

## Goal
Replace the fragile `git pull origin main` in `scripts/local-cleanup.sh` with `git fetch origin main && git reset --hard origin/main` so pull failures never leave local main pointing at a stale SHA.

## Implementation Plan

**Files to modify**:
1. `scripts/local-cleanup.sh` — Step 3: replace `git pull origin main` with `git fetch origin main` + `git reset --hard origin/main`
2. `scripts/local-cleanup.md` — update contract to document new behaviour

**Approach**:
- Replace lines 76-81 (the git pull block) with: first `git fetch origin main` (non-fatal, continue on failure), then `git reset --hard origin/main` (fatal on failure, exits 0 with CLEANUP_SUCCESS=false). This eliminates the divergence scenario because reset --hard is unconditional.
- The `CLEANUP_SUCCESS` / `BRANCH_DELETED` output contract is unchanged.
- Update `local-cleanup.md` to document that the pull step now uses fetch+reset.

**Edge cases**:
- Reset failure: exits 0 with CLEANUP_SUCCESS=false, no regression vs. current pull-failure path.
- Fetch already done in Step 2: double-fetch is a cheap no-op.

## Test plan
- Run `/relevant-checks` after edit.
- Verify `grep -n 'git.*origin main' scripts/local-cleanup.sh` shows only fetch + reset, not pull.
