### [Plan Review] FINDING_2

### FINDING_2: Invoke-only harness must be executable
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The invoke-only harness for `skills/design/scripts/test-trailer-awk.sh` (proposed; wired like existing `test-trailer-has-any.sh` adapters at `skills/design/scripts/test-trailer-helpers.sh:36-41`) must be executable. Sibling `test-trailer-*.sh` scripts are `+x` today; a new file defaulting to `644` yields `Permission denied` and `make test-trailer-helpers` fails closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Require `chmod +x` on `test-trailer-awk.sh` (match sibling `test-trailer-*.sh`) or invoke via `bash "$SCRIPT_DIR/test-trailer-awk.sh"`.


