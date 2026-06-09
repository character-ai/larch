### FINDING_1:
- **Reviewer(s)**: Cursor-dyn-voter-caller-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:283-300; staged-context/scope-files.txt:10-12
- **Concern**: [SCOPE-REDUCTION] Plan and scope-files target scripts/emit-design-plan-preview.sh and bare emit-design-plan-preview.sh but the canonical script is skills/design/scripts/emit-design-plan-preview.sh. Scenario: Implementer edits or creates wrong paths; preview changes for fresh plan-summary.md never land on the script SKILL.md and run-step3-review.sh already call
- **Proposed resolution**: Rename plan entries and scope-files lines to skills/design/scripts/emit-design-plan-preview.sh .md and skills/design/scripts/test-emit-design-plan-preview.sh; remove stale scripts/ and bare duplicates
