### [Plan Review] FINDING_3

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/implement/dispatch_commit_route.py:65-72
- **Concern**: [SCOPE-REDUCTION] Inline step3 cleanup in checks_commit_route_main duplicates run_step_checks_main. Scenario: Plan adds a third copy at composite entry while run_step_checks_main already unlinks the same two paths; two call sites can drift again (prior OOS_4/OOS_6)
- **Proposed resolution**: Clear stale .completed/step-3-terminal and bg-poll-guard-probe-denials.step-3-terminal.count inside _bg_wait_marker when terminal_sentinel is .completed/step-3-terminal, then delete the duplicate block in run_step_checks_main; adjust the new test accordingly

