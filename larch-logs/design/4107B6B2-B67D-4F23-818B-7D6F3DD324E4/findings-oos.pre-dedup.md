### OOS_1:
- **Description**: MERGE_RESULT_MAIN_ADVANCED now encodes two different recovery causes without a ship-side discriminator. Scenario: Pre-merge staleness (mergeStateStatus not admin-eligible) and merge-attempt conflict remap share the same result literal and ship loop behavior. Debugging and future routing (e.g. conflict-only forced rebase) cannot distinguish them from merge.py output alone.
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: python/merge.py:37-45
- **Phase**: design

