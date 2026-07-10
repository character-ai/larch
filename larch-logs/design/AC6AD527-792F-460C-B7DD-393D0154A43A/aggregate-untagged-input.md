### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py
- **Concern**: Finalize-state fallback only flips STALL_TRACKING. Scenario: false
- **Proposed resolution**: If re-entry cannot unlink finalize-state.sh and falls back to rewriting only STALL_TRACKING=false, PHASE/EXIT_CODE/BAIL_REASON can still make the resumed drive normalize to stalled or bailed. Delete finalize-state.sh on re-entry, or rewrite the full neutral mid-flight shape and clear every terminal-overlay key.

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/state/_classify.py:174-177
- **Concern**: Fix 4 remedy text can trip the bare pre-commit lint classifier token. Scenario: After two failed run-log commits the plan appends a remedy mentioning `.pre-commit-config.yaml`. `_classify_text` treats any `pre-commit` substring as lint-failure and returns `RESUME_HINT=step5-review`, so a persistent hook failure at `STALL_STEP=pr-create-guideline-outcome-refresh` can be misrouted even though the new `REFRESH_SKIP_PRETERMINAL_OUTCOME` matcher only covers the pre-terminal deadlock shape.
- **Proposed resolution**: Add an early classifier branch for ship refresh stalls (for example `STALL_STEP=pr-create-guideline-outcome-refresh` and/or commit-failed refresh evidence) that returns `transient-infra` / `step8-shippr` before the lint token check, or reword the remedy to avoid the `pre-commit` substring; extend stall-recovery classify tests with remedy-bearing hook-failure evidence.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship.py
- **Concern**: Non-regular `finalize-state.sh` refusal has no terminal control flow. Scenario: The plan refuses to delete symlink or other non-regular `finalize-state.sh` shapes, but it does not say to stop the drive when deletion is refused. If reset continues, `_stall_signal_is_terminal` can still read a truthy finalize stall overlay and `normalized_outcome_values` can keep yielding `stalled`, so Part B recovery still deadlocks on the exact edge case the plan lists.
- **Proposed resolution**: On refused finalize deletion, fail closed: raise `Stalled` (or return a terminal `ShipResult`) and do not call `flush_logs_pre`; add a focused ship re-entry test with a symlinked finalize overlay asserting the drive stalls instead of looping on pre-terminal refresh.

### FINDING_4:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/implement/ship.py:1289-1372
- **Concern**: De-terminalize placement is contradictory in the plan. Scenario: The Approach section gives two anchors: run the helper after merged/done reconciliation finishes, and also assign the de-stalled ctx at run_ship entry right after blocked-resume handling. The second anchor sits before the done/merged/postmerge-push-watch/emergency-repair returns, so an implementer can reset stalled state before merged/done recovery reads the stalled overlay. That revives accepted FINDING_2 and can break reconciliation.
- **Proposed resolution**: Use one placement rule in the ship.py section: invoke the helper only after those early-return branches complete and immediately before the first pre-PR work that can call flush_logs_pre; assign ctx from the returned RunContext there. Remove the conflicting run_ship-entry-after-blocked-resume wording.
