## Decision 1: test_ci_monitor.py keyed RecordingRunner
- **Question**: Should the local keyed dict-based RecordingRunner in test_ci_monitor.py be replaced with test_support.RecordingRunner?
- **Resolution**: Keep it local. The keyed-by-argv interface is semantically different from the queue runner. Only replace inline `CommandResult(...)` constructions with `ok()` where straightforward.
- **Source**: user

## Decision 2: test_checks.py StubRunner migration safety
- **Question**: Can StubRunner be replaced with RecordingRunner.strict_queue() given the argv-replacement behavior difference?
- **Resolution**: Verify before migrating. StubRunner.calls records `(tuple, dict)` pairs while RecordingRunner.calls records `list[str]`. Multiple tests assert on `runner.calls[-1][0]` (the (argv, kwargs) tuple structure). Rewriting all assertions would be non-trivial and exceed the "minimum change" constraint. Keep StubRunner local.
- **Source**: codebase + user (verify)
