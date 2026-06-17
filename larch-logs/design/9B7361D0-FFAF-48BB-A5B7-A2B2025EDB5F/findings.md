### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/status/SKILL.md:29
- **Concern**: Item 4 distinguishes one-down vs both-down but status.sh emits only DEGRADED and per-vendor presence KVs not BOTH_DOWN. Scenario: Status SKILL rewrite can still emit one generic degraded sentence and fail Item 4
- **Proposed resolution**: Add an explicit render rule: when DEGRADED=true and both CODEX_PRESENT and CURSOR_PRESENT are false describe both-down hard-fail; when exactly one is false describe one-down operator confirmation; do not assume BOTH_DOWN is available from status.sh

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-sessionstart-health.sh:56-67
- **Concern**: Item 5 collect-results regression does not pin how the stub records LARCH_TOKEN_SESSION_ID for assertion. Scenario: Implementer may assert parent-shell env or hook stdout and ship a test that never exercises line 192 child env
- **Proposed resolution**: Require the resolve-implement-tmpdir stub to write LARCH_TOKEN_SESSION_ID to a dedicated temp file and assert that file is empty while the harness pre-exports a stale token outside env -i

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

### OOS_3:
- **Description**: [SCOPE-REDUCTION] Status degraded copy mentions only /implement while both-down hard-fail also applies to /design and /review. Scenario: Operators reading /status may think /design still falls back when both vendors are down
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/status/SKILL.md:29
- **Phase**: design

### OOS_4:
- **Description**: [SCOPE-REDUCTION] NEVER #5 bash-fallback carve-out for run-statistics ownership may be stale extra prose. Scenario: Extra bash-path wording can confuse operators about the active Python oos file writer
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:40
- **Phase**: design

### OOS_5:
- **Description**: [OUT_OF_SCOPE] Additional degraded-tools consumer docs still describe Claude-only fallback or auto-proceed behavior outside this six-item plan. Scenario: After the planned status SKILL edit lands, these docs can still tell operators that both-down has a Claude-only fallback or that one-down auto-proceeds, while the shared contract says one-down prompts and both-down hard-fails
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: correctness
- **Location**: docs/skills.md:179; docs/external-reviewers.md:10
- **Phase**: design
