### FINDING_2: [OUT_OF_SCOPE] code-quality: CHANGELOG.md (historical entries)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Changelog records past 11→13 rebalance; not updated for 16. Readers might confuse history with current layout; changelog is historical by design. Leave as-is or add a new changelog entry on release, outside this diff’s scope.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_3: [OUT_OF_SCOPE] code-quality: docs/linting.md (LPT snippet)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Quadratic bins.index in example snippet Unchanged algorithmic style aside from bin count 13→16 Accept as pre-existing doc example debt or rewrite LPT loop in a separate change
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_4: [OUT_OF_SCOPE] code-quality: docs/linting.md:167-221 (representative)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Many reference-table `via test-harnesses-*` hints already mismatched `main`’s Makefile before this PR. Not introduced by this diff; broad pre-existing doc drift. Optional full-table regeneration from Makefile or drop hard-coded shard hints.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] correctness: docs/linting.md (various table rows)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Some via test-harnesses-N cells predated this branch and already disagreed with main Makefile assignments. Stale cross-refs pre-existed; not introduced solely by this PR’s edits to those lines. Track separately if you want the table mechanically synced to Makefile.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Doc still says test-harnesses-1 through test-harnesses-13. File not modified by this branch diff; stale after shard expansion. Update to sixteen shards in a separate doc pass if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Sibling contract still states umbrella spans test-harnesses-1..13 after branch moves to 16 shards. Same stale matrix-span risk as linting.md but file untouched by this diff/plan. Update line 27 when touching Makefile wiring docs next.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 NEUTRAL=0 Result=neutral

### FINDING_8: [OUT_OF_SCOPE] risk-integration: scripts/test-harness-shards-coverage.md:27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Contract doc still says umbrella spans shards 1–13 after Makefile moved to 16. Readers of the coverage-script contract doc get the wrong shard inventory; file not modified on this branch. Update to 1–16 when editing shard documentation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 NEUTRAL=0 Result=neutral

### FINDING_9: [OUT_OF_SCOPE] risk-integration: ~<TMPDIR>/round-1/diff.txt
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Stale partial diff for docs/linting.md A reviewer using only the cached diff can miss CI Usage 13→16 and harness-table generalizations that exist on HEAD Prefer git diff main...HEAD or a refreshed session artifact for authoritative review
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 NEUTRAL=0 Result=rejected

