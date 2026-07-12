### [Plan Review] FINDING_1

### FINDING_1: Step 2 stdout contract omits CLI-gate `REASON`
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: The authoritative Step 2 stdout contract still restricts `REASON` to `STATUS=bailed`, conflicting with actionable `REASON` output for clean-tree CLI-gate `claude_fallback`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add `### UPDATED: skills/implement/references/step2-dispatch.md` documenting optional sanitized `REASON` on CLI-gate `claude_fallback` (clean tree), the dirty-tree forbidden-authority path, and KV sanitization limits; mirror in `python/tests/implement/test_implement_dispatch.py` and the edit-in-sync list.
  - From Cursor-Requirements: Add ### UPDATED: skills/implement/references/step2-dispatch.md: document optional REASON on claude_fallback for CLI-version gate fallback (sanitized operator message, not a bail token); keep REASON required semantics for STATUS=bailed; sync the mechanical-bail list and edit-in-sync pointers.


### [Plan Review] FINDING_2

### FINDING_2: CLI upgrade message remains hidden from Step 2 chat
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Concern**: The actionable CLI upgrade reason is only added to `execution-issues.md`, while operator-visible Step 2 chat continues showing the vague selection-drift message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In the `coder=codex` + `STATUS=claude_fallback` branch, when `REASON` matches the CLI-upgrade detector, print that message in chat (replace the drift banner or add a second visible line) and keep the Warnings log; do not rely on file-only surfacing.


### [Plan Review] FINDING_3

### FINDING_3: Gate detection may be ordered after dirty-state handling
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: A gated Codex failure that also mutates the tree could be classified as `dirty-state-after-timeout` before gate detection, hiding the actionable upgrade reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In dispatch_step2.py plan text, require shared gate detection immediately after each failed Codex attempt and before the dirty-tree retry/bail branch; when a gate is present on a mutating failure, emit STATUS=bailed with the actionable upgrade REASON (forbidden authority), not dirty-state-after-timeout.


### [Plan Review] FINDING_4

### FINDING_4: Dirty-tree gate path does not explicitly require `STATUS=bailed`
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The plan does not explicitly require `STATUS=bailed` for mutating gated failures, risking an invalid `claude_fallback` envelope with forbidden edit authority.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Explicitly state that mutating gated failures return STATUS=bailed with ORCHESTRATOR_EDIT_AUTHORITY=forbidden and REASON set to the sanitized upgrade message; reserve STATUS=claude_fallback for the clean-tree gate path only.

