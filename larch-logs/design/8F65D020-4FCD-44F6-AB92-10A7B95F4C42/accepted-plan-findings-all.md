### FINDING_8: Ambient plugin-root isolation test
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Concern**: The isolation regression test does not seed ambient `CLAUDE_PLUGIN_ROOT` and `LARCH_CLAUDE_PLUGIN_ROOT`, so a scrub regression could go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Mirror test_conftest_session_isolation: add module-scoped ambient CLAUDE_PLUGIN_ROOT and LARCH_CLAUDE_PLUGIN_ROOT exports, then assert both are absent during the function-scoped scrub (either in test_shell_fixtures.py or by extending test_conftest_session_isolation.py and keeping the plan's regression command)


