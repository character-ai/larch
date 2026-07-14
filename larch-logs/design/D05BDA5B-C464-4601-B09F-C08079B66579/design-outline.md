## Proposed Design Outline

### Goals
- Port all Bash-only behavioral assertions for `flush_execution_issues_main` into `python/tests/issue/test_execution_issues.py` so no pytest-absent assertion remains.
- Reduce `skills/implement/scripts/test-flush-execution-issues.sh` to ~30 lines verifying only plugin-root selection, CLI routing, argument forwarding, and exit-status forwarding.
- Update `skills/implement/scripts/test-flush-execution-issues.md` to reflect the delegation smoke scope.

### Non-goals
- No changes to `flush-execution-issues.sh` (the thin wrapper is already correct).
- No changes to `python/larch/issue/execution_issues.py` (only test code changes).
- No shard rebalancing (`test-flush-execution-issues` already delegates to pytest).

### Approach sketch
- Gap-analyze which Bash assertions lack pytest coverage: empty-input skip, `FLUSH_STATUS=ok` with count, `APPEND_LOG_FILE` in output, NDJSON step/source fields, multi-section count, and run-log failure.
- Add ~5 new pytest functions in `test_execution_issues.py` covering those gaps; existing tests remain unchanged.
- Replace the 258-line Bash harness with a ~30-line delegation smoke using a real plugin-root, verifying routing, exit code, and stdout passthrough.
- Update the contract doc to describe the smoke's purpose and narrow scope.

### Surfaces in scope
- `python/tests/issue/test_execution_issues.py`
- `skills/implement/scripts/test-flush-execution-issues.sh`
- `skills/implement/scripts/test-flush-execution-issues.md`

### Open questions
- None.
