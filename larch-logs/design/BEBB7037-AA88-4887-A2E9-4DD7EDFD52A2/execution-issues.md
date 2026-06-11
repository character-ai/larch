### Warnings

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=586 (baseline 207, ratio 2.83) / DIFF_LINES=8030 (baseline 7880, ratio 1.02) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=637 (baseline 207, ratio 3.08) / DIFF_LINES=8055 (baseline 7880, ratio 1.02) ≥ ×2, under absolute limits; proceeding.**
  ```


- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=691 (baseline 207, ratio 3.34) / DIFF_LINES=8500 (baseline 7880, ratio 1.08) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=725 (baseline 207, ratio 3.5) / DIFF_LINES=8500 (baseline 7880, ratio 1.08) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — check-plan-size.sh (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=774 (baseline 207, ratio 3.74) / DIFF_LINES=8520 (baseline 7880, ratio 1.08) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 5c — design-log-publish.sh failed (exit 1)**:
  ```
design-log-publish: unexpected file under plan-review (see scripts/lib-design-round-artifacts.md): round-4/revise/claude-output.txt.stderr
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

- **Step review Step 2 — cursor-review failed (exit 8 — non-auth — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar.history =====
===== attempt =====
health-probe fast-fail: cursor unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: cursor unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: cursor unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false

===== attempt =====
health-probe fast-fail: cursor unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
===== sidecar =====
health-probe fast-fail: cursor unhealthy before launch
===== diag =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
  ```

- **Step review Step 2 — cursor-review failed (exit 1 — non-auth — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar.history =====
===== attempt =====
health-probe fast-fail: cursor unhealthy before launch

===== prior .diag (entry) =====
health-probe fast-fail: cursor unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
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

- **Step design Step 3 — cursor plan-review slot cursor-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot cursor-plan-innovation (cursor) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED timing-ledger.sh: WARNING: unknown task-kind: cursor-phase1-cursor-plan-innovation 
  ```
