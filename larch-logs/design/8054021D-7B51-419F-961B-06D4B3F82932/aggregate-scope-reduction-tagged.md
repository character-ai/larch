### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:518-519
- **Concern**: [SCOPE-REDUCTION] Plan must explicitly drop orchestrator validation.log writes on rc=2 and other-rc branches, not only append-failure prose. Scenario: Current Step 2b.5 rc=2 text tells the orchestrator to create/overwrite check-plan-size.validation.log from _plan_size_out before append-failure. The plan removes append-failure but does not clearly forbid that write. If it remains, orchestrator stdout-only capture can overwrite the Python-written stdout+stderr log and drop rc=3 diagnostics from execution-issues.md
- **Proposed resolution**: In the skills/design/SKILL.md update bullets, state that on rc=2 and any other non-zero rc the orchestrator must not write check-plan-size.validation.log; only step2b5_main writes it before self-logging

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/design_lifecycle.py:581-602
- **Concern**: [SCOPE-REDUCTION] Reuse existing _capture_stdout_stderr and _append_failure instead of adding _step2b5_log_check_size_failure. Scenario: The plan adds a new private helper while design_lifecycle.py already has _capture_stdout_stderr (step5b OOS paths) and _append_failure for the same capture-then-append contract
- **Proposed resolution**: Implement step2b5_main with _capture_stdout_stderr to a temp stderr sink, combine stdout and stderr into check-plan-size.validation.log on non-zero rc, then call _append_failure; skip a new helper unless it is shared beyond step2b5
