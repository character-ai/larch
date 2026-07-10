### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/implement/ship.py:1258-1259
- **Concern**: _emergency_repair_transient_recovery_result omits skip terminal handling. Scenario: The plan makes skip gate-not-applicable for preflight, Step 2, pre-merge, post-merge push watch, and wait loops, but _emergency_repair_transient_recovery_result still requires health.status == pass. A resume@emergency-repair run whose live probe returns skip (stale state after upgrade, or any path that reached emergency-repair) keeps NEEDS_USER_INPUT instead of finalizing even though main-health is N/A.
- **Proposed resolution**: Add if health.status == skip: return None alongside pass in _emergency_repair_transient_recovery_result; extend python/tests/implement/test_ship.py with emergency-repair resume coverage asserting skip finalizes postmerge; list python/larch/implement/ship.py emergency-repair branch in ### UPDATED files if not already implied.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/tests/implement/test_main_health.py
- **Concern**: Plan lacks regression for non-default missing-workflow rc 1. Scenario: Approach step 4 and edge cases require skip only when query.workflow == config.MAIN_HEALTH_DEFAULT_WORKFLOW; a custom workflow miss must stay error. Tests cover matching CI miss and generic non-matching rc 1, but not rc 1 with gh missing-workflow text while query.workflow is non-default; a removed guard could misclassify other --workflow failures as skip.
- **Proposed resolution**: Add a test_main_health case: run_list_filtered_read rc 1 with could not find any workflows named Other and query.workflow Other (or non-default name) asserts status error not skip.



