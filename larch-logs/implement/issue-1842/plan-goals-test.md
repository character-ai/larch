## Goal
Gate git-log from reviewer prompts for ≤5-commit diffs, cap CI failure logs to 100 lines.

## Implementation Plan

**Task A** — gate `git log` in `render-specialist-prompt.sh` preambles behind `--commit-count N` (omit when N ≤ 5). Add `COMMIT_COUNT` to `gather-branch-context.sh` output; thread through `launch-review.sh` and SKILL.md callers.

**Task B** — cap `gh-run-logs.sh` output to last 100 lines; prepend pointer to full artifact.

## Test plan
- `bash scripts/test-render-specialist-prompt.sh` — add tests for `--commit-count` gating
- `/relevant-checks` — pre-commit + agent-lint
