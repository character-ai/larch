### OOS_1: [SCOPE-REDUCTION] A new `## Execution roots` section adds structure beyond the minimum needed for one entry
- **Description**: [SCOPE-REDUCTION] A new `## Execution roots` section adds structure beyond the minimum needed for one entry. Scenario: One extra top-level section increases doc surface and ordering constraints for a single guideline; `## CLI surface` already covers runtime entry and path resolution concerns
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: ARCHITECTURAL_GUIDELINES.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Doc-only G-Root-1 will not stop recurrence of the #4490 / #4509 / #6049 failure class by itself
- **Description**: Doc-only G-Root-1 will not stop recurrence of the #4490 / #4509 / #6049 failure class by itself. Scenario: Aspirational text that `architectural-guidelines read` further strips of Guidance is easy for agents to miss during /design and /implement; the cited bugs needed code-path fixes, not just documentation
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/core/architectural_guidelines.py:257-288
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

