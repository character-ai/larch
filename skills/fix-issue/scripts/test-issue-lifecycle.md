# skills/fix-issue/scripts/test-issue-lifecycle.sh — contract

Regression harness for `skills/fix-issue/scripts/issue-lifecycle.sh`. The primary behavior contract lives in `skills/fix-issue/scripts/issue-lifecycle.md`; this sibling exists for discoverability per AGENTS.md.

The harness is offline and hermetic. It PATH-stubs `gh`, uses `LARCH_TEST_TRACKING_WRITE_PATH` for marker-helper stderr failure fixtures, and uses `LARCH_TEST_REDACTOR_PATH` to exercise redactor failure and missing-redactor suppression. Keep this file, the primary contract, and the harness fixture list in sync when `close` stdout/stderr behavior or false-positive marker handling changes.
