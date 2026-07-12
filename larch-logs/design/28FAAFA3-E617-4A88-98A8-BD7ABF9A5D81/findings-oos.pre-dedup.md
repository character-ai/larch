### OOS_1: [OUT_OF_SCOPE] Marker-bypass sites stay on independent marker/heading logic after the in-scope migration
- **Description**: [OUT_OF_SCOPE] Marker-bypass sites stay on independent marker/heading logic after the in-scope migration. Scenario: The plan excludes `decompose.py`, `learn_from_bugs.py`, and `design_router.py`, so inline `larch:plan` marker checks and `learn_from_bugs`’s `###`-only heading regex remain parallel owners; the feature goal still names marker drift at those paths
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/decompose.py:336-339; python/larch/issue/learn_from_bugs.py:62-66; python/larch/design/design_router.py:128
- **Phase**: design



