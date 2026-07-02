### OOS_1: [OUT_OF_SCOPE] Plan-faithful CI fixer retry on transient output failures
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `acc707176` implements retry for missing or empty CI fixer output as planned: `_ci_fix_retry_reason` gates on exit 124, missing file, or zero-byte file, with `OSError` on `stat()` mapped to `missing-output` (fail-open retry); `_run_cycle` performs a single bounded retry and refreshes `launcher_exit` after relaunch; `_emit_ci_retry_warning` logs `rc` and `retry_reason` in the planned shape; the stale comment is corrected; tests cover exit-124 retry, missing/empty output retry (parametrized), and existing mocks were updated so non-transient failures with non-empty output still launch once (`test_mixed_fixable_and_unfixable_launches_claude` asserts `launch_calls["n"] == 1`); alignment with `plan_review_panel._voter_needs_retry` is correct for the dominant `#5714` path where `launch-claude-lint-fix` writes a zero-byte output file when Claude returns empty stdout, which now triggers retry.

### OOS_2: [OUT_OF_SCOPE] Run log flush commit
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: nit
- **Concern**: `6705cf6e1` — chore(larch-logs): flush run log is out of scope for code review.

### OOS_3: [OUT_OF_SCOPE] Sentinel empty-result files skip size-based retry
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Retry uses file size only; when launchers write non-zero-byte sentinel placeholders (e.g. `CLAUDE_LINT_FIX_EMPTY_RESULT\n` for parseable JSON with an empty `result`, or `CLAUDE_CI_EMPTY_RESULT` for empty-envelope failures), the new retry predicate does not fire despite semantically empty results; some `launch-claude-ci` empty-envelope failures write sentinel text with exit 1 and the lane still single-shots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Only relevant if production hits this JSON-empty branch for the same transient class as stderr-only "No messages returned from query"; if so, treat known empty-result sentinels like byte-empty or have the launcher write a zero-byte file for that case.
  - From cursor-specialist-edge-cases: Extend predicate or normalize launcher output only if run logs show this sub-mode is common.

### OOS_4: [OUT_OF_SCOPE] Preflight health failures may trigger empty-output retry
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: Preflight health failures write zero-byte output files; binary-missing (rc=127) now retries once and logs subprocess transient though failure is permanent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Exclude known health rc values from empty-output retry or detect preflight .diag markers.

### OOS_5: [OUT_OF_SCOPE] Missing retry boundary tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: Missing negative-path tests for no third retry, explicit no-retry on non-empty failure output, and no second retry after a failed retry attempt; future edits could reintroduce multi-retry or accidental retry on parse failures without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add tests for double-failure and non-empty nonzero-exit no-retry paths.
  - From cursor-specialist-testing: Add a test where both attempts return missing/empty output and assert launch_tier is called exactly twice.

### OOS_6: [OUT_OF_SCOPE] Test stubs omit output writes and launch-count assertions
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Health and parse failure stubs omit output writes so tests exercise retry-before-fail without asserting launch count; `_stub_successful_fix_until_wait` leaves output missing while resolve returns 0, so consumers implicitly depend on one retry; future regressions in retry gating on non-transient failures could slip through because tests only assert terminal STATUS/DETAIL.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Write non-empty output in stubs that model non-transient failures and assert launch_tier is called once.
  - From cursor-specialist-testing: Write minimal non-empty output in the shared stub or assert expected launch count.

