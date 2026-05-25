### OOS_1:
- **Description**: Decompose filing plan uses only --input-file and --intra-batch-deps-file and never --blocked-by-issue. Scenario: New partition issues are not automatically linked as blocked by the original tracking issue unless filed manually
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/issue/SKILL.md:44-45
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_2:
- **Description**: Testing strategy calls out harness anchor updates but the formal file list omits this script. Scenario: Implementer may ship SKILL/reference changes without refreshing structure assertions
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/test-design-structure.sh (not listed in plan `### UPDATED`)
- **Phase**: design


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

