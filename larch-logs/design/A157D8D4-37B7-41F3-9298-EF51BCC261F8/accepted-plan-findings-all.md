### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/external-reviewers.md:10
- **Concern**: The proposed one-down non-interactive wording drops the existing Continue-sentinel exception. Scenario: A non-interactive resume after an operator already chose Continue has .degraded-tools-gate-prompted and should proceed degraded, but the planned text would say it emits a prompt-required envelope anyway
- **Proposed resolution**: Revise the plan to state one-down with an explicit Continue sentinel proceeds degraded in every mode, and qualify prompt-required routing as the one-down without-sentinel path


