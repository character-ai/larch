### OOS_1:
- **Description**: [OUT_OF_SCOPE] The /status catalog entry keeps the same Claude-only fallback framing the plan removes from skills/status/SKILL.md. Scenario: After the planned status SKILL copy fix lands, docs/skills.md still tells users degraded status can mean reduced panel or Claude-only fallback, which conflicts with the both-down hard-fail contract
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/skills.md:173-179
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4598
### OOS_2:
- **Description**: [OUT_OF_SCOPE] External reviewers documentation still describes the retired degraded-tools gate routing. Scenario: The shared gate contract requires Continue for one-down and hard-fails both-down, but this page says one-down auto-proceeds and both-down prompts
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/external-reviewers.md:3-10
- **Phase**: design

