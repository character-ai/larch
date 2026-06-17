### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — unknown — auth-retries=2, transient-retries=1)**:
  ```
===== diag =====
Error: [unavailable] Service Unavailable
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-final-report-rooting dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-final-report-rooting (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED ❌ cursor agent: FAILED (exit code 1, output 0 bytes) ❌ cursor agent: FAILED (exit code 1, output 0 bytes)
  ```
