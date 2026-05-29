Verifying the cited locations to normalize findings and confirm they should stay separate.
### FINDING_1: Structural test gap for retired Step 0b tier-gate prose
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Plan updates pin arg-hint and duplicate-tier rejection in `scripts/test-design-structure.sh` but do not add an absent guard for retired Step 0b tier-gate prose in `skills/design/SKILL.md`. An implementer can land default-SIMPLE pins and approval-gates that omit Step 0 tier-gating while `skills/design/SKILL.md` still documents the AskUserQuestion tier gate and `cancelled-tier-gate` path (e.g. around line 268), so `/design` without `--hard` may still prompt instead of defaulting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Extend test-design-structure.sh edits with absent "$SKILL_MD" '**Tier gate**' (or equivalent) plus contains for **Tier resolution** / default-tier reason string

### FINDING_2: Final summary block references retired tier-flag mutual-exclusion abort
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Concern**: The Final summary block “When” clause at `skills/design/SKILL.md:354` still names a tier-flag mutual-exclusion abort. After removing `--simple` and duplicate-tier mutual exclusion, implementers updating the `SUMMARY_OUTCOME` enum in the same section can leave this pre-`DESIGN_TMPDIR` skip label pointing at a retired exit path; the surviving equivalent is disallowed-public-argv abort before Step 0 (no `DESIGN_TMPDIR`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a plan bullet under skills/design/SKILL.md Final summary block: replace tier-flag mutual-exclusion abort with disallowed public argv abort before Step 0 (no DESIGN_TMPDIR)
