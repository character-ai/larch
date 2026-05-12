## Goal
Fix run_teardown() in scripts/implement-finalize.sh to push the larch-log flush commit when PR_CLOSED=true (merged), preventing local main from being left ahead of origin/main after --merge runs.

## Test plan
- Run /relevant-checks after the change
- Verify git status shows no [ahead 1] after a --merge run
