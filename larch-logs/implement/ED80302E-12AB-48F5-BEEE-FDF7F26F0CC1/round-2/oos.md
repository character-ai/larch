### FINDING_14: [OUT_OF_SCOPE] Unrelated #2667 tests are bundled with Stage 2
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` includes unrelated #2667 structural tests on the Stage 2 branch, increasing harness time and review confusion for breadcrumb-focused changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_18: [OUT_OF_SCOPE] Source-dir session-root derivation can silently skip quiet logs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-larch-log.sh` derives session root from `dirname(source_dir)`, so a nested or unexpected `LARCH_BREADCRUMB_SOURCE_DIR` hint can skip quiet logs with silent success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] CI wait poll-budget test label is misleading
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-ci-wait.sh` has a poll-budget assertion label that implies stderr migration coverage while the test reads stdout KV, confusing future timeout-test maintenance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] Stale `emit_breadcrumb` references remain in later-scope docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Later-scope docs such as `AGENTS.md` still mention `emit_breadcrumb`, which may confuse contributors until the planned Piece 3 doc sweep.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

