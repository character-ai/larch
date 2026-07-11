### FINDING_6: [OUT_OF_SCOPE] Live-base coverage can attribute unrelated upstream plan-path commits
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: Live-base mode attributes plan-path changes across `merge-base..HEAD`, including upstream or other-run commits on shared plan paths. This remains an accepted out-of-scope tradeoff but can satisfy coverage without implementation by the current run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Restrict live-base attribution to run-owned commits or manifest-declared paths.
  - From dyn-dyn-baseline-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_7: [OUT_OF_SCOPE] Relay coverage still depends on `step2-baseline.txt`
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: `_relay_scope_coverage` returns early when `step2-baseline.txt` is absent, even when live-base resolution can succeed without it. Intermediate `PLAN_COVERAGE` KVs may consequently remain stale.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Teach _relay_scope_coverage to run when live-base resolution succeeds without requiring the frozen baseline file.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-baseline-provenance: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Resumed forked runs may miss `FORKED_TARGET=true` fallback
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-baseline-provenance
- **Severity**: minor
- **Concern**: When `ship-pr-state.sh` exists but lacks a parseable `FORKED_TARGET=true`, the code does not fall back to `session-env.sh`, which can select normal `origin` mode for a resumed forked run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Fall back to session-env when ship-state exists but lacks a parseable FORKED_TARGET=true, if product intent allows.
  - From dyn-dyn-baseline-provenance: Address the concern above.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false
