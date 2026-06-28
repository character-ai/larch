### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/SKILL.md:67-74
- **Concern**: [SCOPE-REDUCTION] The SKILL.md removal list names Folded contract, Tradeoff, and pause/resume helper lines but not the Completion sentinels lead-in.. Scenario: Line 67 opens with **Completion sentinels for pause/resume.** and Phase 7 folds absorbed prior-step sentinel writes..., which duplicates the Phase 7 exception on line 61 and keeps always-loaded prose the issue targets for relocation.
- **Proposed resolution**: Explicitly remove the entire Completion sentinels subsection (heading plus lead-in through pause/resume helper coverage), not only the labeled subparagraphs; leave the single maintainer-only sentinel-host-table.md pointer.
