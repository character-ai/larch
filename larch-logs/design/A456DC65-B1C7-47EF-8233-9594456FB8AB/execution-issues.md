### Warnings

- **Step design Step 2b drafter — launch-codex-drafter.sh failed (exit 7)**:
  ```
Step 2b drafter fallback: rc-7 REASON=CODEX_EXEC_FAILED
  ```

### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 1 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
❌ cursor agent: FAILED (exit code 1, 20s elapsed, output 0 bytes)
--- failed agent stderr tail ---
b: Provider Error We're having trouble connecting to the model provider. This might be temporary - please try again in a moment.
Failed with exit code 1 after 20s. Output size: 0 bytes.
--- end failed agent stderr tail ---
===== diag =====
b: Provider Error We're having trouble connecting to the model provider. This might be temporary - please try again in a moment.
Failed with exit code 1 after 20s. Output size: 0 bytes.
  ```

- **Step design Step 3 — cursor plan-review slot dyn-cursor-plan-json-schema-gap dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-cursor-plan-json-schema-gap (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED timing-ledger.sh: WARNING: unknown task-kind: cursor-phase1-dyn-cursor-plan-json-schema-gap 
  ```
