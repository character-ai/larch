# Review Round 2

- Mode: `diff`
- 6 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: compose_env_key reads stale first STALL_RECOVERY_REPORT_STATUS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `compose_env_key` uses `_read_env_value`, which returns the first matching line in `compose.env`. The retired shell used `tail -1`. Compose overwrites then appends: Compose writes `STATUS=printed` or `lookup-failed-open`, and tier_a append adds `STATUS=filed`. Python may read a stale first status, so `handle_compose_outcome` takes the wrong branch (fallback instead of filed success).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: For STALL_RECOVERY_REPORT_STATUS only read the last matching line in compose.env matching design-failure-report.sh compose_env_key behavior


### FINDING_6: step_final_summary_core emits stale summary and sentinel after render exception
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `step_final_summary_core` emits marked summary from disk and writes the completion sentinel even when `render_final_summary_main` raises. After a render exception, a pre-existing `final-summary.md` can be emitted as the authoritative run summary while failure-report gate work inside render never ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Gate marked emission and the completion sentinel on render success; emit explicit degraded content or skip when render did not refresh final-summary.md this run


### FINDING_9: Missing test for failure-report terminal-compose-failed fallback path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test for the failure-report `terminal-compose-failed` fallback path required by the plan. `compose_report_main` non-zero regressions would skip terminal-compose-failed fallback/audit without failing focused tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub compose_report_main to return non-zero after valid terminal state; assert fallback chat, audit reason, and KV decision


### FINDING_10: Missing test for invalid --exit-code values
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test for invalid `--exit-code` values despite plan-required validation coverage. Bad exit-code validation could regress and write corrupt `EXIT_CODE` into terminal-state env undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add tests for --exit-code abc (rc 2) and --exit-code unknown (rc 0)


### FINDING_11: test-design-stage-terminal-state -k filter excludes step0 clarify hard-halt integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-design-stage-terminal-state` `-k` filter excludes `test_step0_clarify_hard_halt` integration. Step 0b hard-halt in-process staging regressions may skip focused harness/relevant-checks runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Widen pytest -k filter or add explicit checks.py assertion for that test name


### FINDING_18: stage_panel_init_failed uses invalid panel-init-failed outcome for terminal-state staging
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: blocking
- **Concern**: `stage_panel_init_failed()` in `python/plan_review.py:263-280` stages `--outcome panel-init-failed`, but `stage_terminal_state_core()` validates outcomes against `stall_recovery._OUTCOMES`, which does not include `panel-init-failed`. A Step 3 panel-init hard stop returns a staging failure instead of writing `design-failure-terminal-state.env`; `python/test_design_lifecycle.py:1609-1613` cannot pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Use `failed-judge-panel` for `--outcome` and `--summary-outcome` in this caller, while keeping `--trigger panel-init-failed` and `--bail-reason panel-init-failed`


