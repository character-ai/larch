### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Dead DEGRADED_ROUND fallback-count branch in plan-review panel dispatch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `dispatch-plan-review-panel.sh` still checks `COMBINED_FALLBACK_COUNT > floor_half` for `DEGRADED_ROUND`, but plan-review always passes `--no-fallback` (count is always 0). Real degraded signaling relies on path-count/`ALL_SLOTS_DROPPED`; the fallback-count branch is dead and obscures triggers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

