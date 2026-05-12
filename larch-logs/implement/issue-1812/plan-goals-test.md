## Goal
Scaffold new plugin skill `/report-tokens` that analyzes token costs across all closed GitHub issues in the larch repo: fetches all issues with structured token-report data, computes per-issue dollar cost (Claude/Cursor/Codex), classifies each issue as SIMPLE or HARD workflow, plots cost over time for each workflow (two separate charts), and produces a written analysis.

## Implementation Plan

**Files:** `skills/report-tokens/SKILL.md` (scaffold + body), `skills/report-tokens/scripts/run-analysis.sh` (master coordinator — gh pagination + Python plotting), `skills/report-tokens/scripts/run-analysis.md` (sibling contract), plus post-scaffold hint updates in README.md, `.claude/settings.json`, `docs/workflow-lifecycle.md`, `docs/configuration-and-permissions.md`.

`run-analysis.sh` uses `gh api` to search all closed issues for `token-report-begin`, parses Claude (6-col and 4-col formats), Codex, and Cursor grand totals via awk/python, extracts `**Workflow path**` and `closedAt`, then invokes Python to compute dollar costs, generate two PNG plots, open them via `open`, and print the written analysis.

## Test plan
- Run `/relevant-checks` (pre-commit + agent-lint)
- Verify `skills/report-tokens/SKILL.md` exists with valid frontmatter
- Verify `run-analysis.sh` is executable with sibling `.md`
