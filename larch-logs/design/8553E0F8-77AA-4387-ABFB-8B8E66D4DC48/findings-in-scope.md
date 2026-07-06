### FINDING_1: Premature-notification contract still blocks the classification Read
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The loaded wait contracts still describe empty-output handling and silent yield in a way that can be read as forbidding the one post-notification `Read` needed to classify a premature notification, and that ambiguity reaches AGENTS.md, skills/design/SKILL.md, skills/shared/design-background-wait.md, and skills/shared/orchestrator-never.md.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "In each listed surface, make step (1) exactly one post-notification Read of the active tasks/*.output; step (2) missing/empty file → silent yield with no further tools; keep prefix-identical repeat and the single sentinel probe after non-empty output; revise silent-yield wording and AGENTS.md "once after completion" so they cover classification Read vs post-completion parse"
  - From Cursor-Innovation: "Reorder every loaded premature-notification contract to: after `<task-notification>`, exactly one Read of the active tasks/*.output to classify; missing/empty file → silent yield; prefix-identical repeat → silent yield; new/changed non-empty file → one terminal-sentinel probe; then after-completion parse. Redefine silent yield as no probe/parse tools after an empty classification Read, not no tools at all"
  - From Cursor-Innovation: "Fix B must state explicitly that empty/non-empty means the tasks/*.output file bytes (missing, whitespace-only, or content), not notification wrapper/summary text; revise AGENTS.md line 65 to distinguish one post-notification emptiness Read from the after-completion result parse; mirror the same wording in orchestrator-never.md NEVER #3"
  - From Cursor-Innovation: "Either extend the listed skills/design/SKILL.md edit to Step 5c/Final summary/Step 4 inline wait bullets, or add one explicit sentence in each that defer to the updated Immediate-background wait rule in skills/shared/design-background-wait.md for post-notification Read classification"
  - From Cursor-Pragmatic: "Rewrite the ordered recovery contract to: (1) after `<task-notification>`, one Read of the active task output; (2) missing/empty file → silent yield with no further tools; (3) prefix-identical repeat → silent yield; (4) new/changed non-empty output → one terminal-sentinel probe. Update NEVER #5 silent-yield wording to forbid further tools after classification, not the classification Read itself; mirror the same ordering in `skills/design/SKILL.md` Step 3 routing and `skills/shared/design-background-wait.md` Step 3 section."
  - From Cursor-Pragmatic: "Revise AGENTS.md:65 to distinguish one post-notification classification Read (not polling; not the after-completion parse) from the after-completion result read, and keep the per-turn no-polling ban otherwise unchanged."
  - From Cursor-Requirements: "Reword silent yield to mean no further tools after the single classification Read; update Apply in order to (0) one post-notification Read of the active tasks/*.output, then (1) empty/missing silent yield, (2) prefix-identical repeat, (3) terminal-sentinel probe; mirror the same ordering in design-background-wait.md Immediate-background and Step 3 sections and refresh both harness pin sets."
  - From Cursor-Pragmatic: "Revise AGENTS.md:65 to distinguish one post-notification classification Read (not polling; not the after-completion parse) from the after-completion result read, and keep the per-turn no-polling ban otherwise unchanged."

### FINDING_2: Anti-polling harness refresh is missing from the plan
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: major
- **Concern**: The plan updates the contract prose but leaves `scripts/test-implement-anti-polling-rule.sh` and its test strategy out of scope, so the same pinned literals that enforce the old wait wording will still fail or stay stale in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`; refresh the AGENTS.md, design-background-wait.md, and orchestrator-never.md literals so they pin the new one post-notification `Read` carve-out while retaining the no-polling and implement bans."
  - From Cursor-Innovation: "Add scripts/test-implement-anti-polling-rule.sh to the firm plan (or a explicit cross-reference in the test-design-structure item) and refresh pins there in the same change when AGENTS.md and orchestrator-never.md gain the post-notification Read carve-out"
  - From Cursor-Pragmatic: "Add `### UPDATED: scripts/test-implement-anti-polling-rule.sh`, refresh the anchored literals (including `no tool`, empty-output, and Step 3 ordered-routing pins), and run `make test-implement-anti-polling-rule` in Testing strategy."
  - From Codex-Requirements: "Add scripts/test-implement-anti-polling-rule.sh to the plan, refresh its pinned literals for the one-Read-after-notification carve-out, and include make test-implement-anti-polling-rule in focused validation"

### FINDING_3:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:7-15
- **Concern**: [SCOPE-REDUCTION] The Read carve-out is specified for every live bg wait even though the bug is /design Step 3 only. Scenario: The plan would remove the task-output Read deny globally and word the contract generically, which weakens the existing /implement Steps 3/5 notification-only guard that says not to read task output while the child is still running. A premature /implement notification could now read empty task output each turn and revive the polling loop the hook currently blocks.
- **Proposed resolution**: Scope Fix A/B to /design Step 3. In the hook, exempt task-output Read only when the retained live marker step is design-step3-review. Keep task-output Read denial for implement markers. Word AGENTS.md and orchestrator-never.md as a /design-only carve-out while preserving /implement notification-only text.

### FINDING_4:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/hook-bg-poll-guard.sh:1128-1154
- **Concern**: [SCOPE-REDUCTION] The planned Read carve-out removes the global tasks/*.output denial for every live marker, not just /design recovery. Scenario: An implement-step5-review or implement-step3-checks marker currently denies same-clone Read of tasks/foo.output while the child is still running; after deleting the arm, that Read is allowed even though skills/implement/SKILL.md and orchestrator-never keep /implement premature notifications notification-only and forbid task-output reads, reopening the polling path the hook protects.
- **Proposed resolution**: Scope the Read exemption to the /design wait steps that need empty-output classification, or keep tasks/*.output Read denied for implement-* markers and keep/update the implement marker regression assertions
