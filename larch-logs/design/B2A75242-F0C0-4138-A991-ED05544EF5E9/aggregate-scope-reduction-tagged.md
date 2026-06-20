### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_design_lifecycle.py:2248-2351
- **Concern**: [SCOPE-REDUCTION] Step 5c failure-tail bullets duplicate existing coverage. Scenario: Plan lines 105-108 ask to add rc 2/rc 5 failure-tail, terminal-sentinel, and sidecar tests, but test_step5c_core_publish_tail_abort_stages_renders_and_writes_terminal and test_step5c_core_publish_tail_abort_rc5_stages_and_writes_terminal already assert terminal-state env, step-5c-terminal, and summary sidecars
- **Proposed resolution**: Drop the redundant failure-tail additions; keep only the new matrix row and stale-summary success-path cases called out elsewhere in the plan
