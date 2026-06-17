### OOS_1:
- **Description**: [OUT_OF_SCOPE] The /status catalog entry keeps the same Claude-only fallback framing the plan removes from skills/status/SKILL.md. Scenario: After the planned status SKILL copy fix lands, docs/skills.md still tells users degraded status can mean reduced panel or Claude-only fallback, which conflicts with the both-down hard-fail contract
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/skills.md:173-179
- **Phase**: design

### OOS_2:
- **Description**: [OUT_OF_SCOPE] External reviewers documentation still describes the retired degraded-tools gate routing. Scenario: The shared gate contract requires Continue for one-down and hard-fails both-down, but this page says one-down auto-proceeds and both-down prompts
- **Reviewer**: Codex-Arch
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/external-reviewers.md:3-10
- **Phase**: design

### OOS_1:
- **Description**: [SCOPE-REDUCTION] Status degraded copy mentions only /implement while both-down hard-fail also applies to /design and /review. Scenario: Operators reading /status may think /design still falls back when both vendors are down
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/status/SKILL.md:29
- **Phase**: design

### OOS_2:
- **Description**: [SCOPE-REDUCTION] NEVER #5 bash-fallback carve-out for run-statistics ownership may be stale extra prose. Scenario: Extra bash-path wording can confuse operators about the active Python oos file writer
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40
- **Phase**: design

### OOS_1:
- **Description**: [OUT_OF_SCOPE] Additional degraded-tools consumer docs still describe Claude-only fallback or auto-proceed behavior outside this six-item plan. Scenario: After the planned status SKILL edit lands, these docs can still tell operators that both-down has a Claude-only fallback or that one-down auto-proceeds, while the shared contract says one-down prompts and both-down hard-fails
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/skills.md:179; docs/external-reviewers.md:10
- **Phase**: design

