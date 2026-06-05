### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:1045-1065
- **Concern**: A1 scopes prose to the python selector/fence but A2 pins target shared Exit 3/4/6 bullets that still mandate ship-pr-state reads. Scenario: Exit 3 reads FAILED_RUN_ID and Exit 4 reads STALL_TRACKING/STALL_STEP from ship-pr-state.sh yet python/ship.py never writes those keys there (JSON + finalize-state.sh only); orchestrator follows stale bullets and misses stall/CI-fix inputs
- **Proposed resolution**: Add explicit UPDATED bullets for the shared post-invoke exit matrix (~1045-1065): dual-path wording (JSON/finalize-state for python; ship-pr-state where keys exist) and align A1 scope text with those lines

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:FINDING_7 / python/ship.py:633-637
- **Concern**: _persist_stall_metadata_if_needed always rewrites finalize-state for every STALLED result. Scenario: run_ship already writes stall_step tokens (e.g. merge path sets stall_step=merge at ship.py:635) but result.detail is free-form error text; main()-time rewrite can replace canonical STALL_STEP with a slug of merged.error and break Step 18a / stall-recovery enum routing
- **Proposed resolution**: Only call write_finalize_state when finalize-state.sh is missing or STALL_TRACKING is not already true; preserve existing stall_step when present

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_support.py:68-70
- **Concern**: Shared RecordingRunner spec mandates strict response exhaustion when responses is non-empty but most duplicate runners use permissive fallback after queue drain. Scenario: test_merge.py test_pr.py test_finalize.py and others return rc=0 for calls beyond len(responses); test_gh.py and test_push.py raise AssertionError — a single strict shared class breaks the majority suite or silently changes merge coverage
- **Proposed resolution**: Match the indexed-queue majority: after responses are exhausted return default CommandResult(rc=0); add optional strict=True only where test_gh.py/test_push.py need AssertionError — or drop consolidation and keep divergent local runners

### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:339-346
- **Concern**: python/ship.py:755-769. Scenario: Proposed `_persist_stall_metadata_if_needed` in `main()` runs on every STALLED result using the pre-run `ctx`, but `run_ship` already writes `finalize-state.sh` via `_write_terminal_state(working, …)` and other in-loop writers that carry `pr_number` / `merge_result`.
- **Proposed resolution**: CI-monitor, merge-cap, and pre-rebase stalls get a second write from stale `ctx`; `PR_NUMBER` and related keys in `finalize-state.sh` are wiped before Step 18. Limit the helper to gap paths only (e.g. `ensure_pr` `ShipError`), or skip when `finalize-state.sh` already has `STALL_TRACKING=true`, or return the final `RunContext` from `run_ship` and persist from that.
