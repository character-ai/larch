### External Reviewer Issues

- **Step review Step 2 — codex-review failed (exit 124 — quota — auth-retries=1, transient-retries=1)**:
  ```
Reading additional input from stdin...
⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1868s elapsed, output 0 bytes)
--- failed agent stderr tail ---
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1868s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
codex-quota: usage limit / quota reported on the codex exec --json events stream (<TMPDIR>/codex-primary-plan-edge-output.txt.events.jsonl); see that file for the reset time
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-edge dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-edge (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=TIMED_OUT
  ```


- **Step review Step 2 — codex-review failed (exit 124 — quota — auth-retries=1, transient-retries=1)**:
  ```
Reading additional input from stdin...
⏳ codex agent: still running (1m elapsed)
⏳ codex agent: still running (2m elapsed)
⏳ codex agent: still running (3m elapsed)
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1867s elapsed, output 0 bytes)
--- failed agent stderr tail ---
⏳ codex agent: still running (4m elapsed)
⏳ codex agent: still running (5m elapsed)
⏳ codex agent: still running (6m elapsed)
⏳ codex agent: still running (7m elapsed)
⏳ codex agent: still running (8m elapsed)
⏳ codex agent: still running (9m elapsed)
⏳ codex agent: still running (10m elapsed)
⏳ codex agent: still running (11m elapsed)
⏳ codex agent: still running (12m elapsed)
⏳ codex agent: still running (13m elapsed)
⏳ codex agent: still running (14m elapsed)
⏳ codex agent: still running (15m elapsed)
⏳ codex agent: still running (16m elapsed)
⏳ codex agent: still running (17m elapsed)
⏳ codex agent: still running (18m elapsed)
⏳ codex agent: still running (19m elapsed)
⏳ codex agent: still running (20m elapsed)
⏳ codex agent: still running (21m elapsed)
⏳ codex agent: still running (22m elapsed)
⏳ codex agent: still running (23m elapsed)
⏳ codex agent: still running (24m elapsed)
⏳ codex agent: still running (25m elapsed)
⏳ codex agent: still running (26m elapsed)
⏳ codex agent: still running (27m elapsed)
⏳ codex agent: still running (28m elapsed)
⏳ codex agent: still running (29m elapsed)
⏳ codex agent: still running (30m elapsed)
⏳ codex agent: still running (31m elapsed)
⚠ codex agent: TIMED OUT after 31 minutes, killing
❌ codex agent: TIMED OUT (exit code 124, 1867s elapsed, output 0 bytes)
--- end failed agent stderr tail ---
codex-quota: usage limit / quota reported on the codex exec --json events stream (<TMPDIR>/codex-primary-plan-arch-output.txt.events.jsonl); see that file for the reset time
  ```

- **Step design Step 3 — codex plan-review slot codex-plan-arch dropped: collector-failure (exit 0)**:
  ```
Reviewer slot codex-plan-arch (codex) was dropped under --no-fallback: collector-failure.
First ~200 chars of the offending output:
STATUS=TIMED_OUT
  ```
### Warnings

- **Step design Step 3.5 / Gate B — check-plan-size(drift-accepted) failed (exit 0)**:
  ```
Plan-size drift accepted by operator at Gate B round 3: DIFF_LINES=2150 vs BASELINE_DIFF_LINES=890 (ratio 2.42, multiple 2); PLAN_LINES=134 vs 99 (1.35). Scope growth driven by issue #3713 "audit ALL vendor-agent sites" + review-panel correctness/security fixes across rounds 1-3.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size(drift-auto-accepted-r4) failed (exit 0)**:
  ```
Plan-size drift re-fired at Gate B round 4; auto-accepted under standing operator consent.
  ```

- **Step design Step 3.5 / Gate B — check-plan-size(drift-auto-accepted-r5) failed (exit 0)**:
  ```
Plan-size drift re-fired at Gate B round 5; auto-accepted under standing operator consent.
  ```
