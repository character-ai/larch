## Goal
Export IMPLEMENT_TMPDIR in ship-pr.sh and implement-finalize.sh so larch-log.sh commit correctly locates batch files in the session tmpdir regardless of whether the caller shell inherited the variable.

## Plan
$(cat <TMPDIR>/design-export/plan.txt)

## Test plan
After implementing: run /relevant-checks to verify pre-commit passes and test-ship-pr.sh / test-implement-finalize.sh pass.
