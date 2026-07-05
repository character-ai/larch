### FINDING_1: Preserve the separate no-tools early-return path
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Repair Loop Risk
- **Severity**: important
- **Concern**: The pre-dispatch refactor must keep the distinct no-tools branch separate from structural fast-fail. If the new helper collapses everything into one `main-agent-required` path, no-tools runs can start returning the wrong `failure_reason` or `ledger_exit_code`, breaking the existing no-tools contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out control flow: (1) `fast_fail_reason = _lint_fix_fast_fail_reason(log_path)`; (2) only if `None`, optionally probe `claude_present`; (3) if `fast_fail_reason`, return `main-agent-required` with that reason and `ledger_exit_code=1`; (4) else if all tools absent, return `main-agent-required` with `failure_reason=None` and `ledger_exit_code=0`; (5) else continue dispatch. Keep fast-fail before binary probing and before `run_dir`/baseline capture.
  - From Cursor-Innovation: Keep if fast_fail_reason or no_tools, then failure_reason = fast_fail_reason (may be None) and ledger_exit_code = 1 only when fast_fail_reason is set. Add a structural-ruff-failure + all-tools-false test mirroring test_run_lint_fix_complexity_baseline_no_tools_fast_fail.
  - From Cursor-Pragmatic: Require `_lint_fix_fast_fail_reason` to return before the no-tools check (still before binary probing), keep `ledger_exit_code=1` for any fast-fail reason, and add a test mirroring `test_run_lint_fix_complexity_baseline_no_tools_fast_fail` using a plain structural ruff row with all tools false.
  - From Cursor-dyn-Repair Loop Risk: In approach step 2, state explicitly: keep `if fast_fail_reason or (not claude_present and not codex_present and not cursor_present)`; set `failure_reason=fast_fail_reason` only when non-None; set `ledger_exit_code=1` only when `fast_fail_reason` is set


### FINDING_2: Remove the PLR0911-only baseline carve-out and pin the test token
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-Repair Loop Risk
- **Severity**: important
- **Concern**: The plan needs to explicitly remove the `any(code != "PLR0911")` exclusion from baseline-shaped `(new)` detection and pin the renamed PLR0911 test to `complexity-baseline-regression`; otherwise `PLR0911 (new)` symbol-shaped rows still follow the external lint-fix path and plain Ruff regexes will not catch them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the baseline sub-helper, remove the `any(code != "PLR0911" for code in new_codes)` guard (keep metric regression matching first). Have baseline `(new)` rows, including PLR0911-only, return `complexity-baseline-regression`. Rename the test accordingly and assert `_assert_complexity_fast_fail` (or equivalent), not `structural-ruff-failure`.
  - From Cursor-Innovation: In _lint_fix_fast_fail_reason, drop the `any(code != "PLR0911")` guard (or treat PLR0911 (new) as complexity-baseline-regression). State this explicitly in the plan and assert failure_reason == complexity-baseline-regression in the renamed PLR0911 (new) test.
  - From Cursor-Pragmatic: State that fast-fail for that row comes from dropping the `any(code != "PLR0911")` guard (or an equivalent baseline `(new)` rule), and that the renamed PLR0911 test expects `failure_reason=="complexity-baseline-regression"` while parametrized plain-ruff cases expect `structural-ruff-failure`.
  - From Cursor-dyn-Repair Loop Risk: In the plan, add an explicit step: remove the PLR0911-only exclusion from complexity-baseline `(new)` detection so baseline `PLR0911 (new)` rows fast-fail


### FINDING_4: Add test coverage for three-part Ruff rows without a column
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan still needs an explicit test for the common `path:line: CODE` Ruff shape. If tests only cover `path:line:col: CODE`, a regex that requires a column can pass review and still miss live pre-commit output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add one parametrized or dedicated case per structural code using the three-part shape (e.g. python/app.py:12: C901 ...).
  - From Cursor-Pragmatic: Extend the parametrized structural tests (or add a dedicated case) for both row shapes per code, or fold both fixtures into the parametrize matrix.
  - From Cursor-Requirements: Add a parametrized lint-fix case for path:line: CODE (no column) for each structural code, asserting main-agent-required, structural-ruff-failure, ledger_exit_code == 1, and no _run_claude/_run_codex/_run_cursor calls.


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/implement/checks_lint_fix.py:404-408
- **Concern**: [SCOPE-REDUCTION] PLR0911 complexity-baseline (new) short-circuit mechanism unspecified. Scenario: The plan updates test_run_lint_fix_complexity_baseline_plr0911_new_uses_normal_fixer but never says to drop the any(code != "PLR0911") guard. That fixture uses path:symbol PLR0911 (new) with a complexity-baseline command, not path:line:col Ruff rows. Parametrized plain-Ruff tests alone would not catch leaving the guard in place, so PLR0911 baseline regressions could keep paying the external lint-fix loop.
- **Proposed resolution**: In approach step 2 or expected behavior, require removing the PLR0911-only exemption (or equivalent symbol-row matching). Pin the renamed test to failure_reason == complexity-baseline-regression and ledger_exit_code == 1 for the command-guarded PLR0911 (new) fixture.

