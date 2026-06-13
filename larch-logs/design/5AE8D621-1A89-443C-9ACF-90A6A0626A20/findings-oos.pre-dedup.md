### OOS_1:
- **Description**: [OUT_OF_SCOPE] lint-retired-scripts table row still claims full-path-only matching with no bare-basename branch. Scenario: After the scoped `.claude/skills/**/*.md` basename check lands, operators following AGENTS.md into docs/linting.md will believe bare basenames are never flagged and may misdiagnose legitimate lint failures or skip the `# lint-ignore` escape hatch
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:174
- **Phase**: design

