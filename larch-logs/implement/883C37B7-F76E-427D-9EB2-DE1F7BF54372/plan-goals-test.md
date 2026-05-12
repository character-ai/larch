## Goal
Fix the broken `write-session-env.sh` invocation in `skills/fix-issue/SKILL.md` Step 1 by adding the required `--repo` and `--repo-unavailable` arguments.

## Implementation Plan
Single-file fix: update lines 109-111 of `skills/fix-issue/SKILL.md` to add `--repo "$REPO"` and `--repo-unavailable "$REPO_UNAVAILABLE"` to the `write-session-env.sh` call in Step 1.

## Test plan
Run `/relevant-checks` (pre-commit + agent-lint) to validate the SKILL.md change.
