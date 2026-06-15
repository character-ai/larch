### OOS_1:
- **Description**: [OUT_OF_SCOPE] NEVER #5 still says run-statistics is owned by the post-checkpoint Step 8+ block after disposition-checkpoint, but the plan moves that gate inside python/cli.py oos file on the Python path. Scenario: Operators reading implement SKILL after Item 8 land may believe run-statistics still comes only from Step 8+ even though oos file will write it post-internal-checkpoint
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4454
### OOS_2:
- **Description**: [OUT_OF_SCOPE] Item 9 updates docs/configuration-and-permissions.md but not larch's canonical .claude/settings.json Skill allowlist. Scenario: Contributors running strict permissions in this repo still lack Skill(bug) / Skill(larch:bug) even after /bug is consumer-facing
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: .claude/settings.json:151
- **Phase**: design

### OOS_1:
- **Description**: New collect harness omits agent collect-results failure logging regression. Scenario: Collect RC non-zero append-failure path could regress without CI signal
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-step1d5.sh:237-243
- **Phase**: design

