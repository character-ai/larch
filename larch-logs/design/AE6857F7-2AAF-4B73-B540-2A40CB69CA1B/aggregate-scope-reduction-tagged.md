### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py
- **Concern**: [SCOPE-REDUCTION] Drop unreadable-file exit-1 edge case. Scenario: Edge cases require unreadable tracked files to surface findings with exit 1, but engine.py discovery calls `_load_source`, which raises `ScanError` and `run_rule` returns exit 2 before the rule detector runs. The engine update explicitly keeps discovery and exit codes unchanged, so this edge case cannot be met without new engine behavior.
- **Proposed resolution**: Remove unreadable-file exit-1 language from Edge cases and tests, or document that unreadable paths remain engine exit 2 while malformed Python stays syntax_policy exit 1.
