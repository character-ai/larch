# Review Round 2

- Mode: `diff`
- 3 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Frozen fallback does not prove plan-path changes are owned by the current run
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-baseline-provenance
- **Severity**: major
- **Concern**: Frozen fallback can count pre-existing porcelain dirt, same-session pre-seeded provenance, or unrelated upstream changes in `anchor_head..HEAD` as implementation coverage. This can clear `disposition_required` without the current `/implement` run changing the path. Persist per-path provenance and state signatures only from verified fallback observations in this run, and reject or prune unverified anchor attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-baseline-provenance: Record plan paths only when first seen during fallback while `session-id` is bound, or require an explicit run-owned marker (manifest/dispatcher commit range) before porcelain alone can satisfy coverage.


### FINDING_4: Missing regression coverage for external commits and provenance-backed reverts
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Existing tests do not exercise frozen fallback after an external implementation commit or a session-bound commit-then-revert sequence. The stale-revert test omits the session ID and commit simulation, so it does not validate anchor provenance, pruning, or clean-tree recomputation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Add external-complete frozen-fallback test and provenance revert test with session-id.
  - From cursor-specialist-edge-cases: Add session-id, HEAD advance, diff_paths commit simulation, revert commit, and assert anchor-based coverage clears the plan path.
  - From codex-specialist-testing: Add session-id simulate commit via head and diff_paths then revert that removes the path from anchor_head..HEAD and assert the plan path is uncovered after recompute or record_disposition.


### FINDING_5: Frozen fallback silently drops committed coverage when the anchor diff fails
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-baseline-provenance
- **Severity**: major
- **Concern**: A non-zero `git diff anchor_head..HEAD` result is ignored in frozen fallback, unlike live-base handling. Rebase or history rewriting can therefore erase committed coverage silently and produce stale or false disposition results. The failure should raise `ShipError` or provide an explicit diagnostic while preserving only verified provenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Raise ShipError on non-zero anchor diff in frozen fallback or re-pin anchor_head after rebase with an explicit diagnostic.
  - From cursor-specialist-testing: Raise ShipError or emit a diagnostic when anchor-range diff fails while fallback provenance is active.
  - From dyn-dyn-baseline-provenance: Raise `ShipError` on non-zero `anchor_head..HEAD` diff failures, matching live-base behavior at `527-529`, so coverage recomputation fails loudly rather than returning an empty touched set.
