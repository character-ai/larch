## Proposed Design Outline

### Goals
- Make `test_worker_failure_exits_2` deterministic whether or not the sandbox allows process spawning.
- Make the codex/cursor stub-timeout flake (`test_codex_launch_does_not_leak_openai_api_key` and its ~20 siblings) robust under suite load.
- Keep `duplicate_code.py` and `launch_review.py` production behavior unchanged.

### Non-goals
- Do not remove or weaken the `PermissionError` in-process fallback in `duplicate_code.py`.
- Do not change production `--timeout` defaults or launcher timeout semantics.
- Do not touch the deliberate timeout-rejection tests (`--timeout 0` / `--timeout 1` / `--timeout abc`).

### Approach sketch
- Item 1: in the test, stub `duplicate_code.ProcessPoolExecutor` with a no-spawn fake so the patched `_collect_worker_results` is always reached; this forces the worker path and makes the test fully hermetic (no real subprocess, no PermissionError fallback). Keep the existing failure-injection monkeypatch.
- Item 2: replace `--timeout 2` in every success-path subprocess `_run([...])` test with one shared generous timeout constant; leave the rejection tests untouched.
- Add short comments documenting the sandbox-spawn and cold-start-under-load rationale.
- Source changes are permitted but not needed: the source behavior is correct, so both fixes stay in the test files.

### Surfaces in scope
- `python/test_duplicate_code.py` (Item 1)
- `python/test_launch_review.py` (Item 2)

### Open questions
- None.
