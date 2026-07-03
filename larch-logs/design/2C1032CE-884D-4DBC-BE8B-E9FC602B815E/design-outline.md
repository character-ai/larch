## Proposed Design Outline

### Goals
- Fix the 3 verified, low-risk findings from issue #6091 (round-cap drop, missing tests, duplicated constant).
- Keep the `gate-b-apply` Gantt bar visible even when a full reviewer panel trips the row cap.
- Close the direct-unit-test gap for `_gate_b_apply_start_s` without changing its behavior.
- Remove the duplicated vendor-column-count constant so the two modules can't drift apart.

### Non-goals
- No per-attempt round timing rows for design re-entry. Current single-row-per-round behavior is intentional and already covered by a passing idempotency test.
- No retry or `execution-issues` surfacing for `TimingLedger._append` flock-timeout drops. Pre-existing, broad (affects all vendor rows, not just Gate B), unproven in production.
- No export of a public Gate B timing helper or module restructuring. Cross-module private imports are the existing convention in `larch.review`.

### Approach sketch
- `progress_report.py`: add `"gate-b-apply"` to `_CODER_APPLY_TASK_KINDS` so `_cap_gantt_rows_reserving_apply` reserves it like the other `*/apply` lanes (same fix pattern as issue #5264).
- `timing.py`: add one canonical vendor-row column-count constant, colocated with the existing sibling constants `TIMING_TASK_KINDS_ALLOWED` / `TIMING_VENDORS_ALLOWED` in the same file (not moved to `config.py`, to match how those siblings are already organized).
- `plan_review_loop.py` and `progress_report.py`: import that constant instead of defining `TIMING_VENDOR_COLS` / `TIMING_VENDOR_MIN_COLS` locally.
- `test_plan_review.py`: add direct unit tests for `_gate_b_apply_start_s` covering empty ledger, boundary (latest vendor end at or after `end_s`), unreadable ledger, and the ready-marker-with-no-vendor-rows case.

### Surfaces in scope
- python/larch/report/progress_report.py
- python/larch/review/plan_review_loop.py
- python/larch/report/timing.py
- python/tests/review/test_plan_review.py

### Open questions
- None.
