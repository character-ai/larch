## Proposed Design Outline

### Goals
- Fix `test_check_reviewers_cursor_preflight_rc2_one_shot_and_cleanup` by adding the missing `_cursor_probe_setup_chain` monkeypatch (OOS_1).
- Remove dead `_step5_post_round_gates_with_timing` wrapper and inline `record_round_timing` after gates in the `step5` loop (OOS_2).
- Update test assertions for OOS_2 to reflect the simplified timing path.

### Non-goals
- Restoring the post-apply `checks.run_relevant_checks` / `checks.run_lint_fix` hook removed by #5540.
- Adding vendor-task row verification for `fix-applied` rounds.
- Changing timing semantics (end_s still recorded after gates complete).

### Approach sketch
- OOS_1: monkeypatch `_cursor_probe_setup_chain` (and `_cursor_probe_cleanup_private_config_dir`) in the failing test, matching the pattern of `test_check_reviewers_cursor_preflight_rc2_transient_rc1_one_shot`.
- OOS_2: remove `_step5_post_round_gates_with_timing`; in `step5` loop call `_step5_post_round_gates` directly then `_record_step5_round_timing` immediately after.
- Update tests that previously asserted deferred timing order via `_step5_post_round_gates_with_timing` mock.

### Surfaces in scope
- `python/test_agents.py` — add monkeypatches to the failing preflight test
- `python/review_and_fix.py` — remove `_step5_post_round_gates_with_timing`, inline timing
- `python/test_review_and_fix.py` — update timing-order assertions

### Open questions
- None.
