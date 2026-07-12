### OOS_2: Unused `block_text` in `_finding_oos_reroute_marker`
- **Description**: Unused `block_text` in `_finding_oos_reroute_marker`. Scenario: Both copies ignore `block_text`; consolidation is a good time to drop the dead parameter, but behavior is already identical and this is not required for acceptance.
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: python/larch/review/review_tally.py:655-659
- **Phase**: design

