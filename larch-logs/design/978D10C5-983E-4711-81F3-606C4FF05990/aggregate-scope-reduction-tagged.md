### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/design-outline.md:21-89
- **Concern**: [SCOPE-REDUCTION] Plan mandates unconditional tightening of Entry guard, Inputs, and Architectural guideline presentation though issue scope limits density work to Approve/Refine/Cancel prompt and Refine-loop prose. Scenario: Issue scope targets only Approval prompt, Refine loop, and Cancel hygiene (~696 est. tokens). The ~382-token / 15% file gate needs ~55% compression in those sections, which is achievable without editing high-branch resume routing or `present-note` branching. Files to modify still requires tightening Entry guard and guideline presentation unconditionally, inviting semantic drift on paths the issue marked density-only and out of scope for semantics change
- **Proposed resolution**: Reframe the Files section: compress Approval prompt, Refine loop, and Cancel hygiene first; touch Entry guard, Inputs, guideline presentation, downstream docs, and invariants only if the per-file `est_tokens` gate still fails after safe issue-scoped compression
