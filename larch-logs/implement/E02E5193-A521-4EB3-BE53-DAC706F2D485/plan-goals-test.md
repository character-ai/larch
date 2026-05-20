## Goal
Fix PR title to use oldest branch commit with issue number prefix

## Implementation Plan

Fix PR title generation in `scripts/ship-pr.sh::run_pr_create_phase()` to use the oldest (first) branch commit instead of the newest (version bump), and prefix the title with `Fixes #N: ` when `ISSUE_NUMBER` is in state.

### Files to modify

1. **`scripts/ship-pr.sh`** — `run_pr_create_phase()` function (around line 941):
   - Add `issue_num` to the `local` declaration
   - Change `head -1` to `tail -1` in both title derivation branches (lines 946 and 948)
   - After `title=${title:-"Implement requested changes"}`, add:
     ```bash
     issue_num=$(read_state ISSUE_NUMBER)
     [ -n "$issue_num" ] && title="Fixes #${issue_num}: ${title}"
     ```

2. **`scripts/ship-pr.md`** — Invariants section (line 70):
   - Change "The **first** non-matching subject becomes the title" to 
     "The **oldest** non-matching subject becomes the title; when `ISSUE_NUMBER` is set in state, the title is prefixed with `Fixes #N:` followed by a space."

3. **`scripts/test-ship-pr.sh`** — Add test after the pr-create log-commit-failure test (after `rm -rf "$sentinel_dir"` near line 883):
   - Make a repo with 3 commits: "initial" (from make_repo), "chore(larch-logs): flush test-run", "Bump version to 1.0.1"
   - Start from `pr-create` phase with ISSUE_NUMBER=7 (default write_state)
   - Assert `PR_TITLE=Fixes #7: initial` in state (proves oldest commit is chosen and issue prefix added)

### Testing strategy
Run `make test-ship-pr-postmerge` to verify the new test passes. The existing `PR_TITLE=Title` tests are from the stubbed `create-pr.sh` return value (not the computed `$title`), so they remain unaffected.

## Test plan
(no test plan section in plan-file)
