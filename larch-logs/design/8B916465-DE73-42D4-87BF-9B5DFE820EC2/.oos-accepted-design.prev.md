### OOS_1:
- **Description**: `skills/implement/SKILL.md` edits only trigger `test-check-contains-pins`, not `test-implement-structure` or `test-render-cost-line-callsites` (unlike `skills/design/SKILL.md` → `test-design-structure`). Scenario: Operators relying only on `relevant-checks.sh` after implement SKILL edits may miss new structure pins until full harness CI
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/relevant-checks.sh:151-298
- **Phase**: design

