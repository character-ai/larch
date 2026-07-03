### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review_panel.py (plan.txt:95-99)
- **Concern**: [SCOPE-REDUCTION] The escalated-pruning plan still asks the design panel test to assert PRUNED_COUNT=0, but that KV is only emitted by the prune filter/code-review panel surface, not by plan-review panel-dispatch.. Scenario: A test that follows the plan can fail despite correct design behavior, or pressure the implementer to add a runtime PRUNED_COUNT emission, violating the test-only/no-runtime-change scope.
- **Proposed resolution**: Revise the planned assertion to use the existing design-panel surface: assert the manifest stays non-empty and PANEL_PRUNED_EMPTY=false, and prove the short-circuit by monkeypatching or capturing _filter_pruned receiving prune_round_num=0.
