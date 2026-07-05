# Review Round 1

- Mode: `diff`
- 1 accepted, 5 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing branch/repo guard before pre-fix rebase
- **Reviewer(s)**: codex-specialist-testing, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `ship_pre_fix_rebase_main` can rebase and force-push the wrong branch or repository because it does not verify the checked-out branch and repo root against `ship-pr-state.sh` before calling `rebase_and_push`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Compare the current branch and repo root against BRANCH_NAME and REPO from ship-pr-state.sh before rebasing, and fail closed with no NEXT_ACTION if either mismatches.
  - From cursor-specialist-edge-cases: Compare git.try_current_branch() to state BRANCH_NAME; refuse main/master when not forked; stall or fail closed


