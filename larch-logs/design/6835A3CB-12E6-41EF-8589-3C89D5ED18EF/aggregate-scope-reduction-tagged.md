### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:20-28
- **Concern**: [SCOPE-REDUCTION] Collected-only history changes the required launched-round pruning rule. Scenario: A reviewer slot that launches in rounds 1 and 2 but returns NOT_SUBSTANTIVE, EMPTY_OUTPUT, or is dropped under no-fallback has zero accepted findings in its last two launched rounds, yet the plan keeps it eligible because collected=false rows do not count
- **Proposed resolution**: Count every filtered manifest row that was actually launched as a strike-window row with accepted_count=0 unless the whole round is rolled back or history is missing/corrupt; use collector status for diagnostics, not to erase launched rounds
