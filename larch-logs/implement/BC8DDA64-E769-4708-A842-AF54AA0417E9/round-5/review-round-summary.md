# Review Round 5

- Mode: `diff`
- 4 accepted, 10 rejected (8 neutral)

## Accepted Findings

### FINDING_1: Step 5 loop lacks catch-all exception envelope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Step 5 loop mode only catches `ValueError` for preflight failures. Other exceptions (missing helper script, unexpected `OSError` during `_run_round`) can exit without emitting the mandatory `STEP5_REVIEW_STATUS` envelope, leaving `/implement` Step 5 without a terminal status and stall/handoff routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Wrap the loop (and optionally single/MAV paths) in except that emits `STEP5_REVIEW_STATUS=stall` with a stable `STALL_REASON`, then return non-zero; keep progress/done in finally.


### FINDING_11: Duplicate `SKIPPED: FINDING_N` lines not de-duplicated
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Duplicate `SKIPPED: FINDING_N` lines are no longer de-duplicated before skipped findings are counted and appended to accumulated OOS artifacts. A coder log that repeats `SKIPPED: FINDING_1` will increment `skipped_count` twice and can duplicate the same OOS block, falsely tripping the bulk-skip ratio gate or creating duplicate OOS follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Build `skip_ids` as a de-duplicated ordered list before the loop, matching the old `sort -u` behavior.


### FINDING_15: `REVIEW_AND_FIX_REVIEW_CORE_SH` env override bypasses lint and in-process path
- **Reviewer(s)**: dyn-migration-surface-output.txt
- **Severity**: important
- **Concern**: `review_core_capture()` still honors `REVIEW_AND_FIX_REVIEW_CORE_SH` by subprocess-invoking an arbitrary executable and writing its stdout to `review-core.env`, bypassing the in-process `review_pipeline.review_core()` path and the `scan_review_and_fix_review_core()` lint that only matches `review core` subprocess strings. If that env var leaks into a real `/implement` session, Step 5 review behavior becomes environment-dependent and unaudited.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-surface-output.txt: Restrict the override to an explicit test-only gate (for example `LARCH_TEST_REVIEW_CORE_OVERRIDE=1` plus pytest/harness-only documentation), or document and lint that production Step 5 must never see a non-empty `REVIEW_AND_FIX_REVIEW_CORE_SH`.


### FINDING_2: Unvalidated `LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS` can skip Step 5 envelope
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS` is parsed with bare `int()` and no validation. Invalid values like `abc` raise `ValueError` mid-loop; Step 5 exits without `STEP5_REVIEW_STATUS` while progress/done is still written in `finally`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Validate like `_skip_ratio_threshold()` with fallback and warning, or catch and emit `STEP5_REVIEW_STATUS=stall` before exit.


