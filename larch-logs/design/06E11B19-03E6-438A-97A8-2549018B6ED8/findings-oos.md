### OOS_1:
- **Description**: [OUT_OF_SCOPE] FINDING_4: Public docs will still describe brainstorm as running before Gate A. Scenario: The proposed runtime change inserts Step 1d.7 after brainstorm and removes first-time Gate A, but adjacent public and flag docs still say brainstorm runs before Gate A. This is not core execution, but it leaves consumer-facing workflow docs stale.
- **Reviewer**: Codex-Arch
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: README.md:61; docs/skills.md:54; skills/design/references/flags.md:21
- **Phase**: design

### OOS_2:
- **Description**: 4. [OUT_OF_SCOPE] Consumer docs still describe --brainstorm as running before Gate A, with no outline gate mention. Scenario: After the PR lands, docs will point users at the old Gate A flow and omit the new approval checkpoint
- **Reviewer**: Codex-Edge
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: README.md:59-61; docs/skills.md:50-54
- **Phase**: design

