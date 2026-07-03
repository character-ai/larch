### [Plan Review] FINDING_6

### FINDING_6:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 while finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `execution_issues.flush_execution_issues_safety_net` before log commit. Adding the same call in `step-18.sh` duplicates append-only work on every finalize path without improving transcript coverage.
- **Proposed resolution**: Limit Step 18 changes to `LARCH_RUN_ID` rehydration and `run-log capture-transcript`. Leave execution-issues flush to finalize teardown; update `step-18.md` and `test-step-18.sh` to match.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/step-18.sh:213-241
- **Concern**: [SCOPE-REDUCTION] Plan re-adds `execution-issues flush-safety-net` in Step 18 though finalize teardown already runs it. Scenario: `python/larch/state/finalize.py` `_teardown_log_flush` already calls `flush_execution_issues_safety_net` before `run-log commit`. Re-adding it in `step-18.sh` duplicates append-only work and expands the transcript diff without helping `session-transcript.jsonl` capture
- **Proposed resolution**: Add only `run-log capture-transcript` (plus `LARCH_RUN_ID` rehydration) in Step 18. Omit `flush-safety-net` from the shell; update `step-18.md` and `test-step-18.sh` to assert transcript capture ordering, not flush duplication

