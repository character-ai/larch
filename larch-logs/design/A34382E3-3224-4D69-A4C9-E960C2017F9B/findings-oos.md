### OOS_1: Testing strategy omits `make test-render-cost-line-callsites` despite pre-edit inventory listing that harness
- **Description**: Testing strategy omits `make test-render-cost-line-callsites` despite pre-edit inventory listing that harness. Scenario: Approach tells implementers to inventory pins from `scripts/test-render-cost-line-callsites.sh`, but the Testing strategy and acceptance bullets never run it. Edits confined to the three named zones are unlikely to break Step 16-18 grep pins, and `/implement` relevant-checks pairs the harness with `skills/implement/SKILL.md`, so CI still catches regressions; local sign-off can nonetheless claim completeness after only the listed make targets.
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md
- **Phase**: design



