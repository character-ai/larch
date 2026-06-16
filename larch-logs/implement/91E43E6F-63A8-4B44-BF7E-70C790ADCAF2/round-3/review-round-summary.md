# Review Round 3

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing pytest parity and plan-mandated coverage in test_agent_waterfall.py
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Plan-mandated pytest parity with the retired bash harness is incomplete in `python/test_agent_waterfall.py`. Missing or thin coverage includes: malformed NDJSON slot-row validation (`_load_slots()` reject paths for bad JSON, invalid tool, empty slot, agent/prompt mutual exclusion, non-string agent schema) with rc=2, no stub launches, and no paths-file written; dyn-* `STATIC_DISPATCH_OK` vs `DYNAMIC_DISPATCH_OK` split on partial failure (mixed static+dynamic panel could emit wrong dispatch OK KVs); optional metadata passthrough (`--diff-file`, `--commit-count`, `--plan-file`) on launcher argv; TAB/CR flattening in dropped-slots sidecar fields; and a dedicated aggregate-alternation invalid-ERE test. Regressions in slot validation, dispatch-flag bookkeeping, metadata forwarding, field flattening, or ERE handling could ship while `make test-dispatch-with-waterfall` stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Teardown may signal stale or reused PIDs via _DISPATCH_LAUNCHES
- **Reviewer(s)**: dyn-teardown-safety-output.txt
- **Severity**: blocking
- **Concern**: `python/agent_waterfall.py:412-426,400-404,382-388` — Teardown keeps every launch in `_DISPATCH_LAUNCHES` until the end of `dispatch_waterfall`, but `_reap_phase` only removes entries from `_ACTIVE_LAUNCHES`. On SIGTERM/atexit, `_kill_active_launches` still calls `_terminate_launch` for already-reaped slots, which runs `os.killpg(pid, SIGTERM)` and a recursive `pgrep -P` descendant sweep using the stored `launch.process.pid`. After `wait()` that PID may be stale or reused, so cancellation can signal an unrelated process group or its children. The retired bash cleared `pids=()` after each phase wait, so its trap only targeted still-running launchers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-teardown-safety-output.txt: Drop each `PhaseLaunch` from `_DISPATCH_LAUNCHES` in `_reap_phase` after a successful `wait()` (mirror bash `pids=()`), or skip `_terminate_launch` when `launch.process.poll() is not None`. Keep `_DISPATCH_LAUNCHES` limited to in-flight launchers only.


### FINDING_2: Phase 2/3 launch-all-then-collect concurrency untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Phase 2/3 launch-all-then-one-collect concurrency is not tested; only phase 1 is pinned (`test_phase1_launches_all_before_single_collect`). Serial per-slot collection in phase 2 or 3 would change fallback ordering and `ALL_OUTPUT_FILES` alignment without CI failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


