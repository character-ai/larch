### FINDING_6: Stage-all behavior has targeted regression coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Tests cover clean collected paths, partial dirty selection, nested untracked files, and the updated status-command argument split.

### FINDING_7: [OUT_OF_SCOPE] Missing mismatched-working-directory fixture
- **Reviewer(s)**: dyn-dyn-stage-all-dirty-intersect
- **Severity**: nit
- **Concern**: The Git fixtures do not verify behavior when the process working directory differs from `CLAUDE_PROJECT_DIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-stage-all-dirty-intersect: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Missing multi-path order fixture
- **Reviewer(s)**: dyn-dyn-stage-all-dirty-intersect
- **Severity**: nit
- **Concern**: Partial-dirty coverage does not verify preservation of commit pathspec order when multiple collected paths remain dirty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-stage-all-dirty-intersect: Address the concern above.
