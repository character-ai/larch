### Warnings

- **Step design Step 2b.5 — python plan check-size failed (exit 2)**:
  ```
PLAN_SIZE_STATUS=invalid-mechanical-churn
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=170 (baseline 115, ratio 1.48) / DIFF_LINES=122 (baseline 57, ratio 2.14) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=178 (baseline 115, ratio 1.55) / DIFF_LINES=144 (baseline 57, ratio 2.53) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 2b.5 — python plan check-size (drift) failed (exit 0)**:
  ```
**⚠ 2b.5: plan-size — drift advisory: plan grew PLAN_LINES=199 (baseline 115, ratio 1.73) / DIFF_LINES=174 (baseline 57, ratio 3.05) ≥ ×2, under absolute limits; proceeding.**
  ```

- **Step design Step 5c — design-log-publish.sh failed (exit 1)**:
  ```
design-log-publish: unexpected file under plan-review (see python/plan_review.py): round-1/revise/cursor-output.txt.token-record
  ```
### External Reviewer Issues

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
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-requirements dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-requirements (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step design Step 3 — codex plan-review slot dyn-codex-plan-prompt-contract dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-codex-plan-prompt-contract (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
  ```

- **Step design Step 3 — codex plan-review slot dyn-codex-plan-structure-pins dropped: collector-failure (exit 0)**:
  ```
Reviewer slot dyn-codex-plan-structure-pins (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=FAILED health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealthy before launch health-probe fast-fail: codex unhealth
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

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=2)**:
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

- **Step review Step 2 — codex-review failed (exit 1 — unknown — auth-retries=1, transient-retries=2)**:
  ```
===== sidecar =====
Reading additional input from stdin...
Not inside a trusted directory and --skip-git-repo-check was not specified.
===== diag =====
Failed with exit code 1. Output size: 0 bytes.
===== launch-stderr =====
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
  ```
