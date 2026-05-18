## Goal
Drop diff bundling from Claude voter context; add --role flag to launch-claude-review.sh

## Implementation Plan

Objective: Drop diff/plan bundling from voter calls in dispatch-code-voters.sh. Also add --role reviewer|voter to launch-claude-review.sh (secondary fix, user-requested).

Files to modify:
1. scripts/dispatch-code-voters.sh — remove lines 124-125 (ctx_args building from DIFF_FILE/PLAN_FILE); always use mode="description" and empty ctx_args
2. scripts/dispatch-code-voters.md — update --diff-file/--plan-file descriptions; add voter-role context shape note
3. scripts/launch-claude-review.sh — add --role reviewer|voter flag (default reviewer); gate diff/plan/feature/scope context-file appends on role=reviewer; voter path skips all context appends
4. scripts/launch-claude-review.md — document --role flag
5. scripts/test-dispatch-code-voters.sh — update symlink test (voter now succeeds with symlink diff since it's no longer forwarded); add 2MB-diff test
6. Verify test-launch-review.sh coverage for --role

Testing: scripts/test-dispatch-code-voters.sh + scripts/test-launch-review.sh + /relevant-checks

## Test plan
(no test plan section in plan-file)
