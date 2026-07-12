# Review Round 2

- Mode: `diff`
- 6 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_4: unsafe result paths permit relaunch
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Unsafe result artifacts are treated as absent, allowing a fresh launch that later cannot publish its result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_5: merge-env publication is not descriptor-safe
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Daemon merge-env publication can follow a same-UID symlink swap and read rows from an unintended file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_6: expired verified-dead restart lacks coverage
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The expired entry path where both processes are verified dead lacks a test proving stale-entry removal and exactly one fresh launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: identity mismatches are treated as proven dead
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: An expired identity-mismatched entry may be cleared and relaunched while a child remains live after exec or process-group changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_12: registry-root lock is not pinned
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: major
- **Concern**: A same-UID symlink swap can redirect lock creation and chmod outside the registry root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_14: combined merge-result publication lacks coverage
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: minor
- **Concern**: Publication of preseeded merge rows together with child-written rows lacks regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
