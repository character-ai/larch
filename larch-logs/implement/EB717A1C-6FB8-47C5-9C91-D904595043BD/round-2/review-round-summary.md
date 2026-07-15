# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (3 neutral)

## Accepted Findings

### FINDING_2: Empty baseline semantics differ from legacy behavior
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: An existing empty baseline with a clean scan exits 0, whereas legacy behavior failed closed with a stale-baseline error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_6: Source filtering occurs after filesystem validation
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: In sparse checkouts, excluded paths reported by `git ls-files` can fail discovery before the source filter excludes them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_8: Global symlink skipping weakens existing rules
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Shared discovery skips tracked symlinks for every engine rule, allowing violating symlinked sources or baseline rows to pass silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
