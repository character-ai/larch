### FINDING_2: Unreadable-file behavior conflicts with engine exit semantics
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The unreadable-file edge-case requirement conflicts with the existing engine behavior, which returns exit code 2 with stderr and no stdout finding for `ScanError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Align edge cases and tests with engine behavior: unreadable paths exit `2` without a stdout finding; reserve exit `1` for live detections such as malformed Python under `syntax_policy=fail`.


### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py
- **Concern**: [SCOPE-REDUCTION] Drop unreadable-file exit-1 edge case. Scenario: Edge cases require unreadable tracked files to surface findings with exit 1, but engine.py discovery calls `_load_source`, which raises `ScanError` and `run_rule` returns exit 2 before the rule detector runs. The engine update explicitly keeps discovery and exit codes unchanged, so this edge case cannot be met without new engine behavior.
- **Proposed resolution**: Remove unreadable-file exit-1 language from Edge cases and tests, or document that unreadable paths remain engine exit 2 while malformed Python stays syntax_policy exit 1.


