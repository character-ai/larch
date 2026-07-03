# Review Round 2

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Clean rebases still invalidate the guidelines note
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: A clean rebase that leaves the implementation diff unchanged still drops the architectural-guidelines note, and the related tests continue to encode “rebased=True => invalidate” instead of preserving a valid pinned note when nothing changed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Successful rebase fakes return an impossible shape
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: Several successful rebase fakes still return `None`, but production now reads `result.rebased`, so rebase-path tests can crash with `AttributeError` before they reach their assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


