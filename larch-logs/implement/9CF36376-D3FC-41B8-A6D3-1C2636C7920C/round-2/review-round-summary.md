# Review Round 2

- Mode: `diff`
- 4 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Clarify mode fallback references an undefined helper
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: important
- **Concern**: `clarify._resolve_summary_mode` calls `_read_source_env_value`, which is undefined in this module; when `run-params.json` lacks `mode`, follow-up render can raise `NameError` after a successful log-publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Copy or import `_read_source_env_value` into clarify (or share both helpers) and add a source-env-only mode fallback test


### FINDING_2: Pause integration test still misses committed summary content
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-summary-publish
- **Severity**: important
- **Concern**: The pause-path real-publish test exercises the driver, but it still does not assert the committed `larch-logs/design/<RUN_ID>/final-summary.md`; a stale or missing enriched summary could slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extend test_pause_save_uses_real_log_publish_path to git-show final-summary.md and assert enriched body markers
  - From cursor-specialist-testing: Mirror log-publish enriched-content assertions in test_pause_save_uses_real_log_publish_path via git show on larch-logs/design/<RUN_ID>/final-summary.md.
  - From codex-specialist-testing: Read the pushed `larch-logs/design/RUN1/final-summary.md` from the local origin branch and assert it exists, is enriched, and uses the paused outcome.
  - From dyn-dyn-summary-publish: Extend the pause integration test to `git show` the committed `final-summary.md`, assert it contains `## /design run` / `<!-- larch:run-summary v=1 -->`, and assert stale placeholders are absent.


### FINDING_4: Step 5c still resolves mode from a different source than log-publish
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-summary-publish
- **Severity**: latent
- **Concern**: The post-publish Step 5c render still uses wrapper/session `ENV_MODE`, while the pre-copy log-publish render prefers `run-params.json` before `source-env.sh`; conflicting inputs can produce different mode metadata in the committed log and the tracking comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Align Step 5c with _resolve_summary_mode and add a parity test for conflicting mode sources.
  - From dyn-dyn-summary-publish: Extract `_resolve_summary_mode` to one shared helper (for example in `design_summary.py`) and use it from both `design_log_publish_flow.py` and `_step5c_render_final_summary`, matching the clarify follow-up path.


### FINDING_6: Failed-plan-write result env ordering is not asserted
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: The failed-plan-write test checks that `--outcome failed-plan-write` was passed, but it does not prove `.design-publish-result.env` is written only after `design log-publish` finishes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Record ordering by monkeypatching `_write_result_env` or by having the fake log-publish inspect whether the result env exists during its call, then assert log-publish precedes the write.


