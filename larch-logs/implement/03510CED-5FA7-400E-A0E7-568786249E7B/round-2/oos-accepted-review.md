### OOS_1: correctness: python/ci_agentic_fix.py:409-421
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Health-class Claude launcher failures on cycle 1 emit first-fixer-non-health same as non-health failures. Auth/quota/infra failure on first agentic cycle routes to Exit 3 autonomous main-agent CI-fix instead of operator bail or in-loop retry. Emit distinct health status or route health to operator bail; reserve first-fixer-non-health for non-health only; retry transient health on later cycles.
- **Suggested revision**: Address the concern above.


### OOS_2: risk-integration: python/ci_agentic_fix.py:222-227
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Agentic driver re-classifies launcher failures without auth_verdict or stdout KV parity. Auth/quota failures may classify differently than launcher envelope, changing cycle>1 routing vs health branch expectations. Reuse launcher stdout KVs or pass external_auth_verdict and binary_present like _emit_ci_launcher_result.
- **Suggested revision**: Address the concern above.


### OOS_3: risk-integration: python/test_ci_monitor.py:1545-2398
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Sixteen evaluate_failure/monitor tests skipped without agentic replacements Agentic KV mapping or delegate argv regressions merge with no failing CI Replace skips with stubbed agentic-delegate tests per plan matrix
- **Suggested revision**: Address the concern above.


### OOS_4: risk-integration: python/test_ci_agentic_fix.py:1-167
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Agentic CI loop has only five tests vs plan ~20 cases Verify-fail/push/wait/empty-delta/20-cycle bugs ship undetected Add stub-runner tests for each _run_cycle terminal branch
- **Suggested revision**: Address the concern above.


### OOS_5: risk-integration: python/test_checks.py:1833-1881
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Lint-fix waterfall tests omit Claude-first production path Codex/Cursor tests pass while Claude tier is broken Update codex_fail_cursor test; add claude-only and triple-fail cases
- **Suggested revision**: Address the concern above.


### OOS_6: **risk-integration** `python/ci_agentic_fix.py:236-247` — On cycle 1, any Claude launcher failure classified as `health` (auth, quota, transient infra, missing binary) is emitted as `STATUS=first-fixer-non-health`. The ship-pr Exit 3 matrix treats that token as the hook for the **autonomous main-agent CI-fix** sub-procedure, which is meant for non-health “other” launcher failures. Transient auth/quota failures therefore bypass the dedicated Opus delegate and can pull in the bloated main agent instead of operator bail or in-delegate retry. The plan only names `first-fixer-non-health` for missing-binary-style CI failures, not all health classes. **Suggested fix:** Reserve `first-fixer-non-health` for `failure_class == "other"` on cycle 1. For `health`, either continue cycling (revert delta, consume a cycle) or fail closed with `waterfall-failed` / `ci-fix-exhausted`. Map missing-binary to `first-fixer-non-health` only when the reason is explicitly binary-absent.
- **Reviewer**: dyn-ci-delegate-output.txt
- **Concern**: - **risk-integration** `python/ci_agentic_fix.py:236-247` — On cycle 1, any Claude launcher failure classified as `health` (auth, quota, transient infra, missing binary) is emitted as `STATUS=first-fixer-non-health`. The ship-pr Exit 3 matrix treats that token as the hook for the **autonomous main-agent CI-fix** sub-procedure, which is meant for non-health “other” launcher failures. Transient auth/quota failures therefore bypass the dedicated Opus delegate and can pull in the bloated main agent instead of operator bail or in-delegate retry. The plan only names `first-fixer-non-health` for missing-binary-style CI failures, not all health classes. **Suggested fix:** Reserve `first-fixer-non-health` for `failure_class == "other"` on cycle 1. For `health`, either continue cycling (revert delta, consume a cycle) or fail closed with `waterfall-failed` / `ci-fix-exhausted`. Map missing-binary to `first-fixer-non-health` only when the reason is explicitly binary-absent.
- **Suggested revision**: Address the concern above.


### OOS_7: **risk-integration** `python/ci_monitor.py:1444-1497` — The parent delegate timeout is `CI_AGENTIC_FIX_MAX_CYCLES * (CI_WAIT_TIMEOUT_SEC + SUBPROCESS_DEFAULT_TIMEOUT_SEC)` (~20h). Each cycle also runs `verify_job_locally` (e.g. `make py-test`) with **no** timeout in the budget. Long verification can push total runtime past the parent cap; `proc.run` then kills the delegate mid-cycle (`fix-exhausted: delegate-timeout`) with possible partial commit/push state. **Suggested fix:** Extend the budget to include a per-cycle verify ceiling (or a single outer wall-clock cap), or run verification under an explicit timeout inside `ci_agentic_fix` and roll back before the parent kills the subprocess.
- **Reviewer**: dyn-ci-delegate-output.txt
- **Concern**: - **risk-integration** `python/ci_monitor.py:1444-1497` — The parent delegate timeout is `CI_AGENTIC_FIX_MAX_CYCLES * (CI_WAIT_TIMEOUT_SEC + SUBPROCESS_DEFAULT_TIMEOUT_SEC)` (~20h). Each cycle also runs `verify_job_locally` (e.g. `make py-test`) with **no** timeout in the budget. Long verification can push total runtime past the parent cap; `proc.run` then kills the delegate mid-cycle (`fix-exhausted: delegate-timeout`) with possible partial commit/push state. **Suggested fix:** Extend the budget to include a per-cycle verify ceiling (or a single outer wall-clock cap), or run verification under an explicit timeout inside `ci_agentic_fix` and roll back before the parent kills the subprocess.
- **Suggested revision**: Address the concern above.


### OOS_8: **risk-integration** `python/test_ci_monitor.py:1545-2398` — Fifteen `evaluate_failure` / monitor integration tests are `@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")` with no unskipped replacements. `python/test_ci_agentic_fix.py` has only five unit-level tests (repo-root validation, exhausted-detail composition, one health→`first-fixer-non-health` case, one `_agentic_fix_result` KV read). Plan-required coverage is missing for: single delegate per evaluation, `--repo-root`/`cwd` threading, rebase-pending non-reentry, passive `ci wait` parsing, `FIX_ATTEMPTED` promotion (`local-unfixable` / `head-changed` → `fix-exhausted`), and `rebase-required` → `goto_rebase`. **Suggested fix:** Add focused `test_ci_monitor.py` tests that stub `_agentic_fix_result` / `runner.run` and assert argv, `cwd`, pending-branch isolation, and KV→`FixResult` mapping; keep cycle-loop tests in `test_ci_agentic_fix.py`.
- **Reviewer**: dyn-ci-delegate-output.txt
- **Concern**: - **risk-integration** `python/test_ci_monitor.py:1545-2398` — Fifteen `evaluate_failure` / monitor integration tests are `@pytest.mark.skip(reason="agentic CI delegate replaces in-process fixer")` with no unskipped replacements. `python/test_ci_agentic_fix.py` has only five unit-level tests (repo-root validation, exhausted-detail composition, one health→`first-fixer-non-health` case, one `_agentic_fix_result` KV read). Plan-required coverage is missing for: single delegate per evaluation, `--repo-root`/`cwd` threading, rebase-pending non-reentry, passive `ci wait` parsing, `FIX_ATTEMPTED` promotion (`local-unfixable` / `head-changed` → `fix-exhausted`), and `rebase-required` → `goto_rebase`. **Suggested fix:** Add focused `test_ci_monitor.py` tests that stub `_agentic_fix_result` / `runner.run` and assert argv, `cwd`, pending-branch isolation, and KV→`FixResult` mapping; keep cycle-loop tests in `test_ci_agentic_fix.py`.
- **Suggested revision**: Address the concern above.


### OOS_9: **risk-integration** `python/ci_agentic_fix.py:335-339` — Passive CI wait parsing treats any outcome that is not `ACTION in {merge, already_merged}` and not `CI_STATUS==pass` as “CI still failing” and continues the loop using `FAILED_RUN_ID` or the prior `run_id`. If `ci wait` times out or publishes malformed/empty output (`wait_main` with `--output-file` writes KV only to the file), `wait` is `{}`, `next_run_id` falls back to the same `run_id`, and the delegate can burn all 20 cycles without a fresh failure signal. **Suggested fix:** Distinguish `ci wait` timeout / `ACTION=bail` / missing `FAILED_RUN_ID` from a genuine new CI failure; fail closed or emit `ci-fix-exhausted` when wait output is empty or `BAIL_REASON` indicates poll budget exhaustion instead of silently reusing the stale run id.
- **Reviewer**: dyn-ci-delegate-output.txt
- **Concern**: - **risk-integration** `python/ci_agentic_fix.py:335-339` — Passive CI wait parsing treats any outcome that is not `ACTION in {merge, already_merged}` and not `CI_STATUS==pass` as “CI still failing” and continues the loop using `FAILED_RUN_ID` or the prior `run_id`. If `ci wait` times out or publishes malformed/empty output (`wait_main` with `--output-file` writes KV only to the file), `wait` is `{}`, `next_run_id` falls back to the same `run_id`, and the delegate can burn all 20 cycles without a fresh failure signal. **Suggested fix:** Distinguish `ci wait` timeout / `ACTION=bail` / missing `FAILED_RUN_ID` from a genuine new CI failure; fail closed or emit `ci-fix-exhausted` when wait output is empty or `BAIL_REASON` indicates poll budget exhaustion instead of silently reusing the stale run id.
- **Suggested revision**: Address the concern above.


### OOS_10: correctness: python/ci_monitor.py:1266-1324
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Dead normal-fix run_waterfall body remains in run_ci_fix after agentic migration. Future or test caller could invoke legacy multi-tier CI fix instead of single agentic Claude delegate. Trim run_ci_fix to push-only ci_fix_rebase_pending branch per plan.
- **Suggested revision**: Address the concern above.


### OOS_11: correctness: python/ci_agentic_fix.py:228-248
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Non-health Claude launcher failures always emit first-fixer-non-health regardless of cycle number. Cycle 1 verify-fails and cycle 2 Claude refuses: delegate exits immediately with first-fixer-non-health instead of using remaining cycles or ci-fix-exhausted. Return first-fixer-non-health only when cycle==1; later cycles should waterfall-fail or continue until cap.
- **Suggested revision**: Address the concern above.


