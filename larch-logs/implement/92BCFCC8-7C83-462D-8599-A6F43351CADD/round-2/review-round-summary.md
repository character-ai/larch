# Review Round 2

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Decompose dependency migration omits operator authorization
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-cas-mutations
- **Severity**: major
- **Concern**: `/design` dependency migration invokes `block-issue` without `--operator-invoked`, causing blocked-by writes to fail authorization.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-cas-mutations: Address the concern above.


### FINDING_2: Triage and dependency regression coverage is incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Required tests are missing for unavailable-main evidence gaps, evidence truncation, duplicate/already-fixed success paths, external codex-model-readonly probes, idempotency, and dependency precondition rejection paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Idempotent triage updates incorrectly stop dependency processing
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: A verified no-op triage update emits `ISSUE_UPDATED=false`, causing later dependency work to be skipped on retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_9: Combine-issues caller omits operator authorization
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The combine-issues `block-issue` caller lacks `--operator-invoked`, so approved dependency writes fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_10: EXIT_REDACTION sanitation failures lack regression tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Malformed triage artifacts and failed post-redaction verification lack tests ensuring fail-closed behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_11: Protected markers can be hidden inside apparent triage blocks
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Protected-marker detection removes the apparent triage block before scanning it, allowing nested untrusted `larch:plan` markers to be overwritten.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_12: Existing dependency edges can fail unchanged-timestamp verification
- **Reviewer(s)**: dyn-dyn-cas-mutations
- **Severity**: major
- **Concern**: A relation that already exists can be treated as failure when `updatedAt` does not advance, breaking retry and resume paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-cas-mutations: Address the concern above.
