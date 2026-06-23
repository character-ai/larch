### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/implement_dispatch.py:44-56
- **Concern**: [SCOPE-REDUCTION] Plan still maps handoff exit 0 with non-OK `outcome` to `reship` and adds a test for it.. Scenario: `python/ship.py` `main()` always returns `config.OUTCOME_EXIT_MAP[result.outcome]` and `OUTCOME_EXIT_MAP` pairs exit 0 only with `Outcome.OK`, so a single `ship pr` invocation cannot produce rc 0 with non-OK JSON. The branch, required-field row, and `exit 0 non-OK → reship` test add dead routing surface that misleads implementers and expands scope beyond the issue.
- **Proposed resolution**: Remove the exit-0 non-OK `reship` mapping from `ship_route_exit_main`, the per-exit required-field table, `ship-pr-exit-matrix.md`, and `test_implement_dispatch.py`; classify exit 0 with `outcome=OK` as `complete` only.
