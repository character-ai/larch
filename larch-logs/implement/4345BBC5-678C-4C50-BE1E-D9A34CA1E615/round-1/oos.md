### FINDING_1: Post-merge retry budget can be consumed by earlier transients
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing, cursor-specialist-plan-fidelity-auto
- **Severity**: major
- **Concern**: Post-merge `TRANSIENT_RETRIES` and `skip_flap_check` reuse ship-wide transient state, so a prior transient or the first stale failure after a submitted rerun can burn the retry budget and send the flow to `emergency-repair` before the merged-SHA rerun has actually settled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Use a postmerge-only retry marker or counter for the rerun budget and skip_flap_check, and cover prior TRANSIENT_RETRIES=1 in tests.
  - From cursor-specialist-testing: Use a postmerge-only retry counter or reset/isolate TRANSIENT_RETRIES at post-merge entry; add a regression test seeding TRANSIENT_RETRIES=1 before the first post-merge failure.
  - From cursor-specialist-plan-fidelity-auto: After a submitted postmerge rerun, poll until MAIN_REPAIR_RUN_ID settles or timeout; do not treat the first stale fail with TRANSIENT_RETRIES>0 as a spent retry budget.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_7: [OUT_OF_SCOPE] Already-running rerun test gap
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: minor
- **Concern**: The post-merge path still lacks an explicit test for `rerun_failed()` returning `submitted=True, already_running=True`; behavior is indirectly covered, but the dedicated case is not locked down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_8: [OUT_OF_SCOPE] Phase metadata for global transient stall seed
- **Reviewer(s)**: dyn-dyn-postmerge-retry
- **Severity**: minor
- **Concern**: When the global transient cap trips, stall metadata is always seeded as `--phase ci-initial`, even if the triggering transient came from `postmerge-push-watch`, so stall recovery can classify the failure under the wrong phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-postmerge-retry: Address the concern above.


Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false

### FINDING_9: [OUT_OF_SCOPE] Post-merge re-entry after TRANSIENT_RETRIES=1 lacks test
- **Reviewer(s)**: dyn-dyn-postmerge-retry
- **Severity**: minor
- **Concern**: The full re-entry path after a prior transient retry is not covered, so the case where `wait_main_health` runs with `skip_flap_check=True` and a second merged-SHA failure should still enter `emergency-repair` is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-postmerge-retry: Address the concern above.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### FINDING_10: [OUT_OF_SCOPE] Stale cross-references outside scoped docs
- **Reviewer(s)**: dyn-dyn-postmerge-retry
- **Severity**: minor
- **Concern**: Repository docs still point at `python/ship.py` in a few out-of-scope places even though runtime code lives under `python/larch/implement/ship.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-postmerge-retry: Address the concern above.
Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

