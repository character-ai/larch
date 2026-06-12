### OOS_1:
- **Description**: prose-audit re-fetches issue bodies already present in open-issues-file. Scenario: Redundant gh API reads on large open-issue sets; slower runs but functionally correct
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/combine_issues.py:163-195
- **Phase**: design

### OOS_2:
- **Description**: Blocks #N parsing planned only inside prose_audit_main not blocker.parse_prose_blockers. Scenario: Duplicate prose dependency regex diverges from blocker.py _KEYWORD_RE over time
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/combine_issues.py:174-175
- **Phase**: design

