### FINDING_3: Forked assessment materialization uses mismatched base refs
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: Forked runs write assessment outcomes against `origin/main` but the ship gate reads against `upstream/main`, dropping unavailable diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Thread `forked_target` through assessment materialization and align `base_ref` in all read/write paths; add fork-mode gate refresh test


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_14: [OUT_OF_SCOPE] Coordinator detail output is rejected by the adapter
- **Reviewer(s)**: dyn-dyn-fd-lifecycle
- **Severity**: minor
- **Concern**: On coordinator failure, `ARCHITECTURAL_ASSESSMENT_DETAIL` is emitted but the adapter accepts only status and results rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-fd-lifecycle: Address the concern above.
Vote tally: YES=3 NO=0 JUDGE_ERROR=0 Result=accepted Fileable=false
