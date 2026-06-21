### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/cleanup_skill.py:157
- **Concern**: Cleanup stderr still labels all design symlink removals as dangling after plan expands removal to resolved symlinks with missing tmpdir. Scenario: After the reaper removes a resolved current-design-env-*.sh whose export-prefixed env points at a deleted DESIGN_TMPDIR, SYMLINKS_REMOVED increments but the footer still prints dangling design-env links; operators may think only broken symlinks were removed and miss that valid-looking session links were reaped
- **Proposed resolution**: Update the cleanup footer (and any test assertions on stderr) to neutral wording such as stale design-env symlinks removed, or split counters for dangling vs missing-tmpdir; do not keep dangling-only prose when resolved symlinks are removed per plan Files section
