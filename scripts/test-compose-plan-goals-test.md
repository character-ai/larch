# test-compose-plan-goals-test.sh contract

Regression harness for `scripts/compose-plan-goals-test.sh`.

Primary callers: `make test-compose-plan-goals-test`, and the
`test-harnesses-4` shard through `make test-harnesses`.

It covers:

- normal plan composition with a test-plan section,
- fallback output when the plan lacks a test-plan section,
- fail-closed behavior for too-short, pointer-only, empty, and missing plan
  files.

Update alongside `scripts/compose-plan-goals-test.sh`.
