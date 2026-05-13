## Goal
Add stub-based test coverage for the --no-logs-commit flag in scripts/test-ship-pr.sh, verifying that all three larch-log.sh commit call sites in ship-pr.sh are suppressed when the flag is true and invoked when false.

## Test plan
- Run `bash scripts/test-ship-pr.sh` and verify all 31 tests pass (19 existing + 12 new assertions)
