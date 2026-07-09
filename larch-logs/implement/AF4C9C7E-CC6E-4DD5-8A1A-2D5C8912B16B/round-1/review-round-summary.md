# Review Round 1

- Mode: `diff`
- 3 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: comment parsing misses later suppressions and delimiter edge cases
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Comment parsing is too shallow: it can misclassify prose that merely mentions suppression keywords, stop after the first suppression-like chunk in a `;`-delimited comment, truncate reasons at embedded `#`, and miss comma-separated pyright disable clauses on the same line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_3: `--initial-reason` should fail closed on existing baselines
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: `--initial-reason` is still applied when a baseline file already exists, so a normal `--write` regen can silently seed new findings instead of failing closed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Only honor `--initial-reason` when bootstrapping a missing baseline file; otherwise fail on any live finding without a preserved reason.
  - From codex-specialist-testing: Only honor initial_reason when bootstrapping a missing baseline, or reject it when the baseline already exists


### FINDING_7: baseline write errors escape `BaselineError`
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: `baseline_path.write_text` can raise directly, so permission or disk-full failures will surface as tracebacks instead of exiting 2 through the normal baseline error path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.


