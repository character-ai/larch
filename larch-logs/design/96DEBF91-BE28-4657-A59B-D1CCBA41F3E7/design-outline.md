## Proposed Design Outline

### Goals
- Fix OOS_1: make `test_worker_failure_exits_2` deterministic, and harden the duplicate-code pool-creation fallback so real runs degrade to serial on any spawn-creation failure.
- Fix OOS_2: drop the duplicate `_gh_pr_checks` by reusing the checks observation `gather_status` already makes to drive the startup deadline.
- Add regression tests for both fixes; keep `make py-test` and `make py-lint` green.

### Non-goals
- No change to `empty_checks_grace` semantics or the duplicate-code parallel/serial chunking design.
- No broad `ci_monitor` or `duplicate_code` refactor.
- No public signature breakage for `monitor` / `poll_ci` / `gather_status` / `checks_status`.

### Approach sketch
- OOS_1 prod: broaden `except PermissionError` to an `OSError`-family fallback in `_find_commonalities_fork` / `_find_commonalities_spawn` (`python/duplicate_code.py`), keeping `_collect_worker_results` translation of real worker failures intact.
- OOS_1 test: inject the simulated worker failure at a point that always executes (independent of real subprocess creation), so the broadened fallback cannot mask it; add a fallback-degrades-to-serial regression test.
- OOS_2: surface a "checks rollup empty" bit from the same query `gather_status` runs, and have `poll_ci`'s startup-deadline block read it instead of calling `_checks_rollup_empty` again (`python/ci_monitor.py`).
- Likely vehicle: a defaulted `checks_empty` field on the frozen `CiStatus` dataclass; the default preserves existing construction sites.

### Surfaces in scope
- `python/duplicate_code.py`, `python/test_duplicate_code.py`
- `python/ci_monitor.py`, `python/test_ci_monitor.py`

### Open questions
- None.
