### [Plan Review] FINDING_1

### FINDING_1: Structural test gap for retired Step 0b tier-gate prose
- **Reviewer(s)**: unknown-slot
- **Severity**: important
- **Concern**: Plan updates pin arg-hint and duplicate-tier rejection in `scripts/test-design-structure.sh` but do not add an absent guard for retired Step 0b tier-gate prose in `skills/design/SKILL.md`. An implementer can land default-SIMPLE pins and approval-gates that omit Step 0 tier-gating while `skills/design/SKILL.md` still documents the AskUserQuestion tier gate and `cancelled-tier-gate` path (e.g. around line 268), so `/design` without `--hard` may still prompt instead of defaulting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From unknown-slot: Extend test-design-structure.sh edits with absent "$SKILL_MD" '**Tier gate**' (or equivalent) plus contains for **Tier resolution** / default-tier reason string


