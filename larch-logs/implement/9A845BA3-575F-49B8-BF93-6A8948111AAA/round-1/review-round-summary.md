# Review Round 1

- Mode: `diff`
- 14 accepted, 0 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Nonzero log-publish failures are reported as success
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: A nonzero log-publish result with a recovery branch can be treated as completed and produce overall success when `PUBLISH_OK=false`. All nonzero subprocess results should remain failures while preserving recovery identifiers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_2: Failed reconciliation permanently suppresses retries
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness
- **Severity**: major
- **Concern**: A reconciliation-failed sentinel is treated as terminal. If commenting succeeds but closing fails, later approved invocations skip reconciliation and leave the report open. Only successfully reconciled state should suppress retries; failed reconciliation must remain retryable and idempotent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Validated design publish identifiers do not reach reports
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Validated design issue, recovery branch, and PR URL identifiers are dropped during classification or report rendering. Recovery reports can therefore show unknown branch and PR metadata despite valid publish-tail state. Thread the identifiers through terminal state and classification, and prefer them during report rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_5: Rc-5 status artifacts omit progress and lack write verification
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Step 5c rc-5 status artifacts omit new publish provenance and progress fields, and the write is not verified as non-empty or complete. Persist validated progress fields and re-read the guarded artifact before terminal staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_6: Publish tail logs are absent from the sensitive corpus
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: Standalone publish stdout, stderr, and nested phase tail files are not included in the sensitive corpus, so secrets or tracebacks in those files may escape redaction before terminal report filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Rc-source provenance can be overwritten by traceback heuristics
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: The rc-5 path can replace a checkpointed `PUBLISH_RC_SOURCE` with a traceback-substring heuristic, mislabeling returned rc-5 failures as exception-sourced. Preserve the current-attempt environment value when proven and use the heuristic only when the key is absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_8: Tail persistence errors can bypass rc-5 terminal staging
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Read or atomic-write failures while persisting publish tails can escape the rc-5 recovery path, causing raw captures to be deleted and leaving no safe terminal diagnostic. Handle per-tail I/O errors, preserve available content, record an execution issue, and continue with generic terminal staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_9: Salvage reconciliation trusts unvalidated publish state
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Salvage reconciliation hand-parses publish result state without sufficient validation. Stale or duplicate-key data can falsely satisfy progress gates and close a report without current salvage evidence. Use the guarded parser, reject unsafe or duplicate state, and require current salvage provenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_10: Step 5c failure-path integration coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Lifecycle tests do not cover nested rename or log-publish stderr when outer stderr is empty. These paths, including exception-mapped rc-5 behavior, can regress without preserving nested diagnostics in auto-filed reports.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Publish-result invalidation failure lacks focused coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no focused test proving that a failed pre-invocation publish-result invalidation prevents publish invocation, avoids stale progress, and still performs safe terminal staging.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Stale rc-4 refusal state lacks retry coverage
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no two-attempt test proving that stale rc-4 refusal state is invalidated before retry, with a tombstone, a new `PUBLISH_ATTEMPT_ID`, and recoverable classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_13: Shard assignments contain an orphaned publish test
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `python/shard-assignments.json` retains an assignment for a removed or renamed publish test, which can break shard or artifact-cleanliness workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_14: Terminal-state validation lacks coverage for publish metadata
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: `validate_terminal_state` tests do not cover the new `PR_URL`, `RECOVERY_BRANCH`, and publish-progress fields, leaving malformed values and valid GitHub URLs insufficiently tested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_15: Salvage reconciliation lacks deduplication and close-verification tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Salvage tests do not cover dedup-report targeting or post-close verification mismatches, so reconciliation could close the wrong issue or report success while the GitHub issue remains open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
