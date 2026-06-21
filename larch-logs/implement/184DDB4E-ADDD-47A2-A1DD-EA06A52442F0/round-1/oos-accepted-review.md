### OOS_1: [OUT_OF_SCOPE] correctness: broad `OSError` handler wraps pool teardown in `duplicate_code.py`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The plan limits serial fallback to `ProcessPoolExecutor` construction and `executor.submit` failures, but `except OSError` wraps the full `with ProcessPoolExecutor` block, including `_collect_worker_results` and pool teardown. Worker failures still propagate as `DuplicateCodeError`, but a post-success teardown `OSError` can trigger an unnecessary serial rerun; in the correctness path, teardown `OSError` can be caught and serial fallback can return success (exit 0) instead of the intended failure exit (exit 2).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Narrow OSError handling to ProcessPoolExecutor construction and executor.submit only; call _collect_worker_results outside the OSError handler
  - From cursor-specialist-testing-output.txt: Narrow the handler to `ProcessPoolExecutor(...)` construction and each `executor.submit(...)` call (or re-raise after a successful `_collect_worker_results` return).


