## Decision 1: Scope both rolled-up bugs in one plan
- **Question**: Should #4917 fix both OOS items or just one?
- **Resolution**: Fix both. OOS_1 (duplicate-code worker-failure test) and OOS_2 (ci_monitor duplicate `_gh_pr_checks`) ship in one plan / one PR. Each fix is small and independent.
- **Source**: user

## Decision 2: OOS_1 fix scope — test determinism plus production hardening
- **Question**: Fix only the test, or also harden production?
- **Resolution**: Do both.
  - (a) Make `test_worker_failure_exits_2` inject the worker failure deterministically, independent of real subprocess creation, so the pool-creation fallback cannot mask the simulated failure.
  - (b) Broaden the production pool-creation fallback in `_find_commonalities_fork` / `_find_commonalities_spawn` from `except PermissionError` to a broader `OSError` family, so real runs degrade to serial on any spawn-creation failure instead of crashing.
- **Source**: user

## Decision 3: OOS_2 fix direction — reuse gather_status's observation
- **Question**: Remove the duplicate query by reusing gather_status's observation, or keep it with a race-guard?
- **Resolution**: Reuse the checks observation `gather_status` already makes. Surface a "checks rollup empty" signal from that same query and drop the second independent `_checks_rollup_empty` call in `poll_ci`'s startup-deadline block. Removes the race and one `gh` call per poll iteration.
- **Source**: user

## Hard constraints (decided from codebase, not asked)
- `make py-test` must stay green; `make py-lint` must pass.
- Preserve public signatures of `monitor()`, `poll_ci()`, `gather_status()`, `checks_status()`. Keyword-only additions with defaults are allowed. `CiStatus` is a frozen dataclass, so any new field must carry a default to keep existing construction sites valid.
- Preserve classification behavior for all non-startup-deadline paths. Only the startup-deadline emptiness source changes.
- Existing startup-deadline tests that assert on duplicate-query consumption (`python/test_ci_monitor.py:735-944`) get updated to the single-query model. That is expected, not a regression.
- Broadening the duplicate-code fallback must not swallow real worker-result failures: `_collect_worker_results` still translates `future.result()` exceptions into `DuplicateCodeError` (exit 2). Only pool creation / submit failures degrade to serial.

## Non-goals
- No change to `empty_checks_grace` semantics or the duplicate-code parallel/serial chunking design.
- No broad `ci_monitor` or `duplicate_code` refactor beyond these two fixes.
