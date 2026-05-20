## Goal
Create /larch:audit-runs skill and add audit-report label filter for /fix-issue

## Implementation Plan

Goal: Create /larch:audit-runs dev-only skill and add audit-report label exclusion to find-lock-issue.sh.

Files created:
- .claude/skills/audit-runs/SKILL.md
- .claude/skills/audit-runs/scans.tsv
- .claude/skills/audit-runs/scripts/test-audit-runs.sh
- .claude/skills/audit-runs/scripts/test-audit-runs.md

Files modified:
- skills/fix-issue/scripts/find-lock-issue.sh (add labels to --json, label check explicit + auto-pick)
- skills/fix-issue/scripts/find-lock-issue.md (doc update)
- skills/fix-issue/scripts/test-find-lock-issue.sh (fixtures 23 + 24)

All tests pass.

## Test plan
(no test plan section in plan-file)
