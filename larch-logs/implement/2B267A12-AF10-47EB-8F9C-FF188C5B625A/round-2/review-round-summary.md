# Review Round 2

- Mode: `diff`
- 7 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Owner identity capture failures become unowned jobs
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: A stale `LARCH_CLAUDE_PID` can make owner capture fail, after which the daemon runs without orphan detection. Propagate capture failures in both constructors; use `getppid` only when the variable is unset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_2: CI-fixer integration scenarios were removed
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: major
- **Concern**: The thin CI-fixer harness no longer covers crash, salvage, hostile integration, and salvage-reship behavior. Port the removed scenarios into adapter-level tests and run them from the wrapper harness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_3: Checks adapter lacks required behavioral coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Tests do not cover stale results, unsafe reattachment, live reattachment, identity drift, atomic publication, and related checks-adapter paths. Restore targeted coverage for these regressions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_5: Step 5 harness omits review and resume lifecycle tests
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The Step 5 harness selects only a subset of contract tests, leaving adapter reuse, liveness, stall, review, stale-result, and resume behavior unverified. Expand it to the full planned Step 5 coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: Repeated CI-fixer starts can lose pending finalization
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: After a salvage lane changes HEAD, repeated CI-fixer entry can derive a duplicate lane and lose the original finalization step. Reuse pending launches or completed results before deriving a new launch, and record lineage before creating another one.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_10: Parent-mode Step 5 resume behavior lacks tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Parent-mode reuse, stale clearing, and checks-site forwarding for Step 5 resume envelopes are untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Step 6 stale completed-result recovery lacks coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Changed worktrees can leave stale Step 6 output without tested recovery before relaunch. Add parent-mode stale-result clearing and fresh-launch coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
