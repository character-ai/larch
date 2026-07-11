# Review Round 2

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Attempt-1 terminal failures skip the required retry
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: When attempt 1 ends with missing terminal identity or missing assessment envelope—such as a child crash, timeout, or `DEAD` job—the adapter can publish attempt-2 fail-closed without starting the contracted retry. Missing identity must be distinguished from explicit non-empty identity drift: missing identity after a seeded attempt-1 launch should retry, while mismatched identity should start a fresh attempt 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Treat missing attempt-1 assessment identity as retryable; distinguish from identity drift; add harness coverage
  - From dyn-dyn-bgjob-identity: In `handle_terminal_outcome`, when both terminal identity fields are empty and `TERM_ATTEMPT` is `1` or empty, set `HANDLE_ACTION=retry`. Reserve `fresh-identity` for non-empty mismatched identity, and only publish terminal `fail-closed` after an actual attempt-2 run fails or validation proves attempt 2.


### FINDING_2: Fail-closed publication can emit `BGJOB_RC=0`
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-bgjob-identity
- **Severity**: major
- **Concern**: `publish_fail_closed_terminal` can preserve or copy a zero or empty `BGJOB_RC` from a malformed prior envelope, producing `ASSESSMENT_STATUS=fail-closed` with `BGJOB_RC=0` and violating downstream fail-closed routing expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Coerce empty or zero rc to a non-zero adapter failure code when publishing fail-closed and cover it in the harness.
  - From dyn-dyn-bgjob-identity: When publishing fail-closed, coerce `rc` to a non-zero value if it is empty or `0` (for example `timeout` when `TERM_BGJOB_RC=timeout`, otherwise `1`), and do not copy a zero `BGJOB_RC` from a stale result file into a newly published fail-closed envelope.


### FINDING_3: Completed rejoin emits insufficiently validated terminal results
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The completed rejoin path can emit a cached `result.env` without requiring terminal validation, including required assessment fields, terminal status, and `BGJOB_STATUS=DONE`. An identity-matched but incomplete or non-terminal envelope can therefore exit successfully instead of being normalized to fail-closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Require DONE for accepted terminal envelopes; treat DEAD, errors, missing status, and malformed output as retryable on attempt 1 or fail-closed on attempt 2.


### FINDING_4: Assessment harness lacks required identity-drift and dead-job coverage
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The harness does not cover stale `HEAD_SHA`, `BASE_REF`, and `DIFF_FINGERPRINT` changes, input drift between attempts, or live/completed `DEAD` results without a usable envelope. Retry-budget resets, stale-result acceptance, and missing-envelope handling can regress without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Add deterministic dead-no-envelope and per-field identity-drift fixtures, asserting one retry for the former and a new attempt 1 for the latter.
  - From cursor-specialist-testing: Add focused harness cases for each missing contract path
  - From codex-specialist-testing: Add deterministic mutations for every identity field before terminal and retry handling, plus a DEAD-without-envelope case; assert stale work clears and restarts at attempt 1.
