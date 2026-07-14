# Review Round 1

- Mode: `diff`
- 7 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_3: Baseline component lstat errors are uncaught
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Permission or other non-`FileNotFoundError` lstat failures can escape as uncaught `OSError` instead of producing `ScanError` and exit 2 in check and write modes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Catch non-FileNotFoundError OSError in the shared validation helper and raise ScanError; add check and write regression coverage.
  - From codex-specialist-edge-cases: Convert non-FileNotFoundError OSError values to ScanError; no sibling new direct baseline lstat call exists.


### FINDING_4: Required guarded-write and read-back tests are missing
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Write-mode coverage does not verify symlink targets, invalid parents, malformed rows, destination safety, read-back failures, exact bytes, prior-baseline preservation, or post-publication no-rollback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Add focused write-mode tests that assert exit 2 and the required pre- and post-publication file-state contracts.
  - From cursor-specialist-edge-cases: Add the plan-listed tests; prioritize monkeypatched read-back mismatch after trusted_atomic_write asserting exit 2 and no false success.
  - From codex-specialist-edge-cases: Add focused tests that assert exit 2, unchanged pre-publication state, and no rollback after publication.
  - From codex-specialist-testing: Add write-mode tests for all guarded destinations read-back failures exact bytes and unchanged prior baselines.


### FINDING_5: Step 4 dispatcher change violates the planned diff scope
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing
- **Severity**: major
- **Concern**: `dispatch_commit_route.py` changes fall outside the two firm headings and widen Piece 2’s blast radius.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Move the dispatcher change into a separate change.
  - From cursor-specialist-testing: Revert dispatch change or split to separate PR and update plan.


### FINDING_6: Noop breadcrumb test still expects stdout
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The noop commit-route test still checks stdout even though the breadcrumb now belongs on stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Assert breadcrumb on captured.err and keep stdout clean
  - From codex-specialist-testing: Assert against captured.err and verify stdout lacks the breadcrumb.


### FINDING_7: Symbol-metric baseline cases lack regression coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Equal or reduced metrics, invalid metric fields, and duplicate symbol identities are not tested, leaving baseline projection and metric comparisons vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add parametrized malformed or duplicate baseline tests monkeypatch read-back failure tests and equal or reduced metric EXIT_CLEAN cases
  - From codex-specialist-testing: Add parameterized run_rule tests for each required symbol-metric path.


### FINDING_8: Generic validation and strict-stale precedence lack tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Required malformed-baseline validation ordering and strict-stale behavior when new findings coexist with stale rows are unverified, including exit-code and stream contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add the plan-listed tests; prioritize monkeypatched read-back mismatch after trusted_atomic_write asserting exit 2 and no false success.
  - From cursor-specialist-testing: Add strict_stale case with both new finding and stale row assert exit 2 and stream behavior
  - From codex-specialist-testing: Add focused tests for the required generic validation and stream-contract cases.


### FINDING_9: Baseline success does not assert canonical serialized bytes
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: The write-success test parses JSON and can accept semantically equivalent but non-canonical output instead of verifying exact serialized bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Compare baseline.read_text to exact _serialized_baseline output. 
