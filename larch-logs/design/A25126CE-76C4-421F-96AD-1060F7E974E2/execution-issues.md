### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-bash-contract dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-bash-contract (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=2, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-innovation (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-requirements dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-requirements (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-bash-parity-auditor dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-bash-parity-auditor (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-run-log-recovery dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-run-log-recovery (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⏳ cursor agent: still running (4m elapsed)
⏳ cursor agent: still running (5m elapsed)
⏳ cursor agent: still running (6m elapsed)
⏳ cursor agent: still running (7m elapsed)
⏳ cursor agent: still running (8m elapsed)
⏳ cursor agent: still running (9m elapsed)
⏳ cursor agent: still running (10m elapsed)
❌ cursor agent: FAILED (exit code 1, 610s elapsed, output 0 bytes)
--- failed agent stderr tail ---
Connection lost, reconnecting (attempt 1)...
Retry attempt 1...
Connection lost, reconnecting (attempt 2)...
Retry attempt 2...
Connection lost, reconnecting (attempt 3)...
Retry attempt 3...
T: [resource_exhausted] Error
Failed with exit code 1 after 610s. Output size: 0 bytes.
--- end failed agent stderr tail ---
  ```

### Warnings

- **Step 2b.5 (plan-size-trigger):** operator chose "override and continue" on the hard plan-size trigger (TRIGGER_REASONS=diff-lines, DIFF_LINES=1800 > 1500). No Split, no Cancel. Proceeding to Step 3b -> Step 4 -> Gate C with the current plan (PLAN_LINES=157, 14 file sections, 11 accepted findings applied). Round 1 decisions verified intact (parity-only, no new make target, bash untouched).
