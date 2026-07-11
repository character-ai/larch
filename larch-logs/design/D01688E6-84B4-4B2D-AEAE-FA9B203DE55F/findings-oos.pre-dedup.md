### OOS_1: Docs-sync harness does not forbid Cursor auto phrasing
- **Description**: Docs-sync harness does not forbid Cursor auto phrasing. Scenario: After SKILL.md and public docs switch to Composer 2.5, stale Cursor auto text in README.md, docs/review-agents.md, docs/workflow-lifecycle.md, or docs/skills.md would not fail `make test-quick-mode-docs-sync` because STALE_PHRASES omits cursor-auto variants. Acceptance rg can also miss per-slot auto without a nearby cursor token.
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/test-quick-mode-docs-sync.sh:96-120
- **Phase**: design



