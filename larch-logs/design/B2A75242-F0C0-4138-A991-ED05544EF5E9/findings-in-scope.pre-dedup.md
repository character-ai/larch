### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_panel.py:214-256
- **Concern**: Dynamic render failure logging omits the established append-failure contract. Scenario: The plan says append per-slot warnings to execution-issues.md under Warnings but plan_review_panel.py has no _run_cli or run-log append-failure path; ad-hoc writes can skip ### Warnings structure and --redact scrubbing that plan_review_round.py uses for the same file
- **Proposed resolution**: Mirror plan_review_round.py:_log_reviewer_status_failure: write a small failure log, call python/cli.py run-log append-failure with --category Warnings --redact, and sanitize slot or stderr text before logging



### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_design_lifecycle.py:2248-2351
- **Concern**: [SCOPE-REDUCTION] Step 5c failure-tail bullets duplicate existing coverage. Scenario: Plan lines 105-108 ask to add rc 2/rc 5 failure-tail, terminal-sentinel, and sidecar tests, but test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal and test_step5c_core_publish_tail_abort_rc5_stages_and_writes_terminal already assert terminal-state env, step-5c-terminal, and summary sidecars
- **Proposed resolution**: Drop the redundant failure-tail additions; keep only the new matrix row and stale-summary success-path cases called out elsewhere in the plan



### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_panel.py:214-256; plan.txt:63-75,130-133
- **Concern**: Dynamic render failure plan still publishes plan-blind fallback rows. Scenario: When render plan-review exits non-zero for a dynamic scout slot, the proposed test still expects the slot in plan-review-slots.ndjson and a one-line fallback prompt. That prompt lacks the plan path and TSV/sentinel contract, so the reviewer can review the wrong artifact and get dropped, leaving item 6 unfixed.
- **Proposed resolution**: For dynamic slots only, record the failure warning but skip appending that row to the manifest. Keep static fallback unchanged. Update the regression test to assert the failed dynamic row is absent and emit the aggregate warning through INVALID_SLOT_PANEL_WARNING or another carried key.



