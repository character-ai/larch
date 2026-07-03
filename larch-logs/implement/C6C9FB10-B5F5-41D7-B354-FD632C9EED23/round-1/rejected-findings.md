### [rejected] FINDING_2

**Rejected subtype:** neutral (YES below acceptance threshold)

### FINDING_2: `ERROR_MESSAGE` Step 0 path needs an integration test
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing, dyn-dyn-cli-envelope
- **Severity**: important
- **Concern**: The current Step 0 tests still mock or match the old `VALIDATION_ERROR` path, so they do not prove that `design step0-parse` / `step0-session` reads the exact `ERROR_MESSAGE` line from the `--output` env file. A regression that drops that env-file field while keeping stdout or fallback behavior intact could still pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Mock or e2e step0-parse with rc 3 plus ERROR_MESSAGE and assert stderr matches the exact ready-to-print line; add run_design_cli step0-parse -- --hard smoke.
  - From cursor-specialist-testing: Add --output file assertions for a standard rejection such as --hard, mirroring the public --output rejection test.
  - From codex-specialist-testing: Pass an ERROR_MESSAGE through the fake parse result and assert the captured stderr matches that exact line, not just the old fallback wording.
  - From dyn-dyn-cli-envelope: Add an integration test that runs `design step0-parse` or `design step0-session` with a disallowed flag such as `--hard` and asserts stderr equals the exact `ERROR_MESSAGE` line emitted by `parse-flags`, including the quoted-env round-trip through `load_bash_quoted_env`.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0

