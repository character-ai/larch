### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_panel.py:214-256
- **Concern**: Dynamic render failure logging omits the established append-failure contract. Scenario: The plan says append per-slot warnings to execution-issues.md under Warnings but plan_review_panel.py has no _run_cli or run-log append-failure path; ad-hoc writes can skip ### Warnings structure and --redact scrubbing that plan_review_round.py uses for the same file
- **Proposed resolution**: Mirror plan_review_round.py:_log_reviewer_status_failure: write a small failure log, call python/cli.py run-log append-failure with --category Warnings --redact, and sanitize slot or stderr text before logging

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/plan_review_panel.py:214-256; plan.txt:63-75,130-133
- **Concern**: Dynamic render failure plan still publishes plan-blind fallback rows. Scenario: When render plan-review exits non-zero for a dynamic scout slot, the proposed test still expects the slot in plan-review-slots.ndjson and a one-line fallback prompt. That prompt lacks the plan path and TSV/sentinel contract, so the reviewer can review the wrong artifact and get dropped, leaving item 6 unfixed.
- **Proposed resolution**: For dynamic slots only, record the failure warning but skip appending that row to the manifest. Keep static fallback unchanged. Update the regression test to assert the failed dynamic row is absent and emit the aggregate warning through INVALID_SLOT_PANEL_WARNING or another carried key.
