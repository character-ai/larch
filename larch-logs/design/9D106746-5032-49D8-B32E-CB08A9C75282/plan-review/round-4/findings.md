### FINDING_1:
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:33-37
- **Concern**: Plan updates arg-hint and duplicate-tier pins but does not add an absent guard for retired Step 0b tier-gate prose in SKILL.md. Scenario: Implementer can land default-SIMPLE pins and approval-gates absent Step 0 tier-gate while leaving skills/design/SKILL.md:268 AskUserQuestion tier gate and cancelled-tier-gate path; /design without --hard still prompts instead of defaulting
- **Proposed resolution**: Extend test-design-structure.sh edits with absent "$SKILL_MD" '**Tier gate**' (or equivalent) plus contains for **Tier resolution** / default-tier reason string

### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:354
- **Concern**: Final summary block When clause still names tier-flag mutual-exclusion abort. Scenario: After removing --simple and duplicate-tier mutual exclusion, implementers updating the SUMMARY_OUTCOME enum in the same section can leave this pre-DESIGN_TMPDIR skip label pointing at a retired exit path; disallowed-public-argv abort before Step 0 is the surviving equivalent
- **Proposed resolution**: Add a plan bullet under skills/design/SKILL.md Final summary block: replace tier-flag mutual-exclusion abort with disallowed public argv abort before Step 0 (no DESIGN_TMPDIR)
