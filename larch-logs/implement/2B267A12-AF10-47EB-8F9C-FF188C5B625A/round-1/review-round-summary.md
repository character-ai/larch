# Review Round 1

- Mode: `diff`
- 10 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Step 5 resume emits premature completion
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: `_step5_resume_worker` emits `STEP5_REVIEW_STATUS=complete` before checks and commit-routing legs succeed, allowing failed or stalled resumes to appear complete.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-bgjob-identity: Address the concern above.


### FINDING_4: Child-output validation rejects values containing spaces
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `_stdout_is_merge_rows` rejects valid relay rows whose values contain spaces, causing ready-to-commit resume output to be discarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_8: Parent-PID owner fallback was dropped
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Converted adapters lack the prior `os.getppid()` fallback when `LARCH_CLAUDE_PID` is unset, so orphaned jobs may have no recoverable owner identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_9: Structure tests retain obsolete Bash requirements
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Implement structure tests still require retired Bash internals and fail to enforce the intended thin-wrapper and Python-owned adapter design.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Step 5 integration coverage was removed
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The Step 5 harness no longer provides equivalent coverage for launch, reuse, stall, reattachment, liveness, and merge-envelope behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_11: CI-fixer crash and salvage coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: Former Bash crash, salvage, and hostile-environment scenarios are not fully covered by Python integration tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Checks and Step 6 identity/publication coverage is incomplete
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests omit stale-result, unsafe-path, reattachment, identity-mismatch, skip, and atomic-publication cases for checks and Step 6 adapters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_16: Step 5 classifier reuse and stale-clear tests are missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Tests do not cover valid reuse, stale review-stall refusal, or safe and unsafe clearing of Step 5 results.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_17: Step 6 reattachment and atomic-publication tests are missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Step 6 lacks adapter-level tests for live reattachment, stale and matching results, skip-to-7a, and atomic identity publication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


### FINDING_18: CI-fixer reuse and crash-finalization tests are missing
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: CI-fixer tests do not cover completed-job reuse or nonzero bgjob finalization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
