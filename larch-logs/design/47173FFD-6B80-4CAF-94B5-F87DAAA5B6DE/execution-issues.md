### Tool Failures

- **Step design pause save — design-log-publish.sh failed (exit 1)**:
  ```
design-log-publish: git push failed: unknown
design-log-publish: local commit preserved on ref larch-log-design-recovery-47173FFD-6B80-4CAF-94B5-F87DAAA5B6DE (a86299944f305441d9475563594e6d0a8babe9a7)
  ```

### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-innovation (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```
