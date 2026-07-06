### [Plan Review] FINDING_2

### FINDING_2: Cover `elif ! command grep` in the regression matrix
- **Reviewer(s)**: Cursor-Arch, Codex-Pragmatic
- **Severity**: minor
- **Concern**: The new lint rule claims to reject the negated `elif` shape, but the regression set does not include a failing `elif ! command grep` case, so an under-broad pattern could still pass the harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Add one failing temp fixture with elif ! command grep -q PATTERN file and assert the new rule text in stderr, using the same suppression-strip pattern as existing bad.sh cases."
  - From Codex-Pragmatic: "Add a failing `elif ! command grep` fixture and assert the same lint error text, ideally alongside the existing grep-family variant"


### [Plan Review] FINDING_3

### FINDING_3: Stabilize the lint rule’s stderr label
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan does not pin a single violation string, so the new assertions can drift if the report text changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: "Name the violation once in scripts/lint-bash32.md and reuse that exact `<rule>` string in the awk report() call and in every new test-lint-bash32.sh needle"


