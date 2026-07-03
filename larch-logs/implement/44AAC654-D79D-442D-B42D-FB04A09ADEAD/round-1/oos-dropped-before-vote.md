### OOS_1: [OUT_OF_SCOPE] clarify reuse tests miss failure-mode coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-publish-lifecycle
- **Severity**: important
- **Concern**: The reuse coverage only exercises the happy-path cancelled-clarify case; failed-clarify and clarify upsert-failure modeling are missing, so the file-exists fast path can regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Add test mirroring cancelled-clarify reuse with SUMMARY_OUTCOME=failed-clarify.
  - From codex-specialist-testing: Parametrize the reuse test over cancelled-clarify and failed-clarify
  - From dyn-dyn-publish-lifecycle: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] local final-summary render ignores upsert failure
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-publish-lifecycle
- **Severity**: nit
- **Concern**: The local render path can report success even if `upsert_final_summary_from_disk` failed, leaving the tracking comment stale while the summary workflow appears complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-publish-lifecycle: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] terminal RECOVERY_BRANCH publish coverage is missing
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-publish-lifecycle
- **Severity**: important
- **Concern**: The terminal publish/recovery path is not exercised end-to-end for `RECOVERY_BRANCH`, so parsing regressions or missing execution-issues warnings could slip through while the terminal path still completes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Mocked publish helper never exercises stdout parsing for recovery branch Seed terminal publish stdout with RECOVERY_BRANCH and assert non-zero rc without completion sentinel
  - From cursor-specialist-testing: Add RECOVERY_BRANCH case and assert execution-issues.md warning text.
  - From codex-specialist-testing: Add a test that emits PUBLISH_OK=true and RECOVERY_BRANCH from log_publish_main and asserts completion is blocked
  - From dyn-dyn-publish-lifecycle: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] log_publish render failure still reports success
- **Reviewer(s)**: dyn-dyn-publish-lifecycle
- **Severity**: important
- **Concern**: `log_publish_main` can emit `PUBLISH_OK=true` after a pre-copy render failure, which weakens the downstream contract and can leave callers with no valid summary to upsert.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-publish-lifecycle: Treat pre-copy render failure as publish failure (`PUBLISH_OK=false`, non-zero exit or explicit failure KV) unless a validated non-empty `final-summary.md` was just written for the current outcome/run id; do not emit success when render failed.

