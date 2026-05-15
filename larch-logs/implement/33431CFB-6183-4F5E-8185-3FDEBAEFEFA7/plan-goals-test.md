## Goal
Add bold /clear reminder at end of /fix-issue and /implement (standalone only)

## Implementation Plan

Goal: Add a bold /clear reminder as the very last output line of /fix-issue and /implement (standalone only).

### Changes

1. skills/fix-issue/SKILL.md
   - At the end of Step 8 (line 336), after the "Otherwise … skipped (no temp dir created)" sentence, add a blank line then:
     After cleanup (or after the skip-note on the no-tmpdir path), print: `**💡 Run /clear before starting your next task to reduce context bloat and save costs.**`

2. skills/implement/SKILL.md
   - At the very end of the file (after line 2016, the final explanatory paragraph about Step 18 — done), add a blank line then:
     If `SESSION_ENV_PATH` is empty (standalone invocation — not called from `/fix-issue` or another orchestrating skill), print as the very last output line: `**💡 Run /clear before starting your next task to reduce context bloat and save costs.**`

### Detection for /implement
SESSION_ENV_PATH is set by --session-env <path>. Per the flag docs: "Empty = standalone invocation (full discovery)."
When /fix-issue calls /implement, it passes --session-env $FIX_ISSUE_TMPDIR/session-env.sh, so SESSION_ENV_PATH is non-empty.
When called standalone by the user, SESSION_ENV_PATH is empty.


## Test plan
Run /relevant-checks after edits to confirm markdownlint passes.
