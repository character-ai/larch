### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/finalize.py:344-378
- **Concern**: Gap-fill says merge read_finalize_state keys then call write_finalize_state but write_finalize_state rebuilds all keys from RunContext only. Scenario: write_finalize_state overwrites the file from ctx fields; preserved keys from read_finalize_state are dropped unless every field is hydrated into ctx first
- **Proposed resolution**: Specify a merge writer (e.g. write_finalize_state_merged(path, base, overrides) or ctx hydration from read_finalize_state + ShipResult + ship-pr-state) instead of implying write_finalize_state performs dict merge

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:344-378
- **Concern**: Plan requires gap-fill to merge and preserve all existing finalize-state keys, but the only planned writer still takes RunContext and rewrites a fixed key set. Scenario: _persist_stall_metadata_if_needed either cannot call write_finalize_state with the merged dict or will drop present keys while trying to set STALL_TRACKING=true
- **Proposed resolution**: Add a small dict-based finalize-state writer, or extend write_finalize_state to accept merged state data and use it for both RunContext serialization and gap-fill preservation

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: python/ship.py:680-685
- **Concern**: 1. Invalid-tmpdir STALLED is not actually JSON-only because emit_result still appends the journal when run_id is set. Scenario: Direct invocation passes --tmpdir outside the allowlist plus --run-id; run_ship returns STALLED invalid tmpdir, but emit_result attempts to create larch-journal under that rejected path, violating the proposed no-write edge and tmpdir containment model
- **Proposed resolution**: Skip journal append unless ctx.tmpdir passes the same allowed-root check, or pass a journal_allowed flag from main; add the invalid-tmpdir regression to assert no finalize-state and no journal sidecar

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1064
- **Concern**: Exit 4 python prose assigns RESUME_PHASE and CALLER_KIND to finalize-state reads. Scenario: Python never writes those keys to finalize-state (lib-finalize-state-keys.sh and write_finalize_state omit them; _write_ship_state persists them only in ship-pr-state.sh). Orchestrator prose/pins that read finalize-state for RESUME_PHASE/CALLER_KIND will miss values even when ship-pr-state has them.
- **Proposed resolution**: Split Exit 4 python reads: STALL_TRACKING/STALL_STEP from finalize-state.sh (JSON detail fallback when absent); RESUME_PHASE/CALLER_KIND from ship-pr-state.sh. Add RESUME_PHASE/CALLER_KIND to the post-invoke scoped ship-pr-state key list (~L1045). Mirror in test-implement-structure.sh A2b pins.

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1309-1318; scripts/restore-finalize-state.sh:77-86; python/ship.py:365-389
- **Concern**: Python stall metadata can be clobbered before teardown. Scenario: The plan writes gap-fill STALL_TRACKING=true to finalize-state.sh, but Python ship-pr-state.sh does not carry STALL_TRACKING. Step 18b still restores finalize-state.sh from ship-pr-state.sh whenever that file exists, defaulting missing STALL_TRACKING to false. A valid-tmpdir early ensure_pr stall can therefore lose its stall state before teardown, causing cleanup and title routing to treat it as non-stalled.
- **Proposed resolution**: Make the Python path restore-safe: skip restore-finalize-state.sh when the Python driver already wrote finalize-state.sh, or update restore-finalize-state.sh to preserve existing finalize-state STALL_TRACKING=true and STALL_STEP when ship-pr-state.sh lacks those keys. Add a structural/unit pin for this handoff.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/logging_util.py:45-49
- **Concern**: python/config.py:75. Scenario: quiet_init() does not spell out formatting PATH_QUIET_LOG_TEMPLATE
- **Proposed resolution**: Implementer may join tmpdir without substituting {script} and {pid}, yielding a literal larch-quiet-{script}-{pid}.log path; quiet logs miss run-log publish patterns and IMPLEMENT_TMPDIR-only invocations get wrong log dirs In quiet_init(), mirror scripts/lib-quiet.sh:37: resolve tmpdir from IMPLEMENT_TMPDIR then TMPDIR (and optionally ctx.tmpdir via main() setdefault before the call); format PATH_QUIET_LOG_TEMPLATE with script=ship.py (or Path(argv[0]).name), pid=os.getpid(), tmpdir=resolved; add a unit test asserting the path shape matches larch-quiet-ship.py-<pid>.log

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:344-378
- **Concern**: Finding 1: stall gap-fill says to preserve all existing finalize-state keys but still routes the merged write through the current RunContext-only writer. Scenario: Existing write_finalize_state rebuilds a fixed key set from RunContext, so gap-fill would drop present keys such as RESUME_PHASE or CALLER_KIND that the plan later tells the Python exit-4 path to read from finalize-state.sh
- **Proposed resolution**: Add a minimal mapping-based atomic writer or extend write_finalize_state to accept the merged dict; validate key syntax and newline-free values, then add a preservation regression

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1049-1067, python/ship.py:698-716
- **Concern**: Finding 2: Python OOS re-entry is not reconciled with the unsupported --resume-phase flag. Scenario: The shared OOS checkpoint still says to re-enter with --resume-phase pr-create, but ship.py has no such parser flag; under the new argparse envelope this becomes INTERNAL_ERROR exit 1 after a Python OOS checkpoint succeeds
- **Proposed resolution**: Add a Python-path override to re-invoke the same Python fence without --resume-phase, or add explicit resume-phase parser/support if that is intended

### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:40,131-133; python/ci_monitor.py:192-193; python/run_logs.py:975
- **Concern**: B4 quiet-routing edits name ci_monitor and run_logs call sites but Files omits both modules (test_ci_monitor.py is comment-only). Scenario: After quiet_init, poll progress and secret-scrub banners still pass quiet=False and write only to the redirected log; acceptance B4/operator-visible warnings fails despite ship.py-only edits
- **Proposed resolution**: Add ### UPDATED: python/ci_monitor.py (drop quiet=False in _warn_stderr or poll_ci progress path) and ### UPDATED: python/run_logs.py (secret-scrub banner uses quiet-aware emit); keep the test_ship fd4 regression

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/finalize.py:344-378
- **Concern**: Gap-fill requires preserving all finalize-state keys, but the plan only adds a reader and still routes writes through RunContext-only write_finalize_state. Scenario: Existing finalize-state keys that are not represented by the pre-run RunContext can be clobbered, violating the no-clobber stall-metadata contract
- **Proposed resolution**: Add a dict-based atomic finalize-state writer or extend write_finalize_state to accept a merged dict; test preservation with an extra pre-seeded key

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: python/logging_util.py:32-47; python/ship.py:100-103; python/ci_monitor.py:192-193; python/run_logs.py:960-975
- **Concern**: Plan allows forcing quiet=True at progress and warning callsites; current BreadcrumbWriter can drop quiet=True messages when quiet is not active. Scenario: If quiet_init degrades to no-op or helpers run directly, CI progress or secret-scrub warnings can disappear instead of reaching stderr
- **Proposed resolution**: Use the default quiet-aware path by omitting the quiet argument, and list ci_monitor.py/run_logs.py explicitly; test both fd4-after-quiet and normal stderr paths

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-io-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:763-765
- **Concern**: Plan omits catch-all traceback emit from quiet=False removal list. Scenario: After quiet_init, main()'s except handler emits traceback with quiet=False, bypassing fd4 routing; traceback lands only in the quiet log while contract JSON may still reach fd3 — operators lose the internal-error traceback on caller-visible stderr
- **Proposed resolution**: Remove quiet=False from the catch-all BreadcrumbWriter.emit at ship.py:763-765 (use default quiet=None); add to plan line 40 enumeration alongside _breadcrumb and run_logs secret-scrub; extend test_ship.py operator-visible fd4 regression to cover internal-error traceback after quiet_init

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-io-routing
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/logging_util.py:45-62; python/ship.py:100-102; python/ci_monitor.py:192-193; python/run_logs.py:960-975
- **Concern**: Plan allows replacing quiet=False bypasses with quiet=True, but quiet=True suppresses output when quiet_init no-ops or setup degrades. Scenario: With LARCH_QUIET_ACTIVE=1 and empty LARCH_QUIET_PID, or a quiet setup failure before fd4/log exists, progress and secret-scrub warnings can disappear instead of falling back to caller-visible stderr
- **Proposed resolution**: Specify that these replacements omit the quiet argument or pass quiet=None; add a no-op/degrade regression that still observes the message on stderr

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-io-routing
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/ship.py:755-768
- **Concern**: The quiet=False removal list misses the catch-all internal-error breadcrumb. Scenario: After quiet_init, an unexpected exception writes the traceback breadcrumb to redirected stderr/quiet log only, not the original stderr/fatal diagnostic path that lib-quiet reserves for user-visible fatals
- **Proposed resolution**: Include this emit site in the bypass-removal pass and route it through the same quiet-aware default or fd4 diagnostic helper

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-pin-coherence
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1045-1067 planned edit; python/ship.py:365-382; python/finalize.py:348-369
- **Concern**: Planned boundary prose says Python continuation keys come from finalize-state.sh for stall/OOS/PR fields, but current Python writes OOS_PENDING to ship-pr-state.sh and finalize-state.sh has no OOS_PENDING field. Scenario: If implemented literally, Step 8+ can direct Python runs to read OOS_PENDING from the wrong file while the later OOS checkpoint pin still passes
- **Proposed resolution**: Change the boundary wording to stall/PR fields from finalize-state.sh and PHASE/OOS_PENDING/FORKED_TARGET/REPO_UNAVAILABLE from ship-pr-state.sh; scope any structural assertion to that boundary window

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-pin-coherence
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:934,1003-1040; scripts/test-implement-structure.sh planned
- **Concern**: FINDING_4 pin can false-pass unless scoped to the Python invoke fence because --no-logs-commit already appears in Step 7a and the bash ship-pr.sh fence while the Python branch currently lacks it. Scenario: A global grep for --no-logs-commit "$no_logs_commit" can pass without proving the Python argv was fixed, leaving LARCH_SHIP_PR_IMPL=python to ignore no_logs_commit
- **Proposed resolution**: Specify an awk/grep window from the LARCH_SHIP_PR_IMPL=python branch start to the else line and assert --no-logs-commit "$no_logs_commit" appears before that else
