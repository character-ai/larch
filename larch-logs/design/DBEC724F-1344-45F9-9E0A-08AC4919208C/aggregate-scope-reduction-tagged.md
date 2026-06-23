### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate renderer drift. Scenario: `### UPDATED: skills/voter-calibration/scripts/voter-calibration.py` still allows a report-local table helper "mirroring `_table`" beside shared `render_voter_severity_scoreboard`. That pattern was rejected in prior rounds and can diverge on columns, empty-state text, and `_format_rate` handling while live tallies use the shared helper.
- **Proposed resolution**: Require `render_voter_severity_scoreboard` from `python/voting.py` only; delete the "or reuse a local table helper mirroring `_table`" option from the plan.

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/voter-calibration/scripts/voter-calibration.py:67
- **Concern**: [SCOPE-REDUCTION] Optional local severity table helper reopens duplicate-renderer drift. Scenario: The plan still allows `render_voter_severity_scoreboard` or a local table helper mirroring `_table` beside the shared `python/voting.py` renderer. Prior rounds rejected that duplicate path; a second renderer can diverge on columns, empty-state text, and rate formatting while live tallies use the shared helper
- **Proposed resolution**: Remove the `or reuse a local table helper mirroring _table` alternative. Require `render_voter_severity_scoreboard` from `python/voting.py` only, matching the agreement path pattern.
