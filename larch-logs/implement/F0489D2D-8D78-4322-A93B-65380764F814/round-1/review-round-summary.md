# Review Round 1

- Mode: `diff`
- 5 accepted, 5 rejected (3 neutral)

## Accepted Findings

### FINDING_1: Pre-publication identity validation rejects authorized checks mutations
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-checks-identity
- **Severity**: major
- **Concern**: The child validates the final repository identity against the launch-time identity after checks and commit-route operations have intentionally changed `HEAD` or rewritten files. Successful Step 3, Step 5, or Step 6 runs can therefore be reported as `identity-integrity-failed` instead of publishing their normal result. The same issue affects legitimate pre-commit autofixes and other subprocess-attributed self-edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-checks-identity: Narrow pre-publish validation to unexpected drift only: drop post-composite HEAD equality for routes that intentionally mutate history, or re-snapshot identity after the checks leg and before commit/rebase, or skip pre-publish when the composite reports a recognized terminal success and only the expected commit/rebase legs changed `HEAD`.
  - From dyn-dyn-checks-identity: Exclude subprocess-attributed self-edits (pre-commit autofix, repair-loop tiers already logged in `self-edit-log.tsv`) from pre-publish drift detection, or recompute and persist a post-checks identity snapshot before terminal publication while keeping launch identity for stale-rejoin invalidation.


### FINDING_3: Live-registry rejoin and identity-mismatch paths lack subprocess coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The production live-registry branches for matching live rejoin and identity-mismatch fail-closed behavior are not covered by launcher-level subprocess tests. Regressions could rejoin the wrong job, silently launch a duplicate, or stop enforcing the expected exit-2 path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Add bgjob registry fixtures for matching live rejoin and mismatch exit 2 without bgjob start
  - From cursor-specialist-testing: Add subprocess live rejoin tests plus unit tests for classify_live_seed
  - From codex-specialist-testing: Add the corresponding plan-required subprocess regressions


### FINDING_4: Required launcher and Step 6 drift regressions are incomplete
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Subprocess coverage does not exercise all planned repository-drift cases across `run-step-checks.sh` and `step-6-entry.sh`, including staged changes, untracked changes, alternate-root execution, force-mode re-entry, stale cleanup, during-run mutation, and pre-publication drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add subprocess tests from the plan for live rejoin, live mismatch fail-closed, and pre-publication drift.
  - From cursor-specialist-edge-cases: Mirror Step 3 live-registry tests against step-6-entry.sh including --force-checks true
  - From cursor-specialist-edge-cases: Add subprocess test that mutates repo after checks run and before merge publish
  - From cursor-specialist-testing: Add parametrized launcher subprocess tests for each drift type on Step 3 and Step 6
  - From cursor-specialist-testing: Add child-mode test with stub checks plus post-run repo mutation asserting identity-integrity-failed
  - From codex-specialist-testing: Add the corresponding plan-required subprocess regressions
  - From codex-specialist-testing: Add the corresponding Step 6 regressions from the implementation plan


### FINDING_6: Checks-identity hostile-environment and schema cases are under-tested
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: minor
- **Concern**: Unit tests do not cover malformed environment files, duplicate keys, git failures, unreadable untracked paths, and schema mismatches, leaving identity classification behavior vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add unit tests for duplicate keys git failures unreadable untracked and schema mismatch


### FINDING_13: Successful composite publication lacks an end-to-end regression
- **Reviewer(s)**: dyn-dyn-checks-identity
- **Severity**: minor
- **Concern**: Subprocess tests do not drive the production child through a successful `checks-commit-route` or Step 6 composite and verify the published merge/result envelope, leaving the interaction between intentional mutations and publication behavior unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-checks-identity: Address the concern above.
