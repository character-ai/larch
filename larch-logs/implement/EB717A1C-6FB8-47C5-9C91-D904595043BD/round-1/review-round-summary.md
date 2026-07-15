# Review Round 1

- Mode: `diff`
- 6 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_2: Tracked symlinks abort discovery
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-occurrence-baseline
- **Severity**: major
- **Concern**: Tracked Python symlinks are rejected during discovery before source filtering, changing legacy behavior from skipping symlinks to exiting 2 for check and write runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-occurrence-baseline: Address the concern above.


### FINDING_5: Root-level Python files are omitted
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: `python/**/*.py` excludes files directly under `python/`, narrowing discovery relative to the legacy scope and omitting those files from checks and baseline regeneration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Missing symlink regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The rewritten rule tests lack coverage proving that tracked symlinks are ignored in check and write paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Missing unreadable-input rule coverage
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: minor
- **Concern**: The rule-level tests do not cover unreadable in-scope tracked files exiting 2 with a deterministic diagnostic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_10: Test-support files are not excluded
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Non-test-named files under `python/tests/support` can be loaded by the production filter, allowing malformed or unreadable helpers to break linting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_11: Baseline paths accept empty components
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: minor
- **Concern**: Baseline validation accepts repeated path separators such as `larch//mod.py`, allowing malformed rows to be silently discarded during clean writes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
