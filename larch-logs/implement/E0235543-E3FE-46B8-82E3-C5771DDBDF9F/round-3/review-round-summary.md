# Review Round 3

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: correctness: empty explicit --session-id changes run_id resolution
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Cores always pass explicit `--session-id` (even when empty), changing run_id resolution vs legacy env-only render. With `SESSION_ID=""` in session env, `run_logs_path` becomes `larch-logs/design//` and the summary header uses an empty run id; legacy path used `unknown` and `N/A`. Omit `--session-id` when `ctx.session_id` is empty, or treat empty explicit argv like absent and fall back to `unknown`; use falsy `run_id` for `run_logs_path` `N/A`.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_5: risk-integration: missing rehydrate-vs-ambient ctx tests for validator paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-required tests for ctx-backed reads of `SUMMARY_OUTCOME`, `ISSUE_NUMBER`, and `REPO` from rehydrate merge are absent in `python/test_plan_quality.py`; only symlink tmpdir pause coverage exists. Session env rehydrates cancelled outcome or issue metadata but ambient `os.environ` holds stale values; `_validator_operator_cancel_audit` or `_validator_pause_save` could use wrong `OUTCOME`/`--issue` without detection. Add test with session-env rehydrate vs stale ambient env; assert pause argv and cancel audit sentinel use ctx fields from rehydrate, not ambient.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_6: risk-integration: missing subprocess_env PATH/HOME regression test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan requires regression that `ctx.subprocess_env` keeps full-process `PATH`/`HOME`; only isolated override/removal coverage exists in `test_ctx.py` while `_maybe_timing_mark` now uses `ctx.subprocess_env`. A partial snapshot missing `PATH`/`HOME` would make timing subprocess env incomplete; failures are swallowed by `suppress(OSError)` and regress silently. Add lifecycle test in `python/test_design_lifecycle.py` building core-style ctx and assert `subprocess_env` includes `PATH`/`HOME` plus wrapper overrides (e.g. `LARCH_TIMING_SKILL`).
- **Suggested revisions (informational for voters; coder decides)**:


