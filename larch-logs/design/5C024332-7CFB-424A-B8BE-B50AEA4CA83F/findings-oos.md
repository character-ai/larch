### OOS_1: Empty paths=[] filter semantics are undefined
- **Description**: Empty paths=[] filter semantics are undefined. Scenario: paths=None scans all tracked files, but paths=[] could mean zero targets (clean 0) or be treated as an error, producing inconsistent exit codes across callers
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: python/larch/lint/engine.py:run_rule
- **Phase**: design



