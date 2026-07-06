### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:7-15
- **Concern**: [SCOPE-REDUCTION] The Read carve-out is specified for every live bg wait even though the bug is /design Step 3 only. Scenario: The plan would remove the task-output Read deny globally and word the contract generically, which weakens the existing /implement Steps 3/5 notification-only guard that says not to read task output while the child is still running. A premature /implement notification could now read empty task output each turn and revive the polling loop the hook currently blocks.
- **Proposed resolution**: Scope Fix A/B to /design Step 3. In the hook, exempt task-output Read only when the retained live marker step is design-step3-review. Keep task-output Read denial for implement markers. Word AGENTS.md and orchestrator-never.md as a /design-only carve-out while preserving /implement notification-only text.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-bg-poll-guard.sh:1128-1154
- **Concern**: [SCOPE-REDUCTION] The planned Read carve-out removes the global tasks/*.output denial for every live marker, not just /design recovery. Scenario: An implement-step5-review or implement-step3-checks marker currently denies same-clone Read of tasks/foo.output while the child is still running; after deleting the arm, that Read is allowed even though skills/implement/SKILL.md and orchestrator-never keep /implement premature notifications notification-only and forbid task-output reads, reopening the polling path the hook protects.
- **Proposed resolution**: Scope the Read exemption to the /design wait steps that need empty-output classification, or keep tasks/*.output Read denied for implement-* markers and keep/update the implement marker regression assertions
