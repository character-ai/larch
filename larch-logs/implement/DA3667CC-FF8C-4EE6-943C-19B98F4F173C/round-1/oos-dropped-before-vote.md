### OOS_1: [OUT_OF_SCOPE] Empty-fingerprint live-materialization ordering is overconstrained
- **Reviewer(s)**: codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The empty-fingerprint path is still pinned to live diff materialization before invalid staged metadata is rejected, and the helper currently skips the live pinning branch when `DIFF_FINGERPRINT` is falsy. That makes a safer fail-fast metadata check incompatible with the current assertion shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Remove the call-count assertion, or assert no materialization after changing the helper to validate stored metadata first.

