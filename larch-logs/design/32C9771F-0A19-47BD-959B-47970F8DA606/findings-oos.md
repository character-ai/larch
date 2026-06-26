### OOS_1: Step 5 timing mark with no round-N dir still falls through to stale ship-pr
- **Description**: Step 5 timing mark with no round-N dir still falls through to stale ship-pr. Scenario: On stall recovery re-entry, progress/done is cleared before round-1 exists; if ship-pr-state.sh remains, the hook can still report Ship-PR until round artifacts appear
- **Reviewer**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: python/progress_report.py:1412-1417
- **Phase**: design



