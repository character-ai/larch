# Review Round 1

- Mode: `diff`
- 7 accepted, 5 rejected (1 neutral)

## Accepted Findings

### FINDING_1: validator_autofix AUTOFIX_STATUS lost after quiet_init
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: blocking
- **Concern**: `validator_autofix_main` calls `quiet_init` before printing `AUTOFIX_STATUS` to stdout. `/design` parses subprocess stdout for `AUTOFIX_STATUS`; after `quiet_init`, those prints go to the quiet log and `_autofix_status` is empty, so the ok branch never runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Emit terminal KVs via logging_util.emit/emit_kv or do not quiet-init this entrypoint if stdout must remain the contract


### FINDING_3: step5c publish and final-summary render disagree on issue/session metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-dyn-env-ctx-output.txt
- **Severity**: important
- **Concern**: `step5c_core` drives publish with merged `ctx` fields (`ctx.issue_number`, `ctx.session_id`, `ctx.claude_pid`), but `_step5c_render_final_summary` still passes `env.get("ISSUE_NUMBER")`, `env.get("SESSION_ID")`, and `env.get("REPO")` from the rehydrate-only `env` dict. `ctx` is built with `{**env, **os.environ, **normalized_overrides}`, so ambient `os.environ` can override session-file values in `ctx` while `env` keeps rehydrated values. When those differ, publish and final-summary render can target different issue/session metadata; the pause path (`_pause_args`) may share the same split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pass ctx fields or explicit argv values from the merged snapshot instead of env.get
  - From cursor-specialist-edge-cases-output.txt: Thread ctx into _step5c_render_final_summary (or pass explicit merged values) and use ctx.issue_number, ctx.session_id, ctx.repo, and ctx str_value helpers for render argv, matching step_final_summary_core and publish ctx fields.
  - From dyn-dyn-env-ctx-output.txt: Thread `ctx` into `_step5c_render_final_summary` and use the same typed fields (or explicit parameters derived from the same snapshot as `publish_args`) for `--issue-number`, `--session-id`, and `--repo`; align the pause path (`_pause_args` at `python/design_lifecycle.py:3792`) the same way so all Step 5c surfaces share one source.


### FINDING_7: direct step5c/final-summary core tests do not assert post-quiet_init contract stream
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Plan-required fd-3 contract test migration for direct `step5c_core` / `step_final_summary_core` invocations is not done; tests still assert `PUBLISH_RC` and `LARCH_FINAL_SUMMARY_*` via `capsys.readouterr().out`. Production cores call `quiet_init` and route contract output through fd 3. `python/conftest.py` autouse sets `LARCH_QUIET_DISABLE=1`, so `quiet_init` is a no-op in those tests and the suite does not regression-test the behavior that changed. Quiet routing or inherited-quiet behavior changes could leave contract KVs unasserted or tests passing on the wrong stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Migrate direct-core contract assertions to capture_contract_stream_to_paths or the inherited-quiet pipe pattern
  - From cursor-specialist-testing-output.txt: Migrate direct-core contract/marker assertions to capture_contract_stream_to_paths or inherited-quiet pipe pattern per plan.
  - From dyn-dyn-quiet-routing-output.txt: Migrate the direct-core contract assertions to fd-3 capture (`capture_contract_stream_to_paths` or the inherited-quiet pipe pattern), with `monkeypatch.delenv(LARCH_QUIET_DISABLE)` where needed, and add a parallel inherited-quiet test for `step_final_summary_main`.


### FINDING_8: missing plan-specified test_agents ctx/precedence coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-listed `python/test_agents.py` updates are missing. `agents.py` ctx conversion is untested for `resolve_model_args` `contains`/precedence and related `run_external_agent` ctx paths. Absent-vs-empty `LARCH_*` vs `CLAUDE_PLUGIN_OPTION_*` regression could slip in without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan-specified tests including test_agents ctx coverage and fd-3 contract capture migration
  - From cursor-specialist-testing-output.txt: Add tests for resolve_model_args with explicit Ctx mappings (absent vs empty primary; plugin fallback) and run_external_agent inner_sentinel_suffix override with ctx.


### FINDING_9: missing plan-specified drift-multiple fallback regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required regression test for invalid/non-positive `LARCH_DESIGN_DRIFT_MULTIPLE` fallback to `2` is missing after ctx conversion. Replacing `isdigit`/else-2 with bare `ctx.int_value` would change plan-size gate thresholds silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add monkeypatch tests for invalid/zero/negative LARCH_DESIGN_DRIFT_MULTIPLE asserting multiple stays 2 and drift trigger behavior unchanged.


### FINDING_10: missing plan-specified validate/check-size argv-wins and no-rehydrate tests
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required argv-wins and no-validator-rehydrate tests for `validate_plan_main` / `check_plan_size_main` are missing. Standalone validate/check-size could regress to validator rehydrate side effects or stale env tmpdir without detection. Broader plan-listed regression coverage for ctx precedence, symlink tmpdir env IPC removal, and drift-multiple fallback remains largely absent from the diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add the plan-specified tests including test_agents ctx coverage and fd-3 contract capture migration
  - From cursor-specialist-testing-output.txt: Add unit tests for argv --design-tmpdir over stale DESIGN_TMPDIR and assert _rehydrate_validator_env is not called on those mains.


### FINDING_11: pre-quiet_init Step 5c failures may not reach fd-4 diagnostic stream
- **Reviewer(s)**: dyn-dyn-quiet-routing-output.txt
- **Severity**: important
- **Concern**: Moving `quiet_init` into `step5c_core` / `step_final_summary_core` after rehydrate and tmpdir validation means pre-`quiet_init` failures (missing `CLAUDE_PLUGIN_ROOT`, missing/invalid `DESIGN_TMPDIR`, parse errors) call `_core_diagnostic` while `_core_quiet_mirrors_to_fd4()` is still false. Under inherited-quiet `/design` wrappers, early configuration errors now stay on stderr only and may not reach the fd-4 diagnostic stream the bash side expects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-quiet-routing-output.txt: Call `logging_util.quiet_init` immediately after successful rehydrate (once `DESIGN_TMPDIR` is known) and before plugin-root / tmpdir validation, or add a small pre-`quiet_init` helper that mirrors `_core_diagnostic` to fd 4 when inherited quiet is active.


