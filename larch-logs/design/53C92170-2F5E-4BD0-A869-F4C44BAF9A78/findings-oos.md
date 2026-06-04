### OOS_1:
- **Description**: Parallel issue #3446 may edit OUTCOME_EXIT_MAP while this plan assumes STALLED stays EXIT_STALLED (4). Scenario: Merge or rebase order could land a #3446 change that remaps Outcome.STALLED or drops the key; main() would return a non-4 exit while tests still expect 4 only if this branch’s test_ship.py pin wins review
- **Reviewer**: Cursor-dyn-stdout-contract
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/config.py:18-23
- **Phase**: design

