## Proposed Design Outline

### Goals
- Re-derive a run's outcome from live ship evidence at the run's own pre-ship flush so a recovered-and-shipped run overwrites a stale "stalled" label with "shipping"/"pr-created"/"merged".
- Add a backstop in the run-log flush/batch path: when a run dir's manifest carries PR/merge evidence but the committed final-summary says "Outcome: stalled", rewrite the label.
- Add regression coverage: a run that flushes a genuine terminal stall, then recovers and ships, must not keep "stalled" in its committed summary.

### Non-goals
- Do not rewrite the 31 already-known-affected (or any other) historical run-log entries; that is a separate one-time data-repair follow-up.
- Do not change behavior for a genuine, permanent stall (no PR/merge evidence ever arrives) — those must keep showing "stalled".
- Do not touch `/design`'s own stall-classification path (`design-failure-terminal-state.env`); that is a separate code path from `/implement`'s ship-pr outcome normalization.

### Approach sketch
- Primary: extend the finalize-state STALL_TRACKING trust logic in `_stall_signal_is_terminal`/`normalized_outcome_values` (python/larch/state/_normalize.py) so a terminal finalize-state.sh stall is only honored absent live evidence of later shipping (PR URL/merge present, PHASE not stalled, BAIL_REASON absent) — same evidence gates already used for the ship-side stale-flag case (#5646/#4900).
- Ensure the run's own success paths in ship.py/ship_pr.py re-flush the committed final-summary after correcting finalize-state.sh, so the corrected label reaches the committed log, not just local state.
- Backstop: hook the existing run-log flush/batch path (python/larch/report/run_log_flush.py, final_report.py's manifest reconciliation) to compare manifest PR/merge evidence against the committed final-summary outcome line and rewrite it on mismatch — write-side mirror of the #4900 audit-tolerance read-time logic.
- Regression test(s) covering: finalize-state.sh records a genuine terminal stall, then live evidence later shows shipping/merge, and the reconciled/committed outcome is no longer "stalled".

### Surfaces in scope
- python/larch/state/_normalize.py
- python/larch/implement/ship_pr.py, ship.py
- python/larch/report/run_log_flush.py, final_report.py
- python/tests/state/test_stall_recovery.py, python/tests/report/test_run_logs.py, python/tests/implement/test_ship.py

### Open questions
- The exact mechanism by which a "recovered and shipped" run currently escapes reconciliation (manual recovery outside ship-pr's own retry loop vs. a success path that writes state but never re-flushes) needs direct confirmation during plan drafting; it determines where the primary fix's call site lands.
