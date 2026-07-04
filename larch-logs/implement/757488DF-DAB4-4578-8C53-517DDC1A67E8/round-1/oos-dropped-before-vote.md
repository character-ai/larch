### OOS_1: [OUT_OF_SCOPE] Private batch_report helper imported from final_report
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-tally-observability
- **Severity**: latent
- **Concern**: `final_report` imports the private `_count_code_review_findings` helper from `batch_report`, coupling report rendering to review internals and making later refactors harder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-tally-observability: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Corrupt or unreadable tally file still bypasses findings fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-tally-observability
- **Severity**: latent
- **Concern**: The JSONL fallback only runs when `code-review-tally.json` is absent. If the file exists but is unreadable or malformed, reports can still render `N/A` even when `review-findings-full.jsonl` has usable counts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend fallback to unreadable/malformed tally only if that failure mode is observed in live runs.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-tally-observability: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Duplicate tally-failure warnings accumulate across rounds
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: Repeated `flush_review_batches` failures can append duplicate tally-failure warnings to `execution-issues.md`, creating avoidable operator noise.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Deduplicate or include round context if warning noise becomes an operator problem.

### OOS_4: [OUT_OF_SCOPE] Findings-only warning lacks path-specific test coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no test covering `write_self_review_tally` when tally succeeds and the findings run-log write fails, so regressions in the new split warning paths could silently reintroduce duplicate logging or drop the findings-only warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add mocked test: tally rc 0, findings run-log rc nonzero; assert one findings-only Warnings entry and no tally-failure warning.

### OOS_5: [OUT_OF_SCOPE] Malformed JSONL rows lack direct unit coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: `_count_code_review_findings` skips malformed lines today, but that behavior is untested, so a future edit could start counting bad rows and skew both tally derivation and final-report fallback ratios.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add unit test mixing valid code-review rows with malformed JSON and non-dict records; assert accepted/rejected/seen_code_review.

### OOS_6: [OUT_OF_SCOPE] flush return value is still ignored
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: `_flush_review_batches_for_result` ignores the return value from `flush_review_batches`, preserving the pre-existing soft-failure behavior where Step 5 does not change exit status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] Findings flush error stays tmpdir-only
- **Reviewer(s)**: dyn-dyn-tally-observability
- **Severity**: latent
- **Concern**: `review-findings-full.flush.err` is still written only under the implement tmpdir, not copied into the committed run-root tree, so findings flush failures can still ship without a durable error artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-tally-observability: Address the concern above.

