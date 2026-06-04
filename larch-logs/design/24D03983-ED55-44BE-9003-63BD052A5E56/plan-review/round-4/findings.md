### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:52-52
- **Concern**: skills/implement/SKILL.md:1277. Scenario: NEVER #11 and Step 18b prose still name ship-pr.sh as the only finalize writer and restore-finalize-state.sh as the sole blessed pre-teardown writer
- **Proposed resolution**: After the default flip, agents following Step 18b (~1277) still believe only ship-pr.sh writes finalize-state.sh and restore is always the blessed writer; that fights FINDING_2/#4 (skip restore when Python already wrote finalize) and FINDING_3 (python/ship.py terminal writes) Expand the SKILL.md edit list to rewrite NEVER #11 Why/How (not only the one-line summary at plan ~47) and the Step 18b paragraph before the fenced block so default writers are python/ship.py (terminal outcomes) plus conditional restore-finalize-state.sh; keep restore as reconstruction only for LARCH_SHIP_PR_IMPL=bash or missing finalize-state.sh on the Python path

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/ship.py:284-287
- **Concern**: Terminal finalize writes are specified for every Python outcome but the plan does not preserve the invalid-tmpdir no-write guard. Scenario: If ctx.tmpdir is outside approved session roots, best-effort finalize-state writing could create files outside the allowed tmpdir before returning JSON
- **Proposed resolution**: Gate every finalize-state and ship-state write, including main exception fallback, with _tmpdir_under_allowed_root(ctx.tmpdir); keep invalid tmpdir as JSON-only/no state

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:955,1040
- **Concern**: Python Exit 6 routing asks for bash-style per-phase retry counters while also forbidding ship-pr-state parsing and keeping the JSON envelope unchanged. Scenario: The Python JSON result has no PHASE, so the orchestrator cannot choose ship-pr-net-retries-$PHASE.count without violating the JSON-only continuation contract
- **Proposed resolution**: Define a Python-path retry counter that needs no phase, or add a phase field to JSON and tests; given the no-envelope-change plan, use a fixed Python transient counter

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:7-13
- **Concern**: Stall recovery still resolves only three STALL_TRACKING layers and omits finalize-state. Scenario: Python default stalls may only be durable in finalize-state.sh; Step 18a can load recovery from that layer, but the reference can re-resolve without it and skip classification or retry
- **Proposed resolution**: Update the reference load and Procedure step 1 to match SKILL.md's four-layer order: memory, ship-pr-state.sh, finalize-state.sh, session-env.sh

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:266-271
- **Concern**: FINDING_3 omits post-merge flush-skip stall finalize refresh. Scenario: run_postmerge_phase writes finalize-state.sh at line 266 then can return Outcome.STALLED when flush_logs_post skips (line 270-271); default Python path skips Step 18 restore when finalize exists, leaving STALL_TRACKING=false for a stalled run and breaking [STALLED] teardown/rename
- **Proposed resolution**: Extend FINDING_3 to require rewriting finalize-state.sh (stall_tracking=true, stall_step for post-merge flush) on the flush-skip return path, or call _write_terminal_state from run_ship when post.outcome is STALLED

### FINDING_6:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:175-181; skills/implement/scripts/stall-recovery-report.sh:566-643
- **Concern**: Python terminal stalls are written to finalize-state but the proposed plan leaves ship-pr-state stall keys stale and the stall classifier ignores finalize-state. Scenario: On a default Python STALLED outcome, Step 18a may see finalize-state STALL_TRACKING=true, but classification still reads only ship-pr-state/session-env; with preserved STALL_TRACKING=false it can classify as unrecoverable or skip recovery instead of resuming step8-shippr
- **Proposed resolution**: Add one minimal contract: either have Python terminal state writes update ship-pr-state STALL_TRACKING/STALL_STEP/EXIT_CODE for terminal stalls, or teach stall-recovery-report.sh and stall-recovery.md to read finalize-state as the same fourth stall layer; add a focused py/shell test for a Python stall with finalize-state true and ship-pr-state false.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:477-478
- **Concern**: skills/implement/SKILL.md:27-28. Scenario: FINDING_3 mandates finalize-state.sh before every terminal ShipResult including TransientNetworkError and retry-handoff NEEDS_USER_INPUT; bash ship-pr only calls write_finalize_state in run_postmerge_phase and exit_transient_net never writes finalize
- **Proposed resolution**: Mid-loop exit 6 or oos-filing exit 3 can leave a premature finalize-state.sh; Step 18 then skips restore-finalize-state.sh whenever finalize exists, so teardown may use incomplete ctx-only state instead of merged ship-pr-state.sh Narrow FINDING_3: write finalize only on paths that already do today (postmerge success, existing _write_terminal_state stalls to Step 16) plus outer main() hard failures; exclude Outcome.TRANSIENT and NEEDS_USER_INPUT outcomes that immediately re-invoke the selector; keep Step 18 restore when finalize is missing

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1277-1288; skills/implement/references/stall-recovery.md:65-85
- **Concern**: Python Step 18 skip-restore gate can ignore later disk state changes. Scenario: Plan says default Python skips restore whenever finalize-state.sh exists, but stall recovery and Step 12d update ship-pr-state.sh after the driver exits and are forbidden from editing finalize-state.sh; a Python stall that is cleared, terminal-seeded, or converted to user-bail can reach teardown with stale finalize-state.sh flags and get the wrong DONE/STALLED cleanup behavior
- **Proposed resolution**: Run restore on the Python path when ship-pr-state.sh has post-driver terminal overrides such as STALL_TRACKING or BAIL_NEEDS_USER_INPUT, or otherwise refresh finalize-state.sh after those prompt-side transitions; skip restore only when finalize-state.sh is current and no later disk state mutation occurred.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:52-53,1277
- **Concern**: Plan updates NEVER #11 writer bullets and the Step 18 restore shell gate (~1281-1290) but not the paired NEVER #11 **Why** or Step 18b Title-prefix prose, which still say the normal ship path is `ship-pr.sh` and finalize is produced during postmerge only. Scenario: After the default flip, an implementer can patch the selector/restore gate yet leave Why/cross-ref claiming only bash `ship-pr.sh` writes `finalize-state.sh`, so prompt-side guidance still treats restore as the normal writer and under-specifies `python/ship.py` terminal finalize (FINDING_3)
- **Proposed resolution**: In the same SKILL.md edit, rewrite NEVER #11 **Why** and the Step 1277 NEVER #11 cross-ref to: default `python/ship.py` writes `$IMPLEMENT_TMPDIR/finalize-state.sh` on terminal driver outcomes; `LARCH_SHIP_PR_IMPL=bash` keeps the bash contract; `restore-finalize-state.sh` runs only on bash opt-in or when `finalize-state.sh` is missing (per Step 18 gate)

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1277-1290
- **Concern**: Proposed Step 18 skips restore whenever Python has written finalize-state.sh, even if ship-pr-state.sh was changed later. Scenario: After Python exits transient or needs-user and the selector or Step 18a marks STALL_TRACKING=true in ship-pr-state.sh, finalize-state.sh can still say false; teardown then treats the run as non-stalled and may clean up artifacts
- **Proposed resolution**: Restore when finalize-state.sh is missing or ship-pr-state.sh has terminal fields that require teardown, at minimum STALL_TRACKING=true, BAIL_NEEDS_USER_INPUT=true, or changed STALL_STEP; skip only when finalize-state is known current

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/ship.py:175-225; skills/implement/scripts/write-final-report.sh:88-95; skills/implement/scripts/stall-recovery-report.sh:657-668
- **Concern**: Terminal Python writes preserve seeded bash state keys but do not set bash-compatible terminal keys for the actual outcome. Scenario: Default Python returns STALLED or NEEDS_USER_INPUT; final report and stall recovery consume EXIT_CODE, BAIL_REASON, BAIL_NEEDS_USER_INPUT, and related state, so defaults can produce wrong outcome text or EXIT_CODE=0 in recovery reports
- **Proposed resolution**: Extend the terminal writer to overlay outcome-derived EXIT_CODE, STALL_TRACKING, STALL_STEP, BAIL_REASON, BAIL_NEEDS_USER_INPUT, FAILED_RUN_ID, and BAIL_FAILURE_DETAIL_LOG where available; ensure final-bail-reason remains restore-compatible

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:266-271
- **Concern**: FINDING_3 terminal-finalize list omits post-merge flush-skip STALLED return. Scenario: In run_postmerge_phase, finalize-state.sh is written for OK-shaped state_ctx, then a skipped post-merge flush returns Outcome.STALLED without rewriting stall-shaped finalize; default Python runs that skip restore when finalize exists, so Step 18 teardown can see non-stall finalize while the driver exited STALLED
- **Proposed resolution**: Add the flush-skip branch to FINDING_3 (and implement _write_terminal_state or equivalent there) so terminal STALLED outcomes always refresh finalize-state.sh after the skip decision

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/stall-recovery.md:7-17
- **Concern**: Plan trusts Python-written finalize-state but leaves stall recovery resolving STALL_TRACKING from only in-memory ship-pr-state and session-env. Scenario: Python default exits STALLED after _write_ship_state preserves seeded STALL_TRACKING=false; Step 18a may enter via finalize-state, then stall-recovery step 1 can re-resolve no stall or classify from stale state
- **Proposed resolution**: Update the plan to align stall-recovery.md and its classify path with Step 18a's four-layer resolve by reading finalize-state.sh, or explicitly have the Python terminal-state write set durable STALL_TRACKING/STALL_STEP in ship-pr-state.sh for stalled outcomes.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-state-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:27-29 / skills/implement/SKILL.md:955
- **Concern**: The rewritten Python driver selector keeps only exit codes 0/6/3/4 and drops the committed exit-3 `needs_user_reason` dispatch (`oos-filing` → Step 9a.1, CI-fix tokens, JSON `failed_run_id` before AskUserQuestion).. Scenario: Implementers following the plan alone can ship a default-Python SKILL that no longer tells the orchestrator how to run OOS filing or autonomous CI-fix after exit 3.
- **Proposed resolution**: Carry forward the full exit-3 JSON routing prose from `skills/implement/SKILL.md` (~955) into the new selector paragraph; do not replace it with the abbreviated routing in plan.txt:27-29 alone.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-cross-doc-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/references/conflict-resolution.md:15,107
- **Concern**: Plan omits `conflict-resolution.md` while SKILL.md Exit 4 still MANDATORY-loads it for `ship_pr_pre_push`. Scenario: Phase 4 exit 0 still tells the orchestrator to re-invoke `ship-pr.sh --resume-phase ship-pr-rrr-phase14`; on the default Python path that revives bash-only resume semantics the plan forbids (`--resume-phase` has no Python contract)
- **Proposed resolution**: Default Python path: re-invoke the Step 8+ selector `python3 …/python/ship.py` foreground argv (with `--state-file`); keep `ship-pr.sh --resume-phase ship-pr-rrr-phase14` bash-only. Add this file to the plan’s updated-file list (minimal qualifier edits, same pattern as stall-recovery / SKILL Exit 4 bullets)

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-cross-doc-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/workflow-lifecycle.md:108-110; docs/run-logs.md:363-365,381-383,433-440
- **Concern**: The file list omits docs that still name ship-pr.sh as the live Step 8+ CI-fix, log-refresh, and final-summary writer.. Scenario: The plan's rg sweep will not catch these plain ship-pr.sh references, so after the default flips to python/ship.py, consumer docs still imply the bash path owns default shipping behavior.
- **Proposed resolution**: Add docs/workflow-lifecycle.md and docs/run-logs.md to UPDATED, reword these passages to the active Step 8+ driver/default Python path, and qualify scripts/ship-pr.sh as the bash opt-in path where needed; skills/pause/SKILL.md needs no change.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-test-pin-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_ship.py:192-217
- **Concern**: `make py-test` coverage for `_write_ship_state` merge and terminal `finalize-state.sh` is prose-only with no concrete fixtures. Scenario: The plan’s Testing strategy names merge/finalize behavior but does not specify seeded `ship-pr-state.sh` inputs, overlay keys, or expected preserved-key sets; `test_ship_writes_phase_state` starts from an empty state file and mocks `write_finalize_state`, so merge regressions and several FINDING_3 gaps (`_oos_gate` at python/ship.py:159-163, invalid tmpdir at :291, outer `except` → `_error_to_result` at :477-478) can ship untested
- **Proposed resolution**: Add one focused test: pre-seed `STALL_TRACKING=true` (plus one other orchestrator-only key), call `_write_ship_state`, assert preserved keys; add parametrized terminal-path tests that assert `finalize-state.sh` exists for OOS, invalid tmpdir, and at least one exception path

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-test-pin-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:953-955; scripts/test-implement-structure.sh:24-30
- **Concern**: The planned negative pin is exact-string only, so it is too weak for the old bash-default sentence with line wrapping or whitespace drift.. Scenario: `default \`LARCH_SHIP_PR_IMPL=bash\` runs` plus a newline before `the bash contract` would keep the old default semantics while passing the planned `grep -Fq` absence check.
- **Proposed resolution**: Use a selector-scoped regex negative, e.g. fail if the Python selector paragraph matches `default[[:space:]]+\`LARCH_SHIP_PR_IMPL=bash\`[[:space:]]+runs[[:space:]]+the[[:space:]]+bash[[:space:]]+contract`.

### FINDING_19:
- **Reviewer(s)**: Codex-dyn-test-pin-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:188-228; python/test_ship.py:192-218
- **Concern**: The plan requires `_write_ship_state` merge semantics but does not specify concrete `make py-test` inputs or the expected preserved-key set.. Scenario: An implementation could add a shallow test that preserves one key, while still dropping seeded keys such as `NO_LOGS_COMMIT`, `EXPECTED_SESSION_ID`, `STALL_TRACKING`, or `CI_FIX_REBASE_PENDING`, recreating the state-loss bug.
- **Proposed resolution**: Add a concrete `python/test_ship.py` case: seed `ship-pr-state.sh` with representative preserved keys, call `_write_ship_state` or a short `run_ship` path, then assert those keys remain unchanged while Python-managed keys such as `PHASE`, `PR_NUMBER`, and counters are overwritten.
