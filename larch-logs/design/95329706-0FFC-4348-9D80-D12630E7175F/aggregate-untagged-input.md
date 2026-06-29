### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:95-108
- **Concern**: Testing plan makes the broader design harness pass optional. Scenario: The issue hard guard requires existing design harnesses to pass, but the plan allows stopping after a narrow subset and only running the broader shard if time allows
- **Proposed resolution**: Replace the optional shard language with a required concrete design-harness verification set, and remove "if time allows" for the relevant CI shard or targets
