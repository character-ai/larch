### OOS_1:
- **Description**: Post-merge MAIN_ADVANCED relies on ci_monitor to set goto_rebase on the next iteration. Scenario: If mergeStateStatus stays BEHIND/BLOCKED (conflicted=false) after a conflict-at-merge API failure, decide() keeps action=merge and ship may retry merge without rebasing until iteration cap
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/ship.py:1643-1670
- **Phase**: design

