### FINDING_1: Ship empty-fingerprint test must force live diff materialization
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The ship-level empty-fingerprint coverage does not prove the fail-closed live-materialization path. If `materialize_implementation_diff` is left optional, the test can fall back through the `live_diff is None` path and miss the branch where a live diff exists but `DIFF_FINGERPRINT` is empty.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the monkeypatch mandatory for this test and assert `materialize_implementation_diff` is called once with `repo_root`, `base_remote="origin"`, and `base_ref="main"` while `DIFF_FINGERPRINT=` remains empty.
  - From Cursor-Pragmatic: Require monkeypatching `materialize_implementation_diff` to return a non-empty diff and assert it was called once with `(repo_root, base_remote="origin", base_ref="main")`. Drop the "optionally" wording.


### FINDING_2: Direct helper empty-fingerprint test needs a live-branch assertion
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The direct helper test only checks the final boolean and durable-note outcome, which is also consistent with the staged fallback. It should prove that the live-materialization branch actually ran before the empty-fingerprint skip was exercised.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: After monkeypatching a non-empty live diff, add `mock.assert_called_once_with(repo, base_remote="origin", base_ref="main")` (or equivalent call-count assertion) in addition to the return-value checks.

