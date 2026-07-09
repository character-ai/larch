### FINDING_1: Stale anti-polling companion doc pins retired literals
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The companion markdown for the deleted anti-polling harness still pins retired literals (`design-background-wait`, `task-notification`, and other removed contracts). After `scripts/test-implement-anti-polling-rule.sh` is deleted, that stale doc can keep the plan’s extinct-token grep failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Delete this companion doc with the harness, or rewrite it to describe only the bgjob-wait replacement contract

### FINDING_2: Dead agent-lint rows for deleted harnesses
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: After the planned file deletions, `agent-lint.toml` will still list removed hook and anti-polling harness entries (`test-hook-bg-poll-guard`, `test-hook-no-progress-guard`, `test-implement-anti-polling-rule`, and their companion docs), so the shipped inventory diverges from the tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove those rows from `agent-lint.toml` when the files are deleted

### FINDING_3: Render-cost-line harness still pins removed task-notification wording
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan rewrites `skills/shared/final-summary-emit.md` and `skills/implement/SKILL.md` to remove task-notification source text, but `scripts/test-render-cost-line-callsites.sh` still requires the old literals. `make test-harnesses` will fail after the planned prose change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add scripts/test-render-cost-line-callsites.sh to the plan and retarget these greps to the new foreground-wrapper/source wording without the forbidden token

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: scripts/test-implement-anti-polling-rule.md:1-67
- **Concern**: [SCOPE-REDUCTION] Deleted anti-polling harness leaves its companion doc with extinct notification-stack tokens. Scenario: The plan deletes scripts/test-implement-anti-polling-rule.sh and adds an extinct-token harness that excludes only larch-logs, but the companion markdown still contains design-background-wait, silent yield, and premature notification, so the new acceptance grep fails
- **Proposed resolution**: Delete scripts/test-implement-anti-polling-rule.md with the harness or explicitly rewrite it so none of the extinct tokens remain
