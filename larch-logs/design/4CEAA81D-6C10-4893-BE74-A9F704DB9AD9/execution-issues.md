### External Reviewer Issues

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
⏳ cursor agent: still running (11m elapsed)
⏳ cursor agent: still running (12m elapsed)
⏳ cursor agent: still running (13m elapsed)
⏳ cursor agent: still running (14m elapsed)
⏳ cursor agent: still running (15m elapsed)
⏳ cursor agent: still running (16m elapsed)
⏳ cursor agent: still running (17m elapsed)
⏳ cursor agent: still running (18m elapsed)
⏳ cursor agent: still running (19m elapsed)
❌ cursor agent: FAILED (exit code 1, 1141s elapsed, output 0 bytes)
--- failed agent stderr tail ---
Connection lost, reconnecting (attempt 1)...
Retry attempt 1...
Connection lost, reconnecting (attempt 2)...
Retry attempt 2...
Connection lost, reconnecting (attempt 3)...
Retry attempt 3...
T: [resource_exhausted] Error
Failed with exit code 1 after 1141s. Output size: 0 bytes.
--- end failed agent stderr tail ---
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
⏳ cursor agent: still running (11m elapsed)
⏳ cursor agent: still running (12m elapsed)
⏳ cursor agent: still running (13m elapsed)
⏳ cursor agent: still running (14m elapsed)
⏳ cursor agent: still running (15m elapsed)
⏳ cursor agent: still running (16m elapsed)
⏳ cursor agent: still running (17m elapsed)
⏳ cursor agent: still running (18m elapsed)
⏳ cursor agent: still running (19m elapsed)
❌ cursor agent: FAILED (exit code 1, 1141s elapsed, output 0 bytes)
--- failed agent stderr tail ---
Connection lost, reconnecting (attempt 1)...
Retry attempt 1...
Connection lost, reconnecting (attempt 2)...
Retry attempt 2...
Connection lost, reconnecting (attempt 3)...
Retry attempt 3...
T: [resource_exhausted] Error
Failed with exit code 1 after 1141s. Output size: 0 bytes.
--- end failed agent stderr tail ---
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-pragmatic dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-pragmatic (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-quiet-fd-parity dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-quiet-fd-parity (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-arch dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-arch (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-edge dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-edge (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-innovation (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-pragmatic dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-pragmatic (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — cursor plan-review slot cursor-plan-requirements dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-requirements (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-requirements dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-requirements (codex) was dropped under --no-fallback: collector-failure.
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

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-pin-literal-consistency dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-pin-literal-consistency (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
health-probe fast-fail: cursor unhealthy before launch
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-pin-coherence dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-pin-coherence (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=3)**:
  ```
  ```
### Warnings

- **Step dispatch-plan-voters.sh voter1 — launch-claude-review.sh (claude plan voter) failed (exit 1)**:
  ```
voter1_rc=1
output_bytes=      70
--- first 200 bytes of voter output ---
You've hit your session limit · resets 12:50am (America/Los_Angeles)

  ```
