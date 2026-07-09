### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-anti-polling-rule.md:1-67
- **Concern**: Stale companion doc for the deleted anti-polling harness still pins retired literals. Scenario: The markdown still names `design-background-wait`, `task-notification`, and other removed contracts, so the plan’s extinct-token grep will keep failing even after `scripts/test-implement-anti-polling-rule.sh` is deleted
- **Proposed resolution**: Delete this companion doc with the harness, or rewrite it to describe only the bgjob-wait replacement contract

### FINDING_2:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: agent-lint.toml:572-574,893-899,1038-1041
- **Concern**: Removed hook and anti-polling harness entries still remain in the agent-lint inventory. Scenario: After the file deletions, `agent-lint.toml` will still carry dead rows for `test-hook-bg-poll-guard`, `test-hook-no-progress-guard`, `test-implement-anti-polling-rule`, and their companion docs, so the shipped inventory and tree diverge
- **Proposed resolution**: Remove those rows from `agent-lint.toml` when the files are deleted

### FINDING_3:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-render-cost-line-callsites.sh:66-99
- **Concern**: Final-summary token removal leaves live harness pins for the removed task-notification wording. Scenario: The plan rewrites skills/shared/final-summary-emit.md and skills/implement/SKILL.md to remove task-notification source text, but make test-render-cost-line-callsites still requires the old literals, so make test-harnesses fails after the planned prose change
- **Proposed resolution**: Add scripts/test-render-cost-line-callsites.sh to the plan and retarget these greps to the new foreground-wrapper/source wording without the forbidden token
