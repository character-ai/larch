### [Plan Review] FINDING_2

### FINDING_2: File-list order conflicts with required A2-before-A1 commit sequence
- **Reviewer(s)**: Cursor-dyn-commit-sequence
- **Severity**: important
- **Concern**: `Files to modify` lists A1 harness (`scripts/test-implement-structure.sh`) before A2 launcher pins, while Approach requires A2 first. An implementer editing or committing top-to-bottom — or splitting item A into an A1-then-A2 commit — can land the scanner while `record-vendor-task` lines at `scripts/launch-codex-implement.sh:230`, `scripts/launch-cursor-implement.sh:169`, `scripts/launch-codex-ci.sh:247`, `scripts/launch-cursor-ci.sh:230`, and `scripts/launch-claude-ci.sh:192` remain unpinned, so the new A1 guard fails until every A2 pin is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-commit-sequence: Reorder Files to modify so all A2 launcher entries precede scripts/test-implement-structure.sh, or add an explicit Commit sequence bullet stating file-list order is not commit order and A2 pins must be committed with or before A1


