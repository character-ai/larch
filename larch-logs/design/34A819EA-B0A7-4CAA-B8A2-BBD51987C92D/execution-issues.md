### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 124 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar.history =====
===== cursor auth attempt =====
❌ cursor agent: FAILED (exit code 1, 10s elapsed, output 0 bytes)
--- failed agent stderr tail ---
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1 after 10s. Output size: 0 bytes.
--- end failed agent stderr tail ---

===== cursor auth diag =====
Error: Password not found for account 'cursor-user' and service 'cursor-access-token'
Failed with exit code 1 after 10s. Output size: 0 bytes.
===== sidecar =====
⏳ cursor agent: still running (1m elapsed)
⏳ cursor agent: still running (2m elapsed)
⏳ cursor agent: still running (3m elapsed)
⚠ cursor agent: TIMED OUT after 3 minutes, killing
❌ cursor agent: TIMED OUT (exit code 124, 186s elapsed, output 0 bytes)
--- failed agent stderr tail ---
Timed out after 186s (limit: 180s). Process was killed after exceeding the timeout. Output size: 0 bytes.
--- end failed agent stderr tail ---
===== diag =====
Timed out after 186s (limit: 180s). Process was killed after exceeding the timeout. Output size: 0 bytes.
  ```
### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=251 (baseline 119, ratio 2.11) / DIFF_LINES=286 (baseline 210, ratio 1.36) ≥ ×2, under absolute limits; proceeding.**
  ```
