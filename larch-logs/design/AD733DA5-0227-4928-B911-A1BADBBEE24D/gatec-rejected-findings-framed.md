---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:assessments branch
- **Concern**: [SCOPE-REDUCTION] Parent MANDATORY READ line says read both present-reference files when a kind is listed. Scenario: The sub-bullets load refs only when DETAIL contains invariants or guidelines, but the parent line can be read as always loading both refs on any single-kind pause, reintroducing rejected dual-read scope creep
- **Proposed resolution**: Reword the assessments branch to: read each present-reference file whose kind appears in DETAIL (load architectural-invariants-present.md only for invariants; load architectural-guidelines-present.md only for guidelines); keep the harness pin that both refs are read only when both kinds are listed


---LARCH-REJECTED-END---
