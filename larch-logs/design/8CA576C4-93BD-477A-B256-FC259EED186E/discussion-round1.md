## Decision 1: Fix scope — source changes permitted
- **Question**: Should the fix stay test-only, or may it also change source (`duplicate_code.py` / `launch_review.py`)?
- **Resolution**: Source changes are permitted, but not required. Prefer the minimum change per item. The plan should still keep production behavior intact unless a source edit is genuinely the cleaner fix.
- **Source**: user

## Decision 2: Item 2 timeout-fix breadth — file-wide
- **Question**: Bump only the named test, or all sibling success-path subprocess stub tests sharing `--timeout 2`?
- **Resolution**: Bump every success-path subprocess stub test in `python/test_launch_review.py` (the ~20 `_run([... "--timeout", "2" ...])` call sites) to a shared generous timeout. Leave the deliberate rejection tests (`--timeout 0` / `--timeout 1` / `--timeout abc`) untouched.
- **Source**: user

## Decision 3: Item 1 root cause (codebase-confirmed)
- **Question**: Why does `test_worker_failure_exits_2` return 8 instead of 2 in some environments?
- **Resolution**: `_find_commonalities_fork` / `_find_commonalities_spawn` wrap the worker pool in `except PermissionError: -> _find_common_chunk_with(...)`. In a sandbox that denies process spawning, `ProcessPoolExecutor` raises `PermissionError`, the fallback runs real in-process duplicate detection on the 3 identical modules, and `duplicate_code_main` returns `8` (pylint refactor bitmask). The monkeypatched `_collect_worker_results` is never reached, so the test only passes when the environment allows spawning.
- **Source**: codebase

## Decision 4: Hard constraints and non-goals
- **Question**: What must not break?
- **Resolution**:
  - Do NOT remove or weaken the `PermissionError` in-process fallback in `duplicate_code.py` (it is correct sandbox behavior).
  - Do NOT change production `--timeout` defaults or the launcher timeout semantics in `launch_review.py`.
  - Do NOT touch the deliberate timeout-rejection tests (`--timeout 0` / `--timeout 1` / `--timeout abc`).
  - Keep every existing `test_launch_review.py` and `test_duplicate_code.py` test green; `make py-lint` and `make py-test` must pass.
  - Both items ship in one plan / PR (both are `python/test_*.py` harness-stability fixes).
- **Source**: codebase
