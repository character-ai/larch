### OOS_4: PostToolUse anti-read-poll still warns on repeated tasks/*.output reads
- **Description**: PostToolUse anti-read-poll still warns on repeated tasks/*.output reads. Scenario: PostToolUse reminders may still fire on the two allowed classification Reads during a live wait, adding noise unrelated to the loop fix
- **Reviewer**: Cursor-Pragmatic
- **Severity**: nit
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.sh:6-8
- **Phase**: design

### OOS_6: Task-output signature checksum algorithm is unspecified
- **Description**: Task-output signature checksum algorithm is unspecified. Scenario: Implementers may pick incompatible checksums and weaken the repeated-content test harness
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/hook-bg-poll-guard.sh / plan Read-clamp bullets
- **Phase**: design

### OOS_7: AGENTS.md silent-yield line still says no further prose tools but not explicit zero chat output
- **Description**: AGENTS.md silent-yield line still says no further prose tools but not explicit zero chat output. Scenario: The prose leak from the bug ("Silent yield — still empty. Waiting.") is only fully forbidden in SKILL/design-background-wait updates
- **Reviewer**: Cursor-Requirements
- **Severity**: nit
- **Focus area**: risk-integration
- **Location**: AGENTS.md:64
- **Phase**: design

