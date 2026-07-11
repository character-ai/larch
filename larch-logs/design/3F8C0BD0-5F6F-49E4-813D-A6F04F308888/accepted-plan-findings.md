### FINDING_1: Recovery can proceed without persisted coverage
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The stale-mismatch recovery path does not fail closed when its second `load_coverage(tmpdir)` call returns `None`. If coverage disappears during recovery, teardown can select `"closes"`, apply the `[DONE]` rename, and complete without validated persisted evidence.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: After recovery calls `load_coverage(tmpdir)`, explicitly raise `ShipError` if it returns `None`. Add this case to the focused recovery test so the done rename and cleanup remain blocked


