# Review Round 1

- Mode: `diff`
- 4 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_4: Occurrence baseline field variants are not validated
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Baseline rows using `pattern_name` are accepted for rules configured with `normalized_condition`, allowing legacy-schema drift and silent migration during `--write`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_5: Initial reason whitespace is not stripped
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: Padded `--initial-reason` values are persisted with surrounding spaces instead of being normalized as before.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: Tracked symlinks are not skipped on the production path
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-occurrence-baseline
- **Severity**: major
- **Concern**: A tracked symlink under `python/larch/` passes the production source filter and causes discovery to abort, whereas the legacy scanner skipped symlinks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-occurrence-baseline: Address the concern above.


### FINDING_8: Engine-backed CLI integration is not tested end to end
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: The required CLI test mocks the runner and bypasses `main`, leaving Git discovery and `ProcRunner` integration unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
