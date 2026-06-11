### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:216
- **Concern**: [SCOPE-REDUCTION] Preflight item 6 bounded probe lacks a mechanical path list contract. Scenario: The plan replaces open-ended reads with one batched Bash probe over plan-cited paths but never defines how to derive those paths from $PREFLIGHT_TMPDIR/plan-from-issue.txt. An orchestrator can satisfy the prose with a hand-picked test -f list, reintroduce a Read/grep preamble before Bash, or under-probe arbitrary issues.
- **Proposed resolution**: Spell out extraction inside the single Bash block: scrape ### NEW:/UPDATED:/REWRITTEN: headings from plan-from-issue.txt into a NUL path list, then run test -f and targeted rg only on that list; forbid any Read/grep tool calls before or after the block.
