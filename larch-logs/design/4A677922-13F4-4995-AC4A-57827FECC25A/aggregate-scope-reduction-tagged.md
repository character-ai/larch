### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-prompt files remain firm UPDATED. Scenario: `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` are `### UPDATED:` while their bullets say "only if" wording conflicts. That turns optional prompt churn into mandatory diff surface.
- **Proposed resolution**: Move both to `### MAY_UPDATE:` or drop them from the firm file list; keep the required gate-5 edits in `skills/shared/review-acceptance-rubric.md` and `skills/shared/reviewer-templates.md` plus `make test-prompt-template-invariants`.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md;skills/shared/oos-acceptance-rubric.md
- **Concern**: [SCOPE-REDUCTION] Conditional shared-rubric files remain firm `### UPDATED:` entries. Scenario: Both files say update only when wording conflicts, but `### UPDATED:` still makes them mandatory diff targets and triggers the six-agent regen sweep even when gate-5 text is unchanged.
- **Proposed resolution**: Reclassify `skills/shared/voting-protocol.md` and `skills/shared/oos-acceptance-rubric.md` as `### MAY_UPDATE:`; run agent regen only when those files actually change.

### FINDING_18:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/shared/voting-protocol.md
- **Concern**: [SCOPE-REDUCTION] Conditional reviewer prompt files listed as firm `### UPDATED:`. Scenario: Bullets say update `voting-protocol.md` and `oos-acceptance-rubric.md` only when wording conflicts, but firm `### UPDATED:` makes optional prompt churn mandatory (~6 agent regens).
- **Proposed resolution**: Reclassify those two paths as `### MAY_UPDATE:`; keep `review-acceptance-rubric.md` and generated agent regen as the firm doctrine surface.
