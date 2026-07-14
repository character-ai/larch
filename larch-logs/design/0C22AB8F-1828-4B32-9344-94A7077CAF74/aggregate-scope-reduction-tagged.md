### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/tests/implement/test_implement_shell_scripts.py
- **Concern**: [SCOPE-REDUCTION] Do not port Step 18 SKILL.md prose-pin grep assertions into pytest. Scenario: `test-step-18.sh:271-273` only grep `skills/implement/SKILL.md` for missing-marker and no-Read prose already pinned by `python/tests/skills/_structure_implement_specialized.py:422-424` and `scripts/test-render-cost-line-callsites.sh:69-70`. Porting them adds duplicate maintenance with no new behavioral coverage.
- **Proposed resolution**: Record in the Step 18 harness contract that those two grep assertions stay owned by structure/callsite pins; exclude them from the pytest parity matrix before deleting `test-step-18.sh`.
