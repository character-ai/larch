### [Plan Review] FINDING_4

### FINDING_4: New umbrella scope-anchor harness duplicates focused harness coverage
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic, Codex-dyn-regression-matrix
- **Severity**: important
- **Concern**: The proposed broad scope-anchor harness duplicates cases already assigned to focused per-script harnesses, increasing fixture, Makefile, and maintenance surface without a distinct contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Drop the new omnibus test-plan-review-scope-anchor.sh target; keep the focused existing harness updates plus the new marker-detector harness
  - From Codex-Pragmatic: Remove test-plan-review-scope-anchor.sh and keep the focused tests plus the new marker-detector harness
  - From Codex-dyn-regression-matrix: Drop the new broad harness, or reduce it to one end-to-end smoke only if it covers behavior not asserted by the existing per-script harnesses; keep the new detector unit test and the existing harness extensions


### [Plan Review] FINDING_8

### FINDING_8: Dedup merge order can drop tagged markers before parity
- **Reviewer(s)**: Cursor-dyn-marker-contract
- **Severity**: important
- **Concern**: The current dedup merge keeps the first Jaccard match body. If an untagged duplicate appears before a tagged one, the `[SCOPE-REDUCTION]` marker can be lost until parity fallback, making marker preservation depend on a degraded heuristic path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-marker-contract: Implement the planned tagged-wins rule inside the dedup loop (prefer tagged body or reinsert leading marker before parity) so tagged markers survive the primary path without depending on fallback


