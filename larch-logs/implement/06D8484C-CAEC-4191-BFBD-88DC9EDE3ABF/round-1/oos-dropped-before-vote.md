### OOS_1: [OUT_OF_SCOPE] correctness: python/checks.py:994-995
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] assert outcome is not None after try/finally would raise AssertionError if impl returned None without raising. Latent footgun if impl contract loosens; not a current runtime path. Return explicit error or drop assert if None is ever valid.
- **Suggested revision**: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] architecture: python/agents.py:5763
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Claude lint-fix launcher records claude-lint-fix with claude.log output, producing inconsistent Gantt labels vs claude/lint-fix.txt path. Chart shows unknown/claude.log instead of claude/lint-fix for Claude-tier lint-fix. Align launcher output basename with claude-lint-fix.txt convention.
- **Suggested revision**: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] architecture: python/review_and_fix.py:2702-2708
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] _record_step5_round_timing is not failure-suppressed unlike checks timing helpers A rare record_round_timing failure in finally could theoretically interfere with exception propagation from post-gate failures. Wrap _record_step5_round_timing in contextlib.suppress(Exception) for parity with _record_checks_vendor_task.
- **Suggested revision**: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] code-quality: python/test_review_and_fix.py
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing plan acceptance and wiring tests No test asserts that a fix-applied round leaves a claude-relevant-checks row in the timing ledger or that Step 5 still wires checks helpers as the plan specified. Add integration-style tests if those paths remain in scope.
- **Suggested revision**: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] code-quality: python/test_checks.py
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Missing lint-fix non-fatal timing test Plan requested a lint-fix mirror of test_run_relevant_checks_timing_failure_is_non_fatal; only relevant-checks coverage exists. Add test_run_lint_fix_timing_failure_is_non_fatal.
- **Suggested revision**: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-dyn-timing-ledger-output.txt
- **Concern**: - **correctness** `python/checks.py:37-60` — `_record_checks_vendor_task` mirrors `_mark_step_ledger` env wiring (`IMPLEMENT_TMPDIR`, cleared `DESIGN_TMPDIR`) but does not hydrate `LARCH_TIMING_LEDGER` from `session-env.sh` the way `step_telemetry_mark` does (`python/timing.py:384-406`). If a session ever points the ledger elsewhere and a child process lacks that env var, vendor rows could land on a different ledger than round rows. This pattern predates the branch; low materiality unless custom ledger paths are in active use.
- **Suggested revision**: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-dyn-round-window-output.txt
- **Concern**: - **risk-integration** `python/test_review_and_fix.py:1893-2042` — The plan required wiring tests asserting Step 5 still routes through `checks.run_relevant_checks` / `checks.run_lint_fix` with `implement_tmpdir`; those tests were not added. Given #5540 removed that wiring, the gap is pre-existing plan drift rather than introduced by this diff, but it leaves the deferral behavior unguarded against future re-wiring mistakes.
- **Suggested revision**: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-dyn-gantt-labels-output.txt
- **Concern**: - **architecture** `python/checks.py:987-990`, `python/checks.py:2135-2138` — Using one fixed output basename per kind (`claude-relevant-checks.txt`, `claude-lint-fix.txt`) for every invocation is consistent with the plan’s generic task-kind surface, and label derivation via `_progress_derived_label` correctly yields `claude/relevant-checks` and `claude/lint-fix` for those basenames. Multiple ledger rows with the same label will overlap rather than stay blank; the cap issue above is the material risk, not the basename pattern itself.
- **Suggested revision**: Address the concern above.

### OOS_9: [OUT_OF_SCOPE] architecture
- **Reviewer**: dyn-dyn-gantt-labels-output.txt
- **Concern**: - **architecture** `python/timing.py:41`, `python/test_timing.py:1319-1333` — Allow-list entries `claude-relevant-checks` and `claude-lint-fix` match the emitted `--task-kind` values and pass allow-list tests without `unknown task-kind` warnings. No round/attempt/site encoding in the kind surface, as specified.
- **Suggested revision**: Address the concern above.

