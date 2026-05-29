### FINDING_1: Gate C `Other` still references removed Step 0 tier-gate cancel path
- **Reviewer(s)**: unknown-slot, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-default-promotion-drift
- **Severity**: important
- **Concern**: Plan updates cross-tier and per-tier argv wording in `approval-gates.md` (e.g. around lines 13 and 43) but leaves the Gate C paragraph at line 191 that contrasts Gate C `Other` with Step 0 tier-gate `Other` as a terminal cancel. After tier-gate removal, that contrast documents a Step 0 cancel path that no longer exists, contradicting `SKILL.md` and misleading operators about Gate C `Other` (re-prompt / full-plan display only; never cancels `/design`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: In the same Gate C Other edit, delete or rewrite the Step 0 tier-gate Other contrast (e.g. state only that Gate C Other never cancels /design)
  - From Cursor-Innovation, Cursor-Requirements, Cursor-dyn-default-promotion-drift: Merge into approval-gates.md edits: drop or rewrite the Step 0 tier-gate `Other` clause (e.g. state only that Gate C `Other` re-prompts and never cancels)

