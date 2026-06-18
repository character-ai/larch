### OOS_1:
- **Description**: [SCOPE-REDUCTION] Port adds design_require_plugin_root before step2b5 pause and check-size but design-step2b5.sh never calls it. Scenario: Empty or template CLAUDE_PLUGIN_ROOT today still reaches pause-save or plan check-size the same way Bash does today; adding validation is a behavioral change beyond the listed bodies to port
- **Reviewer**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:design step2b5
- **Phase**: design

Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral

