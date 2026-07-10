# Review Round 1

- Mode: `diff`
- 8 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Exit-zero no-op incorrectly stops the tier waterfall
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: A tier exiting successfully with no validated repository delta is treated as useful work. The waterfall stops, returns `no-changes`, and fails to try later configured tiers. Useful work should be determined from validated repository changes rather than launcher exit status.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Classify useful work only from a validated repository delta; record a zero-exit no-op and continue to `next_untried_tier`.
  - From cursor-specialist-edge-cases: Base usefulness solely on validated snapshot deltas; ledger no-op tiers and continue selection via `next_untried_tier()`.
  - From codex-specialist-edge-cases: Capture and compare staged and unstaged content identities per path.
  - From codex-specialist-testing: Derive useful_delta only from validated repository changes and add a zero-exit no-op advancement test.
  - From dyn-dyn-waterfall-state: Define `useful_delta` only from validated repository deltas (`useful_delta_paths`, HEAD movement, or index changes). Treat exit 0 with no delta as `no-useful-delta`, append the ledger row, and continue to `next_untried_tier()` without breaking the loop.


### FINDING_2: Repository snapshots omit staged and index-only changes
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: Snapshot state records worktree content but not staged/index content. Index-only edits, including changes to already-dirty paths, can therefore be misclassified as no useful delta and discarded from waterfall decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Compare staged and unstaged per-path content identities, including an index digest, and fail closed on capture errors.
  - From cursor-specialist-edge-cases: Capture staged and unstaged content identities per path in `_RepoPathState` and compare full state against per-attempt baselines.
  - From codex-specialist-edge-cases: Capture and compare staged and unstaged content identities per path.
  - From dyn-dyn-waterfall-state: Include per-path staged and unstaged content fingerprints (for example via `git diff` / `git diff --cached` hashes) in `_RepoPathState`, and use those fields in `_snapshot_delta_paths()`.


### FINDING_3: HEAD movement is not included in useful-delta classification
- **Reviewer(s)**: dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: A tier can commit fixes, exit non-zero, and leave a clean worktree while still changing `HEAD`. Because usefulness is based only on snapshot paths, committed work can be treated as no useful delta and lost from the outcome.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-waterfall-state: Capture `attempt_head` before each launch and treat `HEAD` movement (plus existing snapshot checks) as useful delta before deciding whether to continue the waterfall.


### FINDING_4: Structural dispatch failures are routed to terminal stall
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Post-dispatch structural failures such as forbidden-path, `git add`, or `git commit` integrity violations become `dispatch-failed` and route to `NEXT_ACTION=stall`, preventing the intended main-agent recovery path. Structural failures should map to `main-agent-required` or `main-agent-edit`, while stall remains limited to the named non-structural exhaustion cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Map closed structural `failure_reason` tokens to `main-agent-required` or `main-agent-edit` in handle/repair routing.
  - From cursor-specialist-edge-cases: Add a structural `failure_reason` allowlist or emit `main-agent-required` with escalation ledger fields; keep stall limited to the three named non-structural exhaustion tokens.


### FINDING_5: Anomalous tier outcomes lack durable execution-issue records
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-waterfall-state
- **Severity**: major
- **Concern**: Timeout, authentication, missing-binary, launcher, and related anomalous outcomes are recorded only in the tier ledger’s `execution_issue_kind` field. They do not produce bounded categorized execution-issue evidence associated with the isolated attempt, so run-log audit surfaces cannot reliably observe them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Append bounded execution-issue records from isolated attempt logs on anomalous classifications.
  - From codex-specialist-correctness: Write bounded categorized execution-issue records associated with each isolated attempt artifact before advancing.
  - From cursor-specialist-edge-cases: Append bounded execution-issue entries tied to attempt-scoped redacted logs through the existing execution-issue mechanism.
  - From codex-specialist-edge-cases: Append bounded redacted categorized execution-issue entries for every anomalous attempt.
  - From codex-specialist-testing: Write bounded redacted execution-issue records through the existing mechanism and test their category and payload redaction.
  - From dyn-dyn-waterfall-state: After classifying a non-recoverable tier anomaly, write a bounded execution-issue entry tied to the isolated attempt directory (reusing the existing execution-issues mechanism) in addition to the ledger row.


### FINDING_6: Attempt-log paths can expose unredacted launcher output
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Failing launcher output may contain secrets, while returned log or tail paths can expose raw attempt logs beyond the intended boundary. Attempt logs must be redacted and validated before their paths flow outward.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Create and validate redacted attempt-local logs and return only those paths; fail closed on redaction failure.


### FINDING_7: Claude coder log path is inconsistent with the expected artifact name
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The Claude tier populates `coder_log_path` with `claude.log` rather than the expected `claude-lint-fix.txt`, leaving repair-loop output references missing or incorrect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Use per-tier `log_name` when populating `coder_log_path`.


### FINDING_8: Focused test suite is failing and lacks required waterfall coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: `python/tests/implement/test_checks.py` has reported failures and incomplete coverage for no-op advancement, budget exhaustion, final-tier eligibility, isolation artifacts, tier-ledger rows, execution-issue evidence, terminal stall envelopes, and ship-pr handoffs. Stubbed git sequences and launcher assertions do not match the per-attempt behavior, so regressions are not reliably verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update tests to stall contract; add plan-listed integration tests; extend `StubRunner` git sequences.
  - From cursor-specialist-testing: Extend `StubRunner` for per-tier capture; update routing expectations; run full `test_checks.py` to green.
  - From cursor-specialist-testing: Implement plan testing strategy items and update `scripts/test-implement-structure.sh` plus `scripts/test-implement-fence-shape.sh`.
  - From codex-specialist-testing: Add a zero-exit no-op advancement test.
  - From codex-specialist-testing: Write bounded redacted execution-issue records through the existing mechanism and test their category and payload redaction.
