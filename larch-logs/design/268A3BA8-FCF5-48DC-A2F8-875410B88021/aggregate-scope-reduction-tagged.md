### FINDING_1:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:design step2b-drafter
- **Concern**: [SCOPE-REDUCTION] Fatal in-process postplan should not sys.exit with raw emit rc 2. Scenario: Bash delegates via exec to design-step2b-postplan.sh which maps postplan_emit rc 2 to wrapper exit 1 (design-step2b-postplan.sh:230-232). Plan says drafter exits with the fatal postplan rc (plan.txt:108), so emit rc 2 would yield process exit 2 and change orchestrator/harness expectations vs today.
- **Proposed resolution**: Reuse the postplan wrapper fatal mapping: on emit rc 1 or 2 exit the drafter fence with 1 after diagnostics; reserve returning raw emit rc for the standalone design step2b-postplan CLI only if needed.
