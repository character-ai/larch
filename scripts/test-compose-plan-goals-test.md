# test-compose-plan-goals-test.sh contract

Regression harness for `python/cli.py plan compose-goals-test`.

Primary callers: `make test-compose-plan-goals-test`, and the
`test-harnesses-4` shard through `make test-harnesses`.

It covers:

- normal plan composition with a test-plan section,
- fallback output when the plan lacks a test-plan section,
- source plans that already start with an implementation-plan heading,
- alternate test-plan headings such as `Verification` and `Testing`,
- fail-closed behavior for too-short, pointer-only, empty, and missing plan
  files.

Update alongside `python/plan_quality.py`.
