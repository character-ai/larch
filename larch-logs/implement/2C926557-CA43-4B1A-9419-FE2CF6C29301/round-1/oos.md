### FINDING_3: [OUT_OF_SCOPE] Mixed post-merge evidence may still route through preterminal recovery
- **Reviewer(s)**: cursor-specialist-edge-cases, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Confirmed merge plus `postmerge-flush` plus a real failure marker and stale `preterminal-outcome` evidence can still hit `_ship_refresh_preterminal_stall`, emit `step8-shippr`, and attempt reship on the merged PR. The classifier should ignore preterminal-outcome recovery matching when terminal post-merge failure evidence is present, while preserving failure visibility through a non-pre-merge recovery route.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_4: [OUT_OF_SCOPE] Operator-action classifier may not suppress terminal reporting
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: major
- **Concern**: `FAILURE_CLASS=operator-action` does not appear to wire `compose-report` to `skipped_operator_action`; only a root-cause verdict of `operator-action` does so. Expected post-merge cleanup may still reach terminal-failure filing unless Step 18a writes `verdict=operator-action`. Skip or downgrade terminal reporting for `MATCHED_CLASSIFIER_PATTERN=postmerge-flush-expected`, or document the mandatory orchestrator mapping in `stall-recovery.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### FINDING_5: [OUT_OF_SCOPE] Detail-log-only evidence lacks a dedicated regression fixture
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Positive `postmerge-flush` tests use `NOTE=` in `ship-pr-state.sh` rather than failure-detail-log KV evidence. A regression in detail-log-only evidence paths might not be caught. Add a fixture with `--failure-detail-log` containing `REFRESH_COMMITTED=false REASON=preterminal-outcome` plus terminal `MERGE_RESULT` in state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
Vote tally: YES=2 NO=1 JUDGE_ERROR=0 Result=accepted Fileable=false
