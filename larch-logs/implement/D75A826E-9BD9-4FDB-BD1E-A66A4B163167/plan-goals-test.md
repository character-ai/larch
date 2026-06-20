## Goal
Implement issue #4923: [IMPLEMENTING] [OOS] Local test/harness instability: duplicate-code worker + launch-review timeout (2 items).

## Implementation Plan
## Plan

Fix two flaky harness tests surfaced during `/implement` validation (issue #4923). Both are test-determinism problems; the underlying source behavior is correct. Source changes are permitted but not needed, so the fix stays in the two test files.

**Approach**

- Keep the fix test-only.
- Do not change `python/duplicate_code.py` or launcher timeout semantics.
- Do not weaken the `PermissionError` fallback in `duplicate_code.py`. It is correct production behavior for sandboxes that deny process spawning.
- Do not touch deliberate timeout rejection cases: `--timeout 0`, `--timeout 1`, or `--timeout abc`.

**Root causes**

- Item 1: `test_worker_failure_exits_2` runs with `--jobs 2`, so `_find_commonalities` enters `_find_commonalities_fork` / `_find_commonalities_spawn`. Both wrap the worker pool in `except PermissionError: -> _find_common_chunk_with(...)`. In a sandbox that denies process spawning, `ProcessPoolExecutor` raises `PermissionError`, the fallback runs real in-process duplicate detection on the 3 identical modules, and `duplicate_code_main` returns `8` (pylint refactor bitmask). The monkeypatched `_collect_worker_results` is never reached, so the test passes only when the environment allows spawning.
- Item 2: the inner `--timeout 2` bounds the vendor stub child. A freshly spawned stub can exceed 2s under serial-suite cold-start load, so the launcher kills it and returns non-zero, failing `assert proc.returncode == 0`. The isolated rerun passed in 0.62s, confirming a load-sensitive timeout rather than a logic bug.

### UPDATED: python/test_duplicate_code.py

- In `test_worker_failure_exits_2`, add a small no-spawn fake for `duplicate_code.ProcessPoolExecutor`.
- The fake should:
  - accept `*args` and `**kwargs`, including `max_workers` and `mp_context`;
  - implement `__enter__` and `__exit__`;
  - implement `submit(...)` and return a simple object.
- Monkeypatch `duplicate_code.ProcessPoolExecutor` to that fake before calling `duplicate_code_main`.
- Keep the existing `_collect_worker_results` monkeypatch that raises `DuplicateCodeError`.
- Add a short comment that the fake prevents sandbox spawn denial from taking the `PermissionError` fallback path before `_collect_worker_results` is reached.
- Keep the monkeypatch local to `test_worker_failure_exits_2`.
- Assert the same outcomes: return code is `2`; stderr contains `worker failed`.

### UPDATED: python/test_launch_review.py

- Add one shared constant near `REPO_ROOT` / `CLI`, for example `STUB_AGENT_TIMEOUT = "20"`, with a short comment explaining that subprocess stub tests can cold-start slowly under suite load, so the inner stub-agent timeout must be generous.
- Replace the success-path subprocess `_run([... "--timeout", "2" ...])` literals with the shared constant. Scope the replacement to the `--timeout` argv pair only.
- Cover the success-path stub tests that launch codex or cursor subprocesses, including: basic codex wrapper launch; basic cursor launch; cursor sidecar status; transient retry success; degraded cursor response; invalid token-budget tests that still run the vendor stub; empty-result retry integration; codex home and add-dir success paths; `test_codex_launch_does_not_leak_openai_api_key`; parallel cursor launches; quota, transient exhaustion, and vendor diagnostics subprocess cases; CLI cap-hit subprocess cases.
- Leave deliberate parser and rejection tests unchanged: `test_parser_rejects_invalid_timeout`, `test_parser_rejects_mutually_exclusive_prompts`, and the `--timeout 0` / `--timeout abc` override cases.
- Do not change `_run(..., timeout=60)`. That is the outer subprocess cap.

**Edge cases**

- A sandbox may deny process creation before any future is collected. The fake executor prevents real process creation, so the test reaches the intended patched failure path.
- The `PermissionError` fallback path is still exercised by production; this plan does not remove or change it.
- Do not rewrite retry-counter or state-file assertions that compare against the literal `"2"` (for example `assert state.read_text().strip() == "2"`). The replacement targets only the `--timeout` argv pair inside `_run([...])`.
- Keep direct `argparse.Namespace(timeout="2")` and in-process `timeout_seconds=2` tests unchanged; the flake is specific to the subprocess `_run([...])` cold-start path.
- The constant must be a string because CLI args are string lists.

**Failure modes**

- If a success-path `_run([... "--timeout", "2" ...])` call is missed, the timeout flake may remain there.
- If a deliberate timeout-rejection case is changed to the new constant, parser coverage weakens.
- If the fake executor itself raised `PermissionError`, the duplicate-code test could still hit the production fallback and return `8`; the fake must not raise.

**Testing strategy**

- Run the focused duplicate-code test: `cd python && python3 -m pytest test_duplicate_code.py::test_worker_failure_exits_2 -q`.
- Run the launch-review file: `cd python && python3 -m pytest test_launch_review.py -q`.
- Run Python validation: `make py-lint` and `make py-test`.
- Run full lint because repo rules require it: `make lint`.

## Acceptance

- `test_worker_failure_exits_2` returns `2` and prints `worker failed` deterministically, whether or not the environment allows process spawning, and spawns no real subprocess.
- `test_codex_launch_does_not_leak_openai_api_key` and the other success-path subprocess stub tests no longer trip the inner timeout under serial-suite cold-start load; the deliberate timeout-rejection tests still reject as before.
- `python/duplicate_code.py` and `python/launch_review.py` source are unchanged; the `PermissionError` fallback and production `--timeout` semantics are intact.
- No `== "2"` retry-counter or state-file assertion is altered.
- `make py-lint`, `make py-test`, and `make lint` pass.

diff_lines: 42

## Test plan
(no test plan section in plan-file)
