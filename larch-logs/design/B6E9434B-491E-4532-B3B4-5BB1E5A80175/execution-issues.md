### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=696 (baseline 330, ratio 2.11) / DIFF_LINES=650 (baseline 520, ratio 1.25) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=768 (baseline 330, ratio 2.33) / DIFF_LINES=720 (baseline 520, ratio 1.38) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=798 (baseline 330, ratio 2.42) / DIFF_LINES=710 (baseline 520, ratio 1.37) ≥ ×2, under absolute limits; proceeding.**
  ```

### External Reviewer Issues

- **findings aggregator**: merged output failed validation; leaving <TMPDIR>/findings-in-scope.md unchanged. See <TMPDIR>/aggregator-validate.stderr.

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
