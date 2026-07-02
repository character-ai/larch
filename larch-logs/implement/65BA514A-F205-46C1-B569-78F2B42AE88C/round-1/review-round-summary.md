# Review Round 1

- Mode: `diff`
- 1 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_3: correctness: UnicodeDecodeError aborts drift recovery
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: latent
- **Concern**: Drift recovery catches only `OSError` when reading the staged assessment. A malformed non-UTF-8 staged assessment raises `UnicodeDecodeError`, aborting ship instead of falling back to the drop notice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


