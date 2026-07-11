# Review Round 2

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Dry-run reads the body file before returning
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing, cursor-specialist-testing
- **Severity**: major
- **Concern**: `issue create-one --dry-run` reads and redacts `--body-file` before producing its offline preview. Missing or unreadable body files can therefore make dry-run fail, violating the zero-body-file-work contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_2: Session-backed create-one omits authorization inputs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: Session-backed `create-one` calls `check_live_mutation_auth` without the active `run_id` and trusted session root. Valid `/design` and `/implement` contexts therefore fail authorization before filing, while callers may be tempted to fall back to `--operator-invoked`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-auth-boundary: Address the concern above.


### FINDING_3: OOS filing omits authorization inputs
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-edge-cases, dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: OOS `_file()` performs the live-mutation authorization check without the active `run_id` and trusted temporary directory. Authorized Step 9a.1 sessions are rejected before GitHub work, blocking legitimate OOS filing and nested issue creation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-auth-boundary: Address the concern above.


### FINDING_5: Session authorization does not require a canonical session root
- **Reviewer(s)**: dyn-dyn-auth-boundary
- **Severity**: major
- **Concern**: `check_live_mutation_auth` validates that the context file’s parent equals `trusted_root`, but does not require that root to be an approved larch session temporary directory. Any writable directory can therefore become a self-declared trusted root when marker lines are planted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-auth-boundary: Address the concern above.


### FINDING_7: Refusal coverage is missing from the shell harness
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The cross-repository shell harness lacks cases for missing, invalid, ambient-only, and test-denied mutation contexts. Authorization regressions could therefore pass without proving `mutation-refused` status and zero GitHub subprocesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_8: Design reconciliation lacks real authorization-boundary tests
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Salvage reconciliation tests monkeypatch the GitHub seam instead of exercising the real authorization boundary. Unauthorized reconciliation could reach GitHub, and authorized reconciliation remains unverified end to end.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
