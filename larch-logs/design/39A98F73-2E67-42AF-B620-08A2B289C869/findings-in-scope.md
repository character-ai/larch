### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:86-88
- **Concern**: Task-output counter keys by path but plan never defines Bash canonical path extraction. Scenario: Item 3 says key task-output state by path only; Bash branch only classifies via suffix-tolerant match in the full command string. If implementer keys state by the entire tool_input.command (or by unstable prefixes), incident-shaped variants (sleep && cat …/tasks/id.output 2>/dev/null vs bare cat …/tasks/id.output) never share a counter and slow per-turn Bash polling can evade threshold 2
- **Proposed resolution**: Specify in hook changes: capture the matched tasks/<id>.output token (prefer full absolute path when present in command, else tasks/<id>.output) and use that normalized string as the task-output state key for both Read and Bash branches; add harness case with two Bash payloads that differ only in leading wrappers/suffixes but share the same task id

