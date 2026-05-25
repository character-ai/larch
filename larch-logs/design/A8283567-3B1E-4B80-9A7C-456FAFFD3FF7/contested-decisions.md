### DECISION_1: Fix-dispatch path for per-job inner loop
- **Chosen**: Reuse `run_ci_fix_vendor`'s existing Cursor/Codex/Claude 3-tier waterfall directly, passing the captured local-job log as `--failure-log`. No changes to `lint-fix-loop.sh`.
- **Alternative**: Wrap `lint-fix-loop.sh`, widening its `--site` enum to accept a new value (e.g., `ship-pr-ci-per-job-<job-name>`), and route per-job fixes through it.
- **Tension**: Codex explicitly prefers the run_ci_fix_vendor path because it is already CI-failure-log-shaped and accepts `--failure-log`. Cursor's Claude fallback proposed wrapping lint-fix-loop. lint-fix-loop.sh is designed for `relevant-checks.sh` failures (pre-commit + agent-lint over changed files) and its prompt instructs the LLM to make minimum fixes locally for those linters; the CI launchers (`launch-{cursor,codex,claude}-ci.sh --role fix --failure-log`) are designed to read GitHub Actions logs.
- **Impact**: High
- **Affected files**: `scripts/ship-pr.sh`, `scripts/lint-fix-loop.sh`, new `scripts/ci-failed-jobs.sh`.

### DECISION_2: Whether to factor a reusable "run captured cmd → dispatch fixer → rerun up to 3" helper in ship-pr.sh
- **Chosen**: Factor it out. Introduce a private inline helper in `ship-pr.sh` (e.g., `run_captured_cmd_then_fix_waterfall`) that encapsulates: capture local-run log, redact via `redact-secrets.sh`, dispatch the run_ci_fix_vendor waterfall, re-run mapped command, repeat up to per-job cap. Both the new per-job loop AND the existing `run_checks_with_lint_fix_loop` invocation site can share the primitive (refactor the latter to use it).
- **Alternative**: Keep `run_checks_with_lint_fix_loop` as-is and write a separate per-job loop in ship-pr.sh that duplicates ~80% of the same structure (capture-log, redact, dispatch, re-run, count).
- **Tension**: Codex suggests factoring; Cursor's Claude fallback keeps them separate. Factoring reduces drift between the two but is a refactor of tested code. The risk is that subtle semantic differences (`record_failure` category strings, lint-fix-loop's path-allowlist behavior, `FIXED:`/`UNFIXABLE:` final-line contracts) get lost in the factoring and the existing `test-ship-pr.sh` harness assertions silently start failing on edge cases.
- **Impact**: Medium
- **Affected files**: `scripts/ship-pr.sh`, `scripts/test-ship-pr.sh`, `scripts/test-ship-pr-fix-loop-2632.inc.sh`.
