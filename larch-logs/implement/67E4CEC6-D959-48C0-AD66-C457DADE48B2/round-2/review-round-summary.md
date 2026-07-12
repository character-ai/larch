# Review Round 2

- Mode: `diff`
- 9 accepted, 6 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Ground-truth ended-at fallback semantics
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: major
- **Concern**: Ground-truth ended-at lookup now falls through to alternate manifests after invalid preferred timestamps, changing legacy first-manifest behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


### FINDING_7: Unsafe corpus roots are accepted
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Corpus-root validation accepts symlinked or non-directory roots, allowing scanners to consume runs outside the intended repository corpus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_8: Validated recursive helpers lack provenance enforcement
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: Recursive validated helpers do not establish that their input directory came from safe direct-child selection, allowing callers to scan broader corpus roots.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_9: Run-log lint skips unsafe tracked sources
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: major
- **Concern**: The walker lint silently skips tracked symlinked, non-regular, unreadable, or otherwise unscannable Python sources, allowing bypasses to pass the ratchet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_10: GC marker can precede failed post-slim measurement
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `_slim_dir` writes `gc-slimmed` before a potentially failing final byte measurement, leaving inconsistent partial state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_13: Validated file iteration can yield FIFOs
- **Reviewer(s)**: codex-specialist-edge-cases
- **Severity**: minor
- **Concern**: Validated file iteration does not require regular non-symlink files, so a FIFO at a canonical path could block scanner reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_14: Escape-symlink traversal ignores walk errors
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Recursive escape-symlink checks silently skip unreadable descendants, allowing GC decisions based on incomplete inspection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_15: Annotated corpus aliases evade lint tracking
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: minor
- **Concern**: The lint ratchet does not track `AnnAssign` corpus aliases, allowing raw corpus traversal through annotated assignments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_21: GC passes the wrong containment root
- **Reviewer(s)**: codex-specialist-testing, dyn-dyn-corpus-policy
- **Severity**: major
- **Concern**: GC passes the overall logs root instead of the per-skill parent to validated-run checks, causing clean runs to be classified as escaping and skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-corpus-policy: Address the concern above.
