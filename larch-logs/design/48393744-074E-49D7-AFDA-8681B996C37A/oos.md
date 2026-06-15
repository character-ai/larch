### OOS_1:
- **Description**: Post-invocation verification prose still calls the sentinel gate "/research-specific". Scenario: After /bug lands, maintainers may think only /research should verify issue-completed.sentinel
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/shared/subskill-invocation.md:70-76
- **Phase**: design


Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

### OOS_2:
- **Description**: [SCOPE-REDUCTION] Write tool plus deny-edit-write hook may be unnecessary. Scenario: Research composes issue bodies with Bash heredocs; adding Write and a PreToolUse hook increases surface without a stated requirement
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: skills/bug/SKILL.md:49-50
- **Phase**: design

Vote tally: YES=0 NO=2 JUDGE_ERROR=0 Result=rejected

