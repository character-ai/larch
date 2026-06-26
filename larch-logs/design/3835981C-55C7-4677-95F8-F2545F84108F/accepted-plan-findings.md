### FINDING_1: Test 2 log fixture omits complexity-baseline command guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Test 2 (`test_run_lint_fix_complexity_baseline_new_identity_fast_fail`, `python/test_checks.py` ~100–105) lists only a `(new)` regression row and never includes `python3 python/cli.py lint complexity-baseline` in the log fixture. `_is_complexity_baseline_regression_log` requires both the command substring and a regression row, so the detector returns False, the fast-fail path never runs, and the `(new)` matcher plus ordering stay untested while a broken implementation can still pass and real logs can burn the 600s lint-fix budget.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A mirror Test 1's setup in Test 2: add a "Build a log containing" block with the complexity-baseline command line plus a `(new)` row; repeat the three dispatch monkeypatches; keep at least one external tool present; assert the same explicit fast-fail fields as Test 1.
  - From Codex-Arch: Add `python3 python/cli.py lint complexity-baseline` to the fixture and keep `_run_claude`, `_run_codex`, and `_run_cursor` raising if called
  - From Cursor-Innovation: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus a `(new)` row (e.g. `larch/core/proc.py:ProcRunner.run PLR0915 (new)`), matching Test 1’s fixture shape.
  - From Codex-Innovation: Add the command guard to every fixture in Tests 2-4 before asserting the outcomes.
  - From Cursor-Pragmatic: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus the `(new)` row, mirroring Test 1.
  - From Codex-Pragmatic: Carry over Test 1's `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called setup and spell out the same outcome assertions for the `(new)` case.
  - From Cursor-Requirements: Add `Build a log containing:` to Test 2 with `python3 python/cli.py lint complexity-baseline` plus a `(new)` row (e.g. `larch/core/proc.py:ProcRunner.run PLR0915 (new)`), matching Test 1’s fixture shape.
  - From Codex-Requirements: Add the command guard to the log fixture bullets for Tests 2, 3, and 4.


### FINDING_2: Test 2 lacks no-dispatch monkeypatches and pinned tool setup
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Test 2 asserts “no dispatch” by reference to Test 1 but does not repeat Test 1’s `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called monkeypatches, and may leave Claude/Cursor discovery environment-dependent with only “at least one tool marked present.” If the `(new)` matcher or ordering regresses, dispatch can run (especially with a tool marked present or a Claude binary on PATH), causing flakes, hangs, or a green test that never exercised fast-fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: A mirror Test 1's setup in Test 2: add a "Build a log containing" block with the complexity-baseline command line plus a `(new)` row; repeat the three dispatch monkeypatches; keep at least one external tool present; assert the same explicit fast-fail fields as Test 1.
  - From Codex-Arch: Add `python3 python/cli.py lint complexity-baseline` to the fixture and keep `_run_claude`, `_run_codex`, and `_run_cursor` raising if called
  - From Cursor-Innovation: Copy Test 1’s three dispatch monkeypatches into Test 2 and assert no dispatch helper ran.
  - From Cursor-Pragmatic: Add the same three dispatch monkeypatches and an explicit “no dispatch helper ran” assertion, as in Test 1.
  - From Codex-Pragmatic: Carry over Test 1's `_run_claude` / `_run_codex` / `_run_cursor` raise-if-called setup and spell out the same outcome assertions for the `(new)` case.
  - From Cursor-Requirements: Repeat Test 1’s three dispatch monkeypatches in Test 2 and assert no dispatch helper ran.
  - From Codex-Requirements: Pin `claude_present=False, codex_present=True, cursor_present=False` for Test 2, or explicitly say it reuses Test 1's `_run_*` raise guards.


### FINDING_3: Test 3 log fixture omits complexity-baseline command guard
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Test 3 (`python/test_checks.py` ~107–115) includes only a tool-error line (e.g. `lint-complexity-baseline: ruff exited 2`) with no `python3 python/cli.py lint complexity-baseline` command guard and no regression row. Without the command substring the detector returns False, so the test cannot prove “command present + tool error only → no fast-fail”; a matcher that ignores command context or fast-fails on command alone would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Include `python3 python/cli.py lint complexity-baseline` in the log fixture before the `lint-complexity-baseline:` error line
  - From Codex-Innovation: Add the command guard to every fixture in Tests 2-4 before asserting the outcomes.
  - From Cursor-Requirements: Add `python3 python/cli.py lint complexity-baseline` to the Test 3 log fixture alongside the tool-error line and no regression row.
  - From Codex-Requirements: Add the command guard to the log fixture bullets for Tests 2, 3, and 4.


### FINDING_4: Test 4 log fixture omits complexity-baseline command guard
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: blocking
- **Concern**: Test 4 (`test_run_lint_fix_complexity_baseline_no_tools_fast_fail`, `python/test_checks.py` ~117–122) lists only a regression row without `python3 python/cli.py lint complexity-baseline`. Without the command substring `_is_complexity_baseline_regression_log` returns False, `run_lint_fix` hits the no-tools early return at `python/checks.py:2036` (`failure_reason=None`, `ledger_exit_code=0`), and Test 4 fails opaquely or passes vacuously without proving complexity-baseline ordering runs before that branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the command guard line to Test 4's log fixture (same as Test 1), keep the regression row, call with all tools false, and assert Test 1's positive fast-fail contract (`failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, `ledger_ready is True`, etc.) plus the negated no-tools outcome.
  - From Codex-Arch: Add the complexity-baseline command guard to the fixture and assert `failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, and `ledger_ready is True`
  - From Cursor-Innovation: Add `python3 python/cli.py lint complexity-baseline` to the Test 4 log fixture alongside the regression row, then keep the Test 1 positive fast-fail assertions.
  - From Cursor-Pragmatic: Add `Build a log containing:` with `python3 python/cli.py lint complexity-baseline` plus the regression row, mirroring Test 1.
  - From Codex-Innovation: Add the command guard to every fixture in Tests 2-4 before asserting the outcomes.
  - From Cursor-Requirements: Add `python3 python/cli.py lint complexity-baseline` to the Test 4 log fixture with the regression row, mirroring Test 1.
  - From Codex-Requirements: Add the command guard to the log fixture bullets for Tests 2, 3, and 4.


### FINDING_5: Test 4 does not assert the positive fast-fail contract
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Innovation
- **Severity**: important
- **Concern**: Test 4 only negates the generic no-tools outcome instead of pinning Test 1’s positive fast-fail contract. A partial implementation that returns `main-agent-required` for the wrong reason can still satisfy the test, so it does not prove `failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, or `ledger_ready is True` on the no-tools path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add the command guard line to Test 4's log fixture (same as Test 1), keep the regression row, call with all tools false, and assert Test 1's positive fast-fail contract (`failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, `ledger_ready is True`, etc.) plus the negated no-tools outcome.
  - From Codex-Arch: Add the complexity-baseline command guard to the fixture and assert `failure_reason == "complexity-baseline-regression"`, `ledger_exit_code == 1`, and `ledger_ready is True`
  - From Codex-Innovation: Mirror Test 1's positive assertions in Test 4, not just the negative no-tools assertion.
  - From Cursor-Innovation: Add `python3 python/cli.py lint complexity-baseline` to the Test 4 log fixture alongside the regression row, then keep the Test 1 positive fast-fail assertions.

