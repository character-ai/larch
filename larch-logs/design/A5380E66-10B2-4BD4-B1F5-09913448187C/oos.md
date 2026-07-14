### OOS_1: python/larch/implement/dispatch_ship.py:864-878
- **Description**: python/larch/implement/dispatch_ship.py:864-878. Scenario: Route-exit bgjob and handoff env parsers that fail closed on duplicate keys stay outside the migration and lint owner set (G-IO-1)
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_ship.py:209-214
- **Phase**: design




Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral Fileable=false

### OOS_2: `SECRET_SCRUB_VIOLATIONS` stdout scan stays outside the migration set
- **Description**: `SECRET_SCRUB_VIOLATIONS` stdout scan stays outside the migration set. Scenario: `_scrub_violations` still does a bespoke last-wins `KEY=value` loop with numeric validation on the design log-publish path. It is not in the firm file list, so the ratchet and codec policies will not govern this publish/finalize surface.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/design/design_log_publish_flow.py:311-324
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

