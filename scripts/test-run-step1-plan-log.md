# test-run-step1-plan-log.sh contract

Regression harness for `scripts/run-step1-plan-log.sh`.

Primary caller: `make test-run-step1-plan-log`.

Coverage:

- Missing required flags exit 2.
- The plan path is always `$IMPLEMENT_TMPDIR/plan.txt` and is passed to `compose-plan-goals-test.sh`.
- `session-id` is derived from tmpdir and passed to `larch-log.sh write`.
- The composed output is written to `$IMPLEMENT_TMPDIR/plan-goals-test.md`.
- `larch-log.sh write` receives the hardcoded `implement` /
  `plan-goals-test` batch identifiers.

Update alongside `scripts/run-step1-plan-log.sh`.
