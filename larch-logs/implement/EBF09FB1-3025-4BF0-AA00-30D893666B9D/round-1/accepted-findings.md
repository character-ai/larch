### FINDING_4: phase-3-only WARN test should assert zero phase-2 relaunches
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The phase-3-only WARN threshold test does not assert `PHASE2_RELAUNCH_COUNT=0`, so accidental inclusion of grouped phase-2 relaunches in unrelated runs may not fail that scenario.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_8: design dispatcher docs do not describe combined WARN metering
- **Reviewer(s)**: dyn-combined-fallback-consumers-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-review-panel.md` still documents degradation from phase-3-only `FALLBACK_COUNT` and does not describe `PHASE2_RELAUNCH_COUNT` or that `WARN=cost-fallback-exceeded-threshold` now uses the combined count.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-combined-fallback-consumers-output.txt: Address the concern above.


