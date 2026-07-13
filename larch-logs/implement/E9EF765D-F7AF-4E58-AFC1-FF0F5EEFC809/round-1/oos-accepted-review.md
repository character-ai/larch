### OOS_1: [OUT_OF_SCOPE] untrusted outcome sidecar writes
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Ship outcome sidecar writes lack trusted-root symlink checks, allowing a symlink swap under `IMPLEMENT_TMPDIR` to redirect writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
