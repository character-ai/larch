### OOS_1: [OUT_OF_SCOPE] Stall-before-PR test overfits fake flush ordering
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Stall-before-PR test depends on postbump flush consuming the first fake flush success. Future reordering of fresh-run flushes could make the test pass for the wrong reason or fail spuriously.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Pending-retry invalidate callback is untested on the force-push path
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: run_ci_fix pending-retry invalidate callback is untested on the force-push path. Pending-rebase retry could stop calling invalidate or skip refresh before force-with-lease without test detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Persist-failure test omits return and content assertions
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `_invalidate_guidelines_note` persist-failure test does not assert `warning_logged=True` or execution-issues.md content. If persist failure stops appending warnings, CI-fix callback returns False and skips the mandated pre-push flush silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Stale guidelines-note path still misses the new warning log
- **Reviewer(s)**: dyn-dyn-runlog-flush
- **Severity**: latent
- **Concern**: `_handle_stale_guidelines_note` still does not log a warning when `should_persist` is true but `maybe_persist_dropped_note_before_invalidate` returns false. That leaves `pin_warning_logged=False` on the PR-create path and can skip the new pre-`ensure_pr` flush even though a drop notice is returned for the PR body.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-flush: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Rebase-only ship_merge fallback still lacks the flush seam
- **Reviewer(s)**: dyn-dyn-runlog-flush
- **Severity**: latent
- **Concern**: Post-rebase `_invalidate_guidelines_note` remains a fallback without the new flush seam. Warnings appended there still depend on later pushes that may not refresh run logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-runlog-flush: Address the concern above.

