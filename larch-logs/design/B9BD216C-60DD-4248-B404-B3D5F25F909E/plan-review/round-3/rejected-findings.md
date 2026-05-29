### [Plan Review] FINDING_3

### FINDING_3: Identity-record slimming adds unnecessary churn
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation
- **Severity**: latent
- **Concern**: Removing fields from `.larch-keepalive` is not required to stop cleanup from treating it as a protection sentinel, and it expands the change with fixture, doc, and compatibility risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation, Codex-Innovation: For this PR, keep the existing .larch-keepalive fields and only change cleanup behavior plus wording that calls it cleanup protection. Defer field removal to a separate compatibility cleanup if still wanted.


### [Plan Review] FINDING_5

### FINDING_5: Symlink reaping exceeds session-dir cleanup scope
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements
- **Severity**: nit
- **Concern**: Adding dangling `current-design-env-*.sh` symlink reaping expands cleanup beyond the stated age-based session-directory retention scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements, Codex-Requirements: Drop symlink reaping from the cleanup implementation and test list unless the issue explicitly requires it


### [Plan Review] FINDING_7

### FINDING_7: Stamp write failure path may remain untested
- **Reviewer(s)**: Cursor-dyn-test-wiring, Codex-dyn-test-wiring
- **Severity**: latent
- **Concern**: The plan discusses stamp write failure and exact-cap retention, but the testing strategy does not explicitly require a harness case that simulates failed `.larch-installed-at` writes while pruning more than eight directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-wiring, Codex-dyn-test-wiring: Add the explicit stamp-failure case to the first Testing Strategy bullet: simulate stamp write failure with more than 8 dirs, assert ACTUAL_VERSION is retained, and assert exactly 8 dirs remain.

