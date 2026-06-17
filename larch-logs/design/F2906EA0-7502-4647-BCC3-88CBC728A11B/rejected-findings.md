### [Plan Review] FINDING_1

### FINDING_1: Cross-tool contention tests may not exercise blocking under delayed release
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Contention regression tests may omit holder lock semantics across delayed release. If the implementer calls `release_after` on the first acquire before the contending acquire, the default 0.5s delayed `rmdir` can drop the lock so cross-tool/cross-lane assertions flake or never exercise blocking.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In cross-tool and cross-lane test steps, state explicitly: do not call release_after on the holder before the second acquire; pin LARCH_EXTERNAL_STARTUP_LOCK_DELAY high (e.g. 60) or only rmdir in finally


