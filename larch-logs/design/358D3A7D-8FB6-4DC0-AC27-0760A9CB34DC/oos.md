### OOS_1: [SCOPE-REDUCTION] Full-materialization fail-closed on scalar/non-object `oos_observations` items exceeds retired shell parity
- **Description**: [SCOPE-REDUCTION] Full-materialization fail-closed on scalar/non-object `oos_observations` items exceeds retired shell parity. Scenario: Retired `materialize-manifest-oos.sh` jq loop still processes non-object array elements (empty `.title` becomes `Untitled external implementer OOS N`); the plan adds TypeError fail-closed plus new pytest cases not in `test-materialize-manifest-oos.sh`, expanding diff and bail surface beyond the issue's subprocess-to-Python cutover
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: plan.txt:22-23
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

