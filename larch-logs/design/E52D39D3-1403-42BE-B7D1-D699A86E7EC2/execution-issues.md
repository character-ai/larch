### Warnings

- **Step design Step 2b.5 — python plan check-size failed (exit 2)**:
  ```
PLAN_SIZE_STATUS=invalid-mechanical-churn
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=257 (baseline 113, ratio 2.27) / DIFF_LINES=242 (baseline 120, ratio 2.02) ≥ ×2, under absolute limits; proceeding.**
  ```
### External Reviewer Issues

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-arch dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-arch (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-innovation dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-innovation (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-pragmatic dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-pragmatic (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED ❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-requirements dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-requirements (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr:
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=3)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=3)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=3)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr:
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 7 — health-probe — auth-retries=1, transient-retries=5)**:
  ```
===== diag =====
health-probe fast-fail: codex unhealthy before launch
probe output: CODEX_BINARY_FOUND=true
CURSOR_BINARY_FOUND=true
CODEX_PRESENT=false
CURSOR_PRESENT=false
CODEX_AVAILABLE=false
CURSOR_AVAILABLE=false
CODEX_PROBE_TIMED_OUT=false
CURSOR_PROBE_TIMED_OUT=false; probe stderr: 
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=5)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=4)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
health-probe fast-fail: codex unhealthy before launch
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=1)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
❌ codex agent: FAILED (exit code 1, output 0 bytes)
  ```
