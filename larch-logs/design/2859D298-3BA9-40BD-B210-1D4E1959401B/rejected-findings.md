### [Plan Review] FINDING_1

### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1452-1470
- **Concern**: [SCOPE-REDUCTION] Item 4 proposes a new carry-warning helper but the reset at continuation already owns the bug. Scenario: When PLAN_REVIEW_CONTINUE=true the loop unlinks .step3-review-result.env and sets degraded_values={} so round-1 DEGRADED_PANEL_WARNING / INVALID_SLOT_PANEL_WARNING never reach the final complete envelope even though _STEP3_ROUND_CARRY_KEYS and _step3_round_carry_values already exist
- **Proposed resolution**: Reuse _step3_round_carry_values (or equivalent selective retention of _STEP3_ROUND_CARRY_KEYS) instead of degraded_values={}; add the multi-round test against this exact continuation branch




### [Plan Review] FINDING_7

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/run_logs.py:2008-2013; python/design_log_publish_flow.py:300-425
- **Concern**: [SCOPE-REDUCTION] New run-log commit --pre-scrub-violations flag is unnecessary for the design warning fix. Scenario: The only planned source of pre-redaction counts is design_log_publish_flow.py, and that module already translates run-log commit stdout into its own SECRET_SCRUB_VIOLATIONS output. Adding a public run-log commit flag and validation broadens the CLI contract without being required for implement-path scrub counts.
- **Proposed resolution**: Drop the new CLI flag. Let _commit_run report counts from _copy_tree_to_repo for implement logs, and have design_log_publish_flow add its pre-redaction count to _scrub_violations(commit.stdout) before emitting SECRET_SCRUB_VIOLATIONS.




