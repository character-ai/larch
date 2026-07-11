### [rejected] FINDING_1

**Rejected subtype:** dismissed (0 YES)

### FINDING_1: Frozen fallback can miss committed implementation when first computed on a clean tree
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-baseline-provenance
- **Severity**: major
- **Concern**: In frozen fallback, the first session-bound recomputation can pin `anchor_head` at the already-advanced `HEAD` when porcelain is clean. Committed plan-path work is then absent from `anchor_head..HEAD`, so coverage remains incomplete or disposition state becomes stale. The anchor should be established from verified run-owned work rather than post-implementation `HEAD`, with fail-closed behavior when no valid provenance exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-baseline-provenance: Set `anchor_head` only after at least one in-scope plan path is observed in porcelain, or initialize it to the parent of the first run-owned commit touching plan paths; fail closed when frozen fallback is active, the tree is clean, and no provenance anchor exists yet.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** dismissed (0 YES)

### FINDING_3: Committed reverts can leave stale frozen-fallback coverage
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Name-only retention from `anchor_head..HEAD` does not verify the final state of fallback-observed paths. A path edited during the run and later reverted can remain marked covered even though the implementation was undone. Retained paths need signature or content-state validation so committed reverts remove coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Persist and validate per-path state signatures against worktree or HEAD state, and test distinct anchor edit and revert commits with clean porcelain status.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0
