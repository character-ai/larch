### [Plan Review] FINDING_1

### FINDING_1: Over-scoped `safe_step_value` allowlist rewrite
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Concern**: The plan’s full-string `safe_step_value` allowlist rewrite duplicates `resume_hint_for` logic and is not required to fix silent `ITEMS_TOTAL=0` filing. The root failure is piping a heading-less `stall-recovery-bug-body.md` into `/issue`; existing case globs already require full-string match (e.g. `8a<script>` becomes `unknown`). A large allowlist rewrite plus two sanitizer harness cases roughly doubles test surface for secondary hardening without demonstrating a concrete bypass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Minimum-change path: wire `issue-input-file` in `stall-recovery.md` and add only the proven production gap (`bump-branch-guard`) to the existing case arm; defer full-string grammar rewrite unless a concrete bypass is demonstrated


