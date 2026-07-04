### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: plan.txt:32-34
- **Concern**: [SCOPE-REDUCTION] `scripts/test-design-structure.sh` is listed as a firm update even though the plan keeps the pinned mandatory-read banner byte-stable, and the current harness does not pin the warning prints slated for restyling.. Scenario: The implementer may make an unnecessary harness edit solely to satisfy the firm `### UPDATED:` commitment, which expands a prose-only cleanup beyond the needed diff.
- **Proposed resolution**: Change this entry to `### MAY_UPDATE: scripts/test-design-structure.sh`, or remove it from firm files and keep the existing instruction to run `make test-design-structure` and update only if a changed assertion is actually found.

