### OOS_1: Step 8 trust-boundary docs still describe a single delegated assessment lane.
- **Description**: Step 8 trust-boundary docs still describe a single delegated assessment lane.. Scenario: After the waterfall lands, SECURITY.md will still tell operators the adapter delegates to one lane, which misstates who may author assessments and weakens incident review.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: SECURITY.md:51-55
- **Phase**: design



### OOS_2: The agent contract header still says only the Claude launcher consumes it.
- **Description**: The agent contract header still says only the Claude launcher consumes it.. Scenario: Codex and Cursor lanes copy the same contract into agent-contract.md; the Claude-only header will confuse future maintainers about which vendors honor the file.
- **Reviewer**: Cursor-Arch
- **Severity**: nit
- **Focus area**: architecture
- **Location**: skills/implement/references/architectural-assessment-agent.md:3-7
- **Phase**: design



