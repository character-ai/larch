## Decision 1: run_ci_fix dead-waterfall approach
- **Question**: Should we trim the non-rebase-pending waterfall body or keep/guard it?
- **Resolution**: Trim run_ci_fix to push-only (ci_fix_rebase_pending branch) and update the 6 tests that call run_ci_fix with ci_fix_rebase_pending=False.
- **Source**: user

## Decision 2: Test coverage replacement scope + constraint
- **Question**: Which skipped evaluate_failure tests to replace, and with what?
- **Resolution**: Replace a critical subset of the 16 skipped tests with stubbed _agentic_fix_result tests (monkeypatch, no real LLM calls). Hard constraint: no LLM queries in CI under any circumstances.
- **Source**: user

## Decision 3: Passive CI wait bail approach
- **Resolution**: Return ci-fix-exhausted (fail closed) when _wait_for_ci errors, instead of continuing cycles with a stale run_id.
- **Source**: codebase (OOS suggestion)

## Decision 4: Cycle-dependent first-fixer-non-health
- **Resolution**: Return first-fixer-non-health only on cycle==1; cycle>1 non-health failures return waterfall-failed (allowing the loop to continue).
- **Source**: codebase (OOS suggestion)

## Decision 5: Delegate timeout verify budget
- **Resolution**: Add a per-cycle verify ceiling to _agentic_fix_delegate_timeout_sec or pass an explicit timeout to verify_job_locally.
- **Source**: codebase (OOS suggestion)
