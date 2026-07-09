---LARCH-REJECTED-BEGIN---
## Considered Plan Review Suggestions (Not Adopted)

These reviewer suggestions were considered but not adopted. Some may already be addressed by the current plan; they are not automatically unimplemented gaps.

### [Plan Review] FINDING_2

### FINDING_2: Dead agent-lint rows for deleted harnesses
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Concern**: After the planned file deletions, `agent-lint.toml` will still list removed hook and anti-polling harness entries (`test-hook-bg-poll-guard`, `test-hook-no-progress-guard`, `test-implement-anti-polling-rule`, and their companion docs), so the shipped inventory diverges from the tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Remove those rows from `agent-lint.toml` when the files are deleted


### [Plan Review] FINDING_3

### FINDING_3: Render-cost-line harness still pins removed task-notification wording
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The plan rewrites `skills/shared/final-summary-emit.md` and `skills/implement/SKILL.md` to remove task-notification source text, but `scripts/test-render-cost-line-callsites.sh` still requires the old literals. `make test-harnesses` will fail after the planned prose change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add scripts/test-render-cost-line-callsites.sh to the plan and retarget these greps to the new foreground-wrapper/source wording without the forbidden token


---LARCH-REJECTED-END---
