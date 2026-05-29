### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:191
- **Concern**: Plan updates cross-tier and per-tier argv prose but leaves the Gate C paragraph that contrasts Gate C Other with Step 0 tier-gate Other. Scenario: After tier-gate removal, approval-gates still documents a terminal Step 0 tier-gate cancel path that no longer exists, contradicting SKILL and confusing Gate C Other handling
- **Proposed resolution**: In the same Gate C Other edit, delete or rewrite the Step 0 tier-gate Other contrast (e.g. state only that Gate C Other never cancels /design)

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation, unknown-slot, Cursor-Requirements, Cursor-dyn-default-promotion-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:191
- **Concern**: Gate C `Other` prose still contrasts with removed Step 0 tier-gate. Scenario: Plan updates cross-tier argv wording at :13 and :43 but not the Gate C paragraph; operators see a cancel path that no longer exists
- **Proposed resolution**: Merge into approval-gates.md edits: drop or rewrite the Step 0 tier-gate `Other` clause (e.g. state only that Gate C `Other` re-prompts and never cancels)
