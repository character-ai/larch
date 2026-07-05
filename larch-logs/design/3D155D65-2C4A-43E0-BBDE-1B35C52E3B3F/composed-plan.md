## Plan

## Goal

Short-circuit lint-fix repair when the checks log contains structural Ruff failures that external automated fixers cannot fix safely.

Structural codes in scope:

- `C901`
- `PLR0911`
- `PLR0912`
- `PLC0415`

## Approach

1. Add a small, line-anchored structural Ruff classifier in `python/larch/implement/checks_lint_fix.py`.
   - Match real diagnostic rows, not prose mentions.
   - Cover normal Ruff rows such as `path.py:12:5: PLR0912 ...` and `path.py:12: PLR0912 ...` (no column).
   - Cover complexity-baseline rows such as `path.py:symbol C901 (new)` and `path.py:symbol PLR0912 metric 14 > baseline 12`.
   - Keep the rule set module-local with a typed `Final` constant.

2. Replace the current narrow `complexity_baseline_regression` decision near the pre-dispatch block with an explicit fast-fail path.

   Exact control flow:
   - `fast_fail_reason = _lint_fix_fast_fail_reason(log_path)` (runs after log validation and empty-log check, before binary probing, `run_dir` creation, git baseline capture, prompt composition, or external dispatch).
   - If `fast_fail_reason` is not `None`: return `FixOutcome(status="main-agent-required", failure_reason=fast_fail_reason, ledger_exit_code=1, ...)`.
   - Else: probe `claude_present` only if still `None`.
   - Then `if not claude_present and not codex_present and not cursor_present`: return `FixOutcome(status="main-agent-required", failure_reason=None, ledger_exit_code=0, ...)`.
   - Else: continue dispatch as today.

   The no-tools branch stays separate and retains `failure_reason=None` and `ledger_exit_code=0`.

3. Remove the `PLR0911`-only exclusion from baseline `(new)` detection.
   - In the baseline sub-helper, drop the `any(code != "PLR0911" for code in new_codes)` guard.
   - `PLR0911 (new)` in the complexity-baseline format returns `complexity-baseline-regression`.

4. Preserve normal automated dispatch for non-structural failures.
   - Do not fast-fail Pyright errors.
   - Do not fast-fail Ruff codes outside the scoped set.
   - Do not fast-fail complexity-baseline tool errors without a matching structural row.

## Files to modify/create

### UPDATED: python/larch/implement/checks_lint_fix.py

Add:

- `_STRUCTURAL_RUFF_CODES: Final[frozenset[str]]`
- A compiled line regex matching both `path:line:col: CODE` and `path:line: CODE` Ruff row shapes.
- A helper `_lint_fix_fast_fail_reason(log_path: Path) -> str | None`.

Expected behavior of `_lint_fix_fast_fail_reason`:

- Return `None` when the log cannot be read.
- Return `None` when no matching structural row exists.
- Return `complexity-baseline-regression` for complexity-baseline cases (metric regression or `(new)` rows including PLR0911-only).
- Return `structural-ruff-failure` for plain Ruff diagnostics with scoped structural codes.

Drop the `any(code != "PLR0911" for code in new_codes)` guard from the baseline `(new)` detection path.

Refactor the existing `_is_complexity_baseline_regression_log` into `_lint_fix_fast_fail_reason` as a sub-helper, or inline it; either produces the same behavior.

### UPDATED: python/tests/implement/test_checks.py

Add or update focused tests:

- Parametrize normal Ruff diagnostics for `C901`, `PLR0911`, `PLR0912`, and `PLC0415`.
  - Cover both row shapes: `path:line:col: CODE` and `path:line: CODE` (no column).
  - Assert no `_run_claude`, `_run_codex`, or `_run_cursor` call occurs.
  - Assert `outcome.status == "main-agent-required"`.
  - Assert `outcome.failure_reason == "structural-ruff-failure"`.
  - Assert `outcome.ledger_ready is True`.
  - Assert `outcome.ledger_exit_code == 1`.
  - Assert runner calls only contain the existing timing record path.

- Rename `test_run_lint_fix_complexity_baseline_plr0911_new_uses_normal_fixer`.
  - New name reflects that PLR0911 `(new)` baseline rows now fast-fail.
  - Assert `failure_reason == "complexity-baseline-regression"` and `ledger_exit_code == 1`.
  - Assert no dispatch functions were called.

- Add a no-tools + structural ruff test mirroring `test_run_lint_fix_complexity_baseline_no_tools_fast_fail`.
  - Log contains a plain structural Ruff row; all tool flags are `False`.
  - Assert `failure_reason == "structural-ruff-failure"` (fast-fail beats no-tools).

- Add a false-positive guard.
  - A log that only mentions `C901` or `PLR0912` in prose (not as a diagnostic row) still uses normal fixer dispatch.
  - A log with a non-structural Ruff code such as `E501` still uses normal fixer dispatch.

## Edge cases

- Logs may be truncated to `_PROMPT_TAIL_BYTES`. Use the same bounded read behavior as the existing classifier.
- Ruff output may include `path:line:col: CODE message` or `path:line: CODE message`. The regex must match both.
- File paths should be conservative. Prefer a pattern that requires a valid path prefix before the line number.
- Keep `PLC0415` separate from `lint_complexity_baseline.COMPLEXITY_CODES` since it is not a complexity-baseline code.
- The fast-fail check is independent of external tool availability. It runs before binary probing.

## Failure modes

- A broad regex could route normal fixable failures to main-agent edit. Mitigate with line-anchored path diagnostics only.
- A narrow regex (column required) could miss `path:line: CODE` pre-commit output. Cover both shapes in tests.
- Collapsing the no-tools branch into the fast-fail branch would change `failure_reason` and `ledger_exit_code` for no-tools runs. Keep them separate per the explicit control flow above.
- Losing ledger fields would break repair-loop routing. Assert ledger fields in the new tests.

## Testing strategy

Run focused tests first:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "lint_fix and (structural or complexity_baseline)"
```

Then run changed-file lint and tests:

python3 -m ruff check python/larch/implement/checks_lint_fix.py python/tests/implement/test_checks.py
python3 -m pytest python/tests/implement/test_checks.py

If available in the working environment, finish with relevant checks:

python3 python/cli.py checks run-relevant

confidence: high

## Acceptance

Run focused tests first:

```bash
python3 -m pytest python/tests/implement/test_checks.py -k "lint_fix and (structural or complexity_baseline)"
```

Then run changed-file lint and tests:

python3 -m ruff check python/larch/implement/checks_lint_fix.py python/tests/implement/test_checks.py
python3 -m pytest python/tests/implement/test_checks.py

If available in the working environment, finish with relevant checks:

python3 python/cli.py checks run-relevant

confidence: high

review_status: complete
rounds_completed: 2
difficulty: MODERATE
mechanical_churn: false
diff_lines: 185
