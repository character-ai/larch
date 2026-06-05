### FINDING_1: Post-invoke exit matrix still points python path at stale ship-pr-state keys
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The implement skill prose scopes A1 to the python selector/fence, but the shared Exit 3/4/6 bullets still require reading keys from `ship-pr-state.sh`. The python implementation records these values through JSON/finalize-state instead, so the orchestrator can miss failed-run, stall, or CI-fix inputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add explicit UPDATED bullets for the shared post-invoke exit matrix (~1045-1065): dual-path wording (JSON/finalize-state for python; ship-pr-state where keys exist) and align A1 scope text with those lines


### FINDING_2: STALLED finalize-state can be overwritten with stale or degraded metadata
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Concern**: `_persist_stall_metadata_if_needed` runs for every `STALLED` result from `main()` using the pre-run context. Since `run_ship` and in-loop writers may already have written canonical stall metadata and final context such as `PR_NUMBER`, this second write can replace canonical `STALL_STEP` values with free-form detail slugs or wipe PR/merge-related keys before Step 18.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Only call write_finalize_state when finalize-state.sh is missing or STALL_TRACKING is not already true; preserve existing stall_step when present
  - From Cursor-Pragmatic: CI-monitor, merge-cap, and pre-rebase stalls get a second write from stale `ctx`; `PR_NUMBER` and related keys in `finalize-state.sh` are wiped before Step 18. Limit the helper to gap paths only (e.g. `ensure_pr` `ShipError`), or skip when `finalize-state.sh` already has `STALL_TRACKING=true`, or return the final `RunContext` from `run_ship` and persist from that.


### FINDING_3: Shared RecordingRunner strict exhaustion conflicts with most existing tests
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The proposed shared `RecordingRunner` contract requires strict response exhaustion when responses are non-empty, but most existing duplicate runners fall back to a default successful command after their queued responses are drained. Consolidating into one strict shared class would either break the majority of tests or alter coverage semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Match the indexed-queue majority: after responses are exhausted return default CommandResult(rc=0); add optional strict=True only where test_gh.py/test_push.py need AssertionError — or drop consolidation and keep divergent local runners

