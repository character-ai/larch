### External Reviewer Issues

- **Step review Step 2 — cursor-review failed (exit 124 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
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

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar.history =====
===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
===== sidecar =====
health-probe fast-fail: codex unhealthy before launch
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
  ```

- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar.history =====
===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
===== sidecar =====
health-probe fast-fail: codex unhealthy before launch
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
  ```


- **Step review Step 2 — codex-review failed (exit 7 — non-auth — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar.history =====
===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: codex unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
===== sidecar =====
health-probe fast-fail: codex unhealthy before launch
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
  ```
### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=411 (baseline 179, ratio 2.3) / DIFF_LINES=738 (baseline 232, ratio 3.18) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=498 (baseline 179, ratio 2.78) / DIFF_LINES=810 (baseline 232, ratio 3.49) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=556 (baseline 179, ratio 3.11) / DIFF_LINES=872 (baseline 232, ratio 3.76) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 5c — design-log-publish.sh failed (exit 1)**:
  ```
design-log-publish: unexpected file under plan-review (see scripts/lib-design-round-artifacts.md): round-2/revise/codex-output-candidate.patch
  ```
