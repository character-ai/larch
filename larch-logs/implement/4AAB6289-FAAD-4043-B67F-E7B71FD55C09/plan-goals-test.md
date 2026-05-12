## Goal
Fix two bugs in scripts/ship-pr.sh: internalize ACTION=rebase handling and prevent false stall when vendor CI-fix agent self-commits.

## Implementation Plan
See design-export/plan.txt

## Test plan
- Run /relevant-checks after implementation
- Verify rebase case changes handle return 0 correctly  
- Check timing-task-kind allowlist for new vendor call
- Verify git diff check works for both staged and unstaged changes
