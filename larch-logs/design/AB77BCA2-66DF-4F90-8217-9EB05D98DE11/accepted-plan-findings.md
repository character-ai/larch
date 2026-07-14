### FINDING_2: Reject lexical `..` result-env paths during prevalidation
- **Reviewer(s)**: Codex-Requirements
- **Severity**: minor
- **Concern**: Path prevalidation remains incomplete for lexical `..` paths, which can cause the validator’s lexical parent loop to fail to reach the resolved root and hang at `/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Reject result-env paths containing `..` before calling the validator, and add this case to the planned preflight tests


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/larch/implement/ship_result.py
- **Concern**: [SCOPE-REDUCTION] Blanket uppercase key rendering drifts from route-exit wire names. Scenario: `dispatch_ship` handoff emits lowercase ledger keys such as `ledger_ready=true` (see `test_implement_dispatch.py`), while repair/CI keys are uppercase. Uniform uppercasing of JSON keys would emit `LEDGER_READY` and break parity with established handoff vocabulary piece 2 must consume.
- **Proposed resolution**: Name an explicit mixed-case key map aligned with `dispatch_ship` (`FAILED_RUN_ID`, lowercase `ledger_*`, uppercase repair/CI keys, plus documented `outcome` casing) instead of uppercasing every JSON field.


