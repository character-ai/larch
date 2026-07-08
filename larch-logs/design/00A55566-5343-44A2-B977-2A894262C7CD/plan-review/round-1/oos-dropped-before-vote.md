### OOS_3: Design anti-halt still lists summary among mid-turn halt surfaces without a terminal carve-out
- **Description**: Design anti-halt still lists summary among mid-turn halt surfaces without a terminal carve-out. Scenario: Anti-halt through Step 6 forbids ending on summary mid-pipeline. After the fix the skill legitimately ends on deferred summary text; wording is slightly stale but Step 6-then-emit ordering is clear enough from Step 5c/5d edits
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:25
- **Phase**: design

### OOS_4: Emoji stalled bullets need explicit reconciliation test coverage
- **Description**: Emoji stalled bullets need explicit reconciliation test coverage. Scenario: Plan updates _summary_stalled_outcome_index for ❌ STALLED but does not list a dedicated test for emoji-prefixed stalled outcomes; residue guards could miss the new shape
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: correctness
- **Location**: python/larch/report/final_report.py:572-576
- **Phase**: design

