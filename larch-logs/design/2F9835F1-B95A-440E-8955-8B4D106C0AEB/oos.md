### OOS_1: [SCOPE-REDUCTION] --sweep still runs the full default -n 200 prefetch
- **Description**: [SCOPE-REDUCTION] --sweep still runs the full default -n 200 prefetch. Scenario: The issue targets cheap discovery over recent main merges, but the plan always runs Stage 0 prefetch before sweep work, rebuilding up to 200 bug bundles and triage batches even when the operator only wants merge sweeps. That doubles Task cost and blurs sweep vs legacy budgets in one run.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: .claude/skills/analyze-bugs/SKILL.md:Stage 0
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

