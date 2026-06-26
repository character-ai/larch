### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:100-105
- **Concern**: Test 2 fixture and setup remain incomplete versus Test 1. Scenario: Test 2 lists only a `(new)` regression row and never requires `python3 python/cli.py lint complexity-baseline` in the log fixture. `_is_complexity_baseline_regression_log` returns False without both the command substring and a regression row, so Test 2 never exercises the `(new)` fast-fail path. It also omits Test 1's `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called monkeypatches, so a broken matcher or ordering can reach dispatch and flake while outcome fields still look plausible.
- **Proposed resolution**: A mirror Test 1's setup in Test 2: add a "Build a log containing" block with the complexity-baseline command line plus a `(new)` row; repeat the three dispatch monkeypatches; keep at least one external tool present; assert the same explicit fast-fail fields as Test 1.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:117-122
- **Concern**: Test 4 log fixture still omits the complexity-baseline command guard. Scenario: Test 4 only lists a regression row. Without `python3 python/cli.py lint complexity-baseline` the detector returns False, `run_lint_fix` hits the no-tools early return (`failure_reason=None`, `ledger_exit_code=0` at `python/checks.py:2036`), and Test 4 either fails opaquely or passes vacuously without proving complexity-baseline ordering runs before that branch.
- **Proposed resolution**: Add the command guard line to Test 4's log fixture (same as Test 1), keep the regression row, call with all tools false, and assert Test 1's positive fast-fail contract (`failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, `ledger_ready is True`, etc.) plus the negated no-tools outcome.



### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:100-105
- **Concern**: Test 2 still omits the complexity-baseline command guard and the fail-if-called dispatch stubs. Scenario: The `(new)` fixture can pass without proving the detector saw a real complexity-baseline log, and a broken implementation can dispatch or match the wrong log shape without the test noticing
- **Proposed resolution**: Add `python3 python/cli.py lint complexity-baseline` to the fixture and keep `_run_claude`, `_run_codex`, and `_run_cursor` raising if called



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:107-115
- **Concern**: Test 3 omits the complexity-baseline command guard. Scenario: The tool-error case is not tied to the new detector. A matcher that ignores command context can still look correct, so the test does not prove tool errors stay on the normal fixer path
- **Proposed resolution**: Include `python3 python/cli.py lint complexity-baseline` in the log fixture before the `lint-complexity-baseline:` error line



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:117-122
- **Concern**: Test 4 omits the command guard and does not pin the full fast-fail contract. Scenario: The no-tools case can pass vacuously if the log never reaches the detector, and the current assertion only excludes the generic no-tools outcome instead of proving the new regression reason and ledger fields
- **Proposed resolution**: Add the complexity-baseline command guard to the fixture and assert `failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, and `ledger_ready is True`



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 2 fixture still omits the complexity-baseline command guard (prior rounds 3–4 accepted; plan not updated). Scenario: `test_run_lint_fix_complexity_baseline_new_identity_fast_fail` lists only a `(new)` row. `_is_complexity_baseline_regression_log` requires both `python/cli.py lint complexity-baseline` and a regression row, so the detector returns False, the fast-fail path never runs, and the `(new)` matcher plus ordering stay untested while the 600s lint-fix burn can return in production.
- **Proposed resolution**: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus a `(new)` row (e.g. `larch/core/proc.py:ProcRunner.run PLR0915 (new)`), matching Test 1’s fixture shape.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 4 fixture still omits the complexity-baseline command guard (prior rounds 3–4 accepted; plan not updated). Scenario: `test_run_lint_fix_complexity_baseline_no_tools_fast_fail` lists only a regression row. Without the command substring the detector returns False, `run_lint_fix` hits the no-tools branch at ~`python/checks.py:2036` (`failure_reason=None`, `ledger_exit_code=0`), and Test 4 cannot prove complexity-baseline ordering runs before that branch or guard the no-tools regression from round 1 FINDING_6.
- **Proposed resolution**: Add `python3 python/cli.py lint complexity-baseline` to the Test 4 log fixture alongside the regression row, then keep the Test 1 positive fast-fail assertions.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/test_checks.py
- **Concern**: Test 2 still lacks dispatch raise-if-called monkeypatches (round 4 FINDING_5 accepted; plan not updated). Scenario: Test 2 asserts “no dispatch” by reference to Test 1 but does not repeat Test 1’s `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called monkeypatches. If the `(new)` matcher or ordering regresses, dispatch can run (especially with a tool marked present), causing flakes, hangs, or a green test that never exercised fast-fail.
- **Proposed resolution**: Copy Test 1’s three dispatch monkeypatches into Test 2 and assert no dispatch helper ran.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:100-122
- **Concern**: Tests 2-4 still omit the `python3 python/cli.py lint complexity-baseline` command guard.. Scenario: Without the command substring, `_is_complexity_baseline_regression_log` returns False. Test 2 will not prove the `(new)` fast-fail, Test 3 will not prove tool errors stay on the normal fixer path under a real complexity-baseline run, and Test 4 can pass vacuously on the no-tools branch.
- **Proposed resolution**: Add the command guard to every fixture in Tests 2-4 before asserting the outcomes.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:117-122
- **Concern**: Test 4 only negates the generic no-tools outcome.. Scenario: A partial implementation that returns `main-agent-required` for the wrong reason can still satisfy the test, so the planned check does not prove `complexity-baseline-regression`, `ledger_exit_code=1`, or `ledger_ready is True` on the no-tools path.
- **Proposed resolution**: Mirror Test 1's positive assertions in Test 4, not just the negative no-tools assertion.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py:100-105
- **Concern**: Test 2 fixture still omits the complexity-baseline command guard. Scenario: Test 2 only lists a `(new)` regression row. `_is_complexity_baseline_regression_log` requires both `python/cli.py lint complexity-baseline` and a regression row, so the planned fixture returns False, never hits fast-fail, and a broken `(new)` matcher or ordering can still pass while the 600s lint-fix burn remains on real logs. Prior-round accepted fix is incomplete.
- **Proposed resolution**: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus the `(new)` row, mirroring Test 1.



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:100-105
- **Concern**: Test 2 still lacks dispatch monkeypatches. Scenario: Test 2 claims “no dispatch” by reference to Test 1 but does not repeat Test 1’s `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called monkeypatches. If the detector or ordering regresses, dispatch can run and the test may flake or pass on outcome fields alone. Prior-round FINDING_5 fix is incomplete.
- **Proposed resolution**: Add the same three dispatch monkeypatches and an explicit “no dispatch helper ran” assertion, as in Test 1.



### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py:117-122
- **Concern**: Test 4 fixture still omits the complexity-baseline command guard. Scenario: Test 4 lists only a regression row. Without the command substring the detector returns False, `run_lint_fix` hits the no-tools branch at `python/checks.py:2036` (`failure_reason=None`, `ledger_exit_code=0`), and Test 4 fails opaquely or passes vacuously without proving ordering before that branch. Prior-round accepted fix is incomplete.
- **Proposed resolution**: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus the regression row, mirroring Test 1.



### FINDING_14:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py:100-106
- **Concern**: Test 2 does not explicitly repeat Test 1's no-dispatch monkeypatches or the concrete fast-fail assertions.. Scenario: The plan only says "same fast-fail outcome contract as Test 1," so a broken `(new)` detector could still pass if dispatch runs or the assertions stay implicit.
- **Proposed resolution**: Carry over Test 1's `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called setup and spell out the same outcome assertions for the `(new)` case.



### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 2 fixture still omits the complexity-baseline command guard (prior round 4 FINDING_1 incomplete). Scenario: Planned Test 2 lists only a `(new)` row and never `python3 python/cli.py lint complexity-baseline`. `_is_complexity_baseline_regression_log` requires both the command substring and a regression row, so Test 2 never exercises fast-fail; a broken `(new)` matcher or ordering can pass while the command guard stays untested and real logs still burn the 600s lint-fix budget.
- **Proposed resolution**: Add `Build a log containing:` to Test 2 with `python3 python/cli.py lint complexity-baseline` plus a `(new)` row (e.g. `larch/core/proc.py:ProcRunner.run PLR0915 (new)`), matching Test 1’s fixture shape.



### FINDING_16:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 2 still lacks dispatch raise-if-called monkeypatches (prior round 4 FINDING_5 incomplete). Scenario: Test 2 says “assert the same contract as Test 1” but does not repeat Test 1’s `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called monkeypatches. If `(new)` matching or ordering regresses, dispatch can run and the test may flake, hang, or pass on outcome fields alone without proving no-dispatch fast-fail.
- **Proposed resolution**: Repeat Test 1’s three dispatch monkeypatches in Test 2 and assert no dispatch helper ran.



### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 3 fixture still omits the complexity-baseline command guard (prior round 4 FINDING_2 incomplete). Scenario: Planned Test 3 includes only `lint-complexity-baseline: ruff exited 2` with no regression row and no `python3 python/cli.py lint complexity-baseline`. The detector returns False without the command guard, so the test cannot prove “command present + tool error only → no fast-fail”; a detector that fast-fails on command alone would not be caught.
- **Proposed resolution**: Add `python3 python/cli.py lint complexity-baseline` to the Test 3 log fixture alongside the tool-error line and no regression row.



### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 4 fixture still omits the complexity-baseline command guard (prior rounds 3–4 FINDING_2/3 incomplete). Scenario: Planned Test 4 lists only a regression row without `python3 python/cli.py lint complexity-baseline`. The detector returns False, `run_lint_fix` hits the no-tools early return at `python/checks.py:2036` (`failure_reason=None`, `ledger_exit_code=0`), and Test 4 fails opaquely or passes vacuously without proving complexity-baseline ordering before that branch.
- **Proposed resolution**: Add `python3 python/cli.py lint complexity-baseline` to the Test 4 log fixture with the regression row, mirroring Test 1.



### FINDING_19:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Tests 2-4 never spell out the `python3 python/cli.py lint complexity-baseline` guard. Scenario: Only Test 1 includes the command-prefix fixture. Tests 2 and 4 would hit `_is_complexity_baseline_regression_log` as false and fail on the intended implementation, and Test 3 would no longer prove that complexity-baseline tool errors stay on the normal fixer path.
- **Proposed resolution**: Add the command guard to the log fixture bullets for Tests 2, 3, and 4.



### FINDING_20:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/test_checks.py
- **Concern**: Test 2 still leaves Claude/Cursor discovery to the host and does not say it reuses Test 1's no-dispatch setup. Scenario: With only "at least one tool marked present," the new-identity fast-fail test stays environment-dependent. A machine with a Claude binary on PATH can probe the wrong tier or dispatch real code before the new detector is proven.
- **Proposed resolution**: Pin `claude_present=False, codex_present=True, cursor_present=False` for Test 2, or explicitly say it reuses Test 1's `_run_*` raise guards.



