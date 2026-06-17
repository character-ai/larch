### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:519-520
- **Concern**: Makefile test-review-design-step3-loop still selects removed embedded/_run_legacy pytest names. Scenario: Plan deletes embedded-asset parity tests but leaves -k 'embedded_review or embedded_run_step3_review or embedded_waterfall or run_legacy'; pytest collects zero tests (exit 5) and test-harnesses-16 fails
- **Proposed resolution**: Pin Makefile:519-520 to native loop/panel selectors (for example cap_reached or tally_error_rollback plus new native round/continuation tests) when embedded tests are removed

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:307-316; skills/design/scripts/design-step3b-tail.sh:113-130
- **Concern**: Step 3b-tail plan changes the step-4 sentinel timing. Scenario: Current tail renders Gate C preview and emits SKIP_APPROVE_REQUESTED_GATEC before touching .completed/step-4; the plan requires the sentinel before Gate C preview, so an interrupted or failed preview can leave Step 4 marked complete and resume may skip the missing Gate C surface
- **Proposed resolution**: Revise the plan and tests to preserve current ordering: Gate C timing mark and preview first, then SKIP_APPROVE_REQUESTED_GATEC, then create .completed/step-4 after that path succeeds

### FINDING_2:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:106-114; plan.txt:166-178
- **Concern**: Preserved RUN_STEP3_PLAN_REVIEW_LOOP_SH seam has no native default target. Scenario: The plan says surviving RUN_STEP3_* hooks default to native CLI targets, but it registers no single-round plan-review verb; after deleting plan-review-loop.sh and _run_legacy, following this can leave run_step3_review defaulting to a deleted shell path or an unregistered command
- **Proposed resolution**: Either call run_plan_review_round in process when the env override is unset and document RUN_STEP3_PLAN_REVIEW_LOOP_SH as override-only, or register a minimal native single-round plan-review verb before deleting the shell body
