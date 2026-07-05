### FINDING_1: [OUT_OF_SCOPE] ship recovery should assert a DONE outcome line
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Ship-recovery coverage only checks that the old lowercase stalled text is gone; it does not verify the recovered output explicitly includes a DONE outcome line, so a partial recovery could still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_2: [OUT_OF_SCOPE] reconciliation should reuse the shared outcome-display mapper
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Reconciliation hardcodes DONE instead of using the shared outcome-display mapping, so future mapper changes could make reconciliation diverge from normal rendering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_3: [OUT_OF_SCOPE] degraded /design fallback should explicitly render STALLED
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-testing
- **Severity**: minor
- **Concern**: The degraded /design fallback is not asserted against a stalled render, so a regression could leak raw stalled output or miss the STALLED outcome entirely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Add a failing-render test for outcome stalled and assert the fallback body contains - **Outcome**: STALLED


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] legacy reconciled summaries may miss an Outcome bullet
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Older reconciled summaries can still be missing an Outcome bullet entirely, which leaves downstream parsers unable to classify those runs with the new bullet-based logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

