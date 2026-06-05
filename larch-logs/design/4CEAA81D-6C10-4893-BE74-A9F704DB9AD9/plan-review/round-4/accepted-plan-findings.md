### FINDING_1: Finalize-state gap-fill can clobber existing keys
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned gap-fill says to merge/preserve finalize-state keys, but the available writer rebuilds state from `RunContext`, so merged or pre-existing keys can be dropped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify a merge writer (e.g. write_finalize_state_merged(path, base, overrides) or ctx hydration from read_finalize_state + ShipResult + ship-pr-state) instead of implying write_finalize_state performs dict merge
  - From Codex-Arch: Add a small dict-based finalize-state writer, or extend write_finalize_state to accept merged state data and use it for both RunContext serialization and gap-fill preservation
  - From Codex-Pragmatic: Add a minimal mapping-based atomic writer or extend write_finalize_state to accept the merged dict; validate key syntax and newline-free values, then add a preservation regression
  - From Codex-Requirements: Add a dict-based atomic finalize-state writer or extend write_finalize_state to accept a merged dict; test preservation with an extra pre-seeded key


### FINDING_2: Invalid tmpdir path can still receive journal writes
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: The invalid-tmpdir STALLED path is intended to be JSON-only/no-write, but `emit_result` can still append a journal when `--run-id` is present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Skip journal append unless ctx.tmpdir passes the same allowed-root check, or pass a journal_allowed flag from main; add the invalid-tmpdir regression to assert no finalize-state and no journal sidecar


### FINDING_3: Python continuation keys are read from the wrong state file
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-pin-coherence
- **Severity**: important
- **Concern**: Planned boundary/Exit 4 prose assigns some Python continuation keys to `finalize-state.sh` even though Python persists them in `ship-pr-state.sh`, so orchestrator reads can miss values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split Exit 4 python reads: STALL_TRACKING/STALL_STEP from finalize-state.sh (JSON detail fallback when absent); RESUME_PHASE/CALLER_KIND from ship-pr-state.sh. Add RESUME_PHASE/CALLER_KIND to the post-invoke scoped ship-pr-state key list (~L1045). Mirror in test-implement-structure.sh A2b pins.
  - From Codex-dyn-pin-coherence: Change the boundary wording to stall/PR fields from finalize-state.sh and PHASE/OOS_PENDING/FORKED_TARGET/REPO_UNAVAILABLE from ship-pr-state.sh; scope any structural assertion to that boundary window


### FINDING_4: Stall metadata can be lost during restore-finalize-state
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Python can write stall metadata to `finalize-state.sh`, but Step 18b may later restore from `ship-pr-state.sh`, whose missing stall keys default to false and clobber the stall state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the Python path restore-safe: skip restore-finalize-state.sh when the Python driver already wrote finalize-state.sh, or update restore-finalize-state.sh to preserve existing finalize-state STALL_TRACKING=true and STALL_STEP when ship-pr-state.sh lacks those keys. Add a structural/unit pin for this handoff.


### FINDING_5: quiet_init path formatting can produce wrong quiet log paths
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `quiet_init()` does not clearly require formatting the quiet log template with script/pid and resolving tmpdir like the shell implementation, risking literal template paths or wrong log directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Implementer may join tmpdir without substituting {script} and {pid}, yielding a literal larch-quiet-{script}-{pid}.log path; quiet logs miss run-log publish patterns and IMPLEMENT_TMPDIR-only invocations get wrong log dirs In quiet_init(), mirror scripts/lib-quiet.sh:37: resolve tmpdir from IMPLEMENT_TMPDIR then TMPDIR (and optionally ctx.tmpdir via main() setdefault before the call); format PATH_QUIET_LOG_TEMPLATE with script=ship.py (or Path(argv[0]).name), pid=os.getpid(), tmpdir=resolved; add a unit test asserting the path shape matches larch-quiet-ship.py-<pid>.log


### FINDING_6: Python OOS re-entry conflicts with unsupported --resume-phase
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The OOS checkpoint still instructs re-entry with `--resume-phase pr-create`, but `ship.py` does not support that flag, so a successful checkpoint can be followed by an argparse failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add a Python-path override to re-invoke the same Python fence without --resume-phase, or add explicit resume-phase parser/support if that is intended


### FINDING_7: Quiet-routing callsites can hide operator-visible warnings/progress
- **Reviewer(s)**: Cursor-Requirements, Codex-Requirements, Codex-dyn-io-routing
- **Severity**: important
- **Concern**: Planned quiet-routing changes omit or mishandle `ci_monitor.py` and `run_logs.py` callsites, and using explicit `quiet=True` can suppress messages when quiet setup is inactive or degraded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ### UPDATED: python/ci_monitor.py (drop quiet=False in _warn_stderr or poll_ci progress path) and ### UPDATED: python/run_logs.py (secret-scrub banner uses quiet-aware emit); keep the test_ship fd4 regression
  - From Codex-Requirements: Use the default quiet-aware path by omitting the quiet argument, and list ci_monitor.py/run_logs.py explicitly; test both fd4-after-quiet and normal stderr paths
  - From Codex-dyn-io-routing: Specify that these replacements omit the quiet argument or pass quiet=None; add a no-op/degrade regression that still observes the message on stderr


### FINDING_8: Catch-all traceback still bypasses quiet-aware stderr routing
- **Reviewer(s)**: Cursor-dyn-io-routing, Codex-dyn-io-routing
- **Severity**: important
- **Concern**: The quiet-bypass removal list misses the catch-all internal-error traceback emit, so unexpected exceptions after `quiet_init` can be written only to the quiet log instead of caller-visible stderr.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-io-routing: Remove quiet=False from the catch-all BreadcrumbWriter.emit at ship.py:763-765 (use default quiet=None); add to plan line 40 enumeration alongside _breadcrumb and run_logs secret-scrub; extend test_ship.py operator-visible fd4 regression to cover internal-error traceback after quiet_init
  - From Codex-dyn-io-routing: Include this emit site in the bypass-removal pass and route it through the same quiet-aware default or fd4 diagnostic helper


### FINDING_9: no-logs-commit structural pin can pass without checking Python argv
- **Reviewer(s)**: Codex-dyn-pin-coherence
- **Severity**: important
- **Concern**: A global grep can match existing `--no-logs-commit` occurrences outside the Python invoke fence, leaving the Python branch unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-pin-coherence: Specify an awk/grep window from the LARCH_SHIP_PR_IMPL=python branch start to the else line and assert --no-logs-commit "$no_logs_commit" appears before that else

