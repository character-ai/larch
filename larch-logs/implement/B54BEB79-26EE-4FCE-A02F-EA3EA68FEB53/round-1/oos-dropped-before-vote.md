### OOS_1: [OUT_OF_SCOPE] Command guard rejects versioned or absolute Python paths
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `_COMPLEXITY_BASELINE_COMMAND_RE` (`python/checks.py:63-64`) accepts only a bare `python`/`python3` prefix before `python/cli.py`, not a versioned interpreter such as `python3.12` or an absolute path like `/usr/bin/python3`. This is a pre-existing guard-shape limitation, not introduced by this branch’s regression-row logic; it only matters when `PYTHON` is overridden locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: widen the command guard to tolerate `\S+/python\d*(\.\d+)?` or similar if that environment is supported.

### OOS_2: [OUT_OF_SCOPE] No negative test for regression row without command guard
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `python/test_checks.py` — no test asserts that a regression-shaped line **without** the `python/cli.py lint complexity-baseline` command guard does **not** fast-fail. All four new fixtures include the command, so removing or breaking the command check in `_is_complexity_baseline_regression_log` would not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a negative test with only a regression row and assert normal fixer dispatch (or at least `failure_reason != "complexity-baseline-regression"`).
  - From cursor-specialist-testing-output.txt: Add a small test (or parametrize case) with only `larch/core/proc.py:ProcRunner.run PLR0913 metric 8 > baseline 7` and assert `run_lint_fix` does not return `failure_reason=="complexity-baseline-regression"` (and may attempt normal fixer dispatch when tools are present).

### OOS_3: [OUT_OF_SCOPE] Regression row format duplicated across modules
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/checks.py:56-75` — regression row format is duplicated as regex, coupled to `find_regressions` string formatting in `lint_complexity_baseline.py:270-274`. A future output-format change could desync detector and producer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Consider a shared formatter constant or a cross-module contract test (outside this feature’s required scope).

### OOS_4: [OUT_OF_SCOPE] Bounded tail read may miss command guard in truncated prefix
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/checks.py:1421-1430` — bounded 60KB tail read can miss the command guard when it appears only in truncated-away prefix while regression rows remain in the tail (unlikely for typical `py-lint-main` failures where complexity output is near the log end).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optionally also match `lint-complexity-baseline:` stderr prefix as a secondary command signal if this edge case is observed in production.

### OOS_5: [OUT_OF_SCOPE] Generic no-tools test lacks explicit ledger assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `python/test_checks.py:968-989` — `test_run_lint_fix_no_tools` predates this change and only asserts `status == "main-agent-required"`, not `failure_reason is None` or `ledger_exit_code == 0`. The new no-tools fast-fail test (Test 4) covers the complexity-specific contract, but the generic no-tools path still lacks explicit ledger assertions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional hardening of the pre-existing test; not required for this feature to ship correctly.

