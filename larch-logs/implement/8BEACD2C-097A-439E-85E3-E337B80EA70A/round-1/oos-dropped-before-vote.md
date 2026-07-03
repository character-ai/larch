### OOS_1: [OUT_OF_SCOPE] Live-diff test coverage misses the production repo_root path
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: nit
- **Concern**: The helper unit test does not pass repo_root, so it skips the live-diff branch that production callers use. A regression in repo_root/live-diff delegation or materialization could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a test passing repo_root with mocked materialize_implementation_diff, or an integration test for no-delta rebase note preservation.
  - From cursor-specialist-testing: Extend or add a test passing repo_root and mocking materialize_implementation_diff to cover the production code path.

### OOS_2: [OUT_OF_SCOPE] No test covers pin failure falling back to invalidate and drop notice
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: There is no test for the branch where pin is attempted with a non-empty head SHA but `pin_note_from_staged_for_current_head` returns false. The invalidate-and-drop-notice path is therefore unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Add a test monkeypatching pin to False and asserting invalidate clears artifacts and writes the drop notice.

