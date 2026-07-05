### [Plan Review] FINDING_3

### FINDING_3: AGENTS.md non-empty probe rule remains unconditional
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned `AGENTS.md` probe-rule update does not qualify the leading non-empty probe condition, so Tier-1 readers can still foreground-probe every non-empty premature notification before the repeat silent-yield carve-out applies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Qualify the AGENTS.md non-empty premature-notification sentence to first or changed non-empty output only, and state evaluation order: empty output silent yield; prefix-identical repeat (first 200 chars) with absent terminal sentinel silent yield; otherwise one foreground probe against the active wait terminal sentinel.


