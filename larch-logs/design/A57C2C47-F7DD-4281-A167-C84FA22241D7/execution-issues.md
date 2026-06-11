### Warnings

- **Step design Step 2b drafter — launch-codex-drafter.sh failed (exit 7)**:
  ```
Step 2b drafter fallback: rc-7 CODEX_EXEC_FAILED
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=595 (baseline 203, ratio 2.93) / DIFF_LINES=4950 (baseline 4900, ratio 1.01) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=673 (baseline 203, ratio 3.32) / DIFF_LINES=5020 (baseline 4900, ratio 1.02) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=800 (baseline 203, ratio 3.94) / DIFF_LINES=5150 (baseline 4900, ratio 1.05) ≥ ×2, under absolute limits; proceeding.**
  ```

### External Reviewer Issues

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
