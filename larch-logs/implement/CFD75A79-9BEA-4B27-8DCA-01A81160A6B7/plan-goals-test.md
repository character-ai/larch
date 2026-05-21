## Goal
Make /audit-runs verbal description optional, defaulting empty to 'since last audit'

## Implementation Plan

Objective: Make <verbal-description> optional in /audit-runs skill.
When empty, route to the existing "since last audit" behavior instead of failing.

### Files to modify

1. .claude/skills/audit-runs/SKILL.md
   - Line 28: change "Default when empty: fail with usage error"
     to "Default when empty: treat as 'since last audit' (requires a prior
     audit-report issue; continues to error if no prior report or malformed
     frontmatter — same as the explicit 'since last audit' form)"

2. .claude/skills/audit-runs/scripts/test-audit-runs.sh
   - Test 5: rename label, update check_empty() to emit "since_last_audit"
     for empty input, update assertion from "usage_error" to "since_last_audit"

### Testing strategy
- Run: bash .claude/skills/audit-runs/scripts/test-audit-runs.sh
- Run relevant-checks (pre-commit + agent-lint)

## Test plan
(no test plan section in plan-file)
