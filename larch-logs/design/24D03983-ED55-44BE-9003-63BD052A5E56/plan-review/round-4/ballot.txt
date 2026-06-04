### FINDING_1: SKILL.md still describes bash/restore as the normal finalize-state writer
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan updates some writer bullets and gates, but leaves paired NEVER #11 and Step 18b prose saying `ship-pr.sh`/postmerge is the normal finalize writer and `restore-finalize-state.sh` is the blessed pre-teardown writer. After the Python default flip, this can mislead implementers into preserving bash-only finalize semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After the default flip, agents following Step 18b (~1277) still believe only ship-pr.sh writes finalize-state.sh and restore is always the blessed writer; that fights FINDING_2/#4 (skip restore when Python already wrote finalize) and FINDING_3 (python/ship.py terminal writes) Expand the SKILL.md edit list to rewrite NEVER #11 Why/How (not only the one-line summary at plan ~47) and the Step 18b paragraph before the fenced block so default writers are python/ship.py (terminal outcomes) plus conditional restore-finalize-state.sh; keep restore as reconstruction only for LARCH_SHIP_PR_IMPL=bash or missing finalize-state.sh on the Python path
  - From Cursor-Pragmatic: In the same SKILL.md edit, rewrite NEVER #11 **Why** and the Step 1277 NEVER #11 cross-ref to: default `python/ship.py` writes `$IMPLEMENT_TMPDIR/finalize-state.sh` on terminal driver outcomes; `LARCH_SHIP_PR_IMPL=bash` keeps the bash contract; `restore-finalize-state.sh` runs only on bash opt-in or when `finalize-state.sh` is missing (per Step 18 gate)

### FINDING_2: Python finalize/state writes must preserve invalid-tmpdir no-write guard
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Terminal finalize writes are planned for Python outcomes, but the invalid tmpdir guard is not preserved. If `ctx.tmpdir` is outside approved session roots, best-effort state writes could create files outside the allowed tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Gate every finalize-state and ship-state write, including main exception fallback, with _tmpdir_under_allowed_root(ctx.tmpdir); keep invalid tmpdir as JSON-only/no state

### FINDING_3: Python Exit 6 retry routing lacks a phase-compatible counter
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The Python selector asks for bash-style per-phase retry counters while forbidding ship-pr-state parsing and keeping the JSON envelope unchanged. Since the Python JSON has no `PHASE`, the orchestrator cannot select `ship-pr-net-retries-$PHASE.count` without violating the JSON-only contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define a Python-path retry counter that needs no phase, or add a phase field to JSON and tests; given the no-envelope-change plan, use a fixed Python transient counter

### FINDING_4: Stall recovery/classification omits finalize-state as a stall source
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Requirements
- **Severity**: important
- **Concern**: The plan trusts Python-written `finalize-state.sh`, but stall recovery documentation and classifier paths still resolve stall state from older layers such as memory, `ship-pr-state.sh`, and `session-env.sh`. A Python STALLED outcome may therefore be visible to Step 18a but lost or misclassified during recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Update the reference load and Procedure step 1 to match SKILL.md's four-layer order: memory, ship-pr-state.sh, finalize-state.sh, session-env.sh
  - From Codex-Edge: Add one minimal contract: either have Python terminal state writes update ship-pr-state STALL_TRACKING/STALL_STEP/EXIT_CODE for terminal stalls, or teach stall-recovery-report.sh and stall-recovery.md to read finalize-state as the same fourth stall layer; add a focused py/shell test for a Python stall with finalize-state true and ship-pr-state false.
  - From Codex-Requirements: Update the plan to align stall-recovery.md and its classify path with Step 18a's four-layer resolve by reading finalize-state.sh, or explicitly have the Python terminal-state write set durable STALL_TRACKING/STALL_STEP in ship-pr-state.sh for stalled outcomes.

### FINDING_5: Post-merge flush-skip STALLED path can leave non-stall finalize-state
- **Reviewer(s)**: Cursor-Edge, Cursor-Requirements
- **Severity**: important
- **Concern**: `run_postmerge_phase` writes `finalize-state.sh` before the post-merge flush skip check. If the flush skip returns STALLED, the Python path may skip restore because finalize already exists, leaving teardown with stale non-stall state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Extend FINDING_3 to require rewriting finalize-state.sh (stall_tracking=true, stall_step for post-merge flush) on the flush-skip return path, or call _write_terminal_state from run_ship when post.outcome is STALLED
  - From Cursor-Requirements: Add the flush-skip branch to FINDING_3 (and implement _write_terminal_state or equivalent there) so terminal STALLED outcomes always refresh finalize-state.sh after the skip decision

### FINDING_6: Terminal finalize writes are over-broad for transient and needs-user outcomes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan mandates finalize-state before every terminal Python `ShipResult`, including transient retry handoffs and needs-user routing. That can create premature/incomplete finalize-state that causes Step 18 to skip restore even though selector re-entry or follow-up routing still needs merged disk state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Mid-loop exit 6 or oos-filing exit 3 can leave a premature finalize-state.sh; Step 18 then skips restore-finalize-state.sh whenever finalize exists, so teardown may use incomplete ctx-only state instead of merged ship-pr-state.sh Narrow FINDING_3: write finalize only on paths that already do today (postmerge success, existing _write_terminal_state stalls to Step 16) plus outer main() hard failures; exclude Outcome.TRANSIENT and NEEDS_USER_INPUT outcomes that immediately re-invoke the selector; keep Step 18 restore when finalize is missing

### FINDING_7: Step 18 skip-restore gate can use stale finalize-state after later ship-pr-state mutations
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The Python path skips restore whenever `finalize-state.sh` exists, but later prompt-side or recovery transitions can update `ship-pr-state.sh` with terminal overrides. Teardown can then read stale finalize flags and perform the wrong DONE/STALLED/user-bail cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Run restore on the Python path when ship-pr-state.sh has post-driver terminal overrides such as STALL_TRACKING or BAIL_NEEDS_USER_INPUT, or otherwise refresh finalize-state.sh after those prompt-side transitions; skip restore only when finalize-state.sh is current and no later disk state mutation occurred.
  - From Codex-Pragmatic: Restore when finalize-state.sh is missing or ship-pr-state.sh has terminal fields that require teardown, at minimum STALL_TRACKING=true, BAIL_NEEDS_USER_INPUT=true, or changed STALL_STEP; skip only when finalize-state is known current

### FINDING_8: Python terminal writer does not overlay bash-compatible outcome keys
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: Python terminal writes preserve seeded bash state keys, but do not set outcome-derived terminal fields consumed by final reports and recovery. Default STALLED or NEEDS_USER_INPUT outcomes can therefore produce wrong report text or recovery `EXIT_CODE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Extend the terminal writer to overlay outcome-derived EXIT_CODE, STALL_TRACKING, STALL_STEP, BAIL_REASON, BAIL_NEEDS_USER_INPUT, FAILED_RUN_ID, and BAIL_FAILURE_DETAIL_LOG where available; ensure final-bail-reason remains restore-compatible

### FINDING_9: Rewritten selector drops committed exit-3 needs_user_reason routing
- **Reviewer(s)**: Cursor-dyn-state-contract-drift
- **Severity**: important
- **Concern**: The planned Python driver selector keeps only abbreviated exit-code routing and omits existing exit-3 `needs_user_reason` dispatch for OOS filing, CI-fix token handling, and JSON `failed_run_id` handling before user questions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-state-contract-drift: Carry forward the full exit-3 JSON routing prose from `skills/implement/SKILL.md` (~955) into the new selector paragraph; do not replace it with the abbreviated routing in plan.txt:27-29 alone.

### FINDING_10: conflict-resolution.md still revives bash-only resume semantics
- **Reviewer(s)**: Cursor-dyn-cross-doc-sweep
- **Severity**: important
- **Concern**: The plan omits `conflict-resolution.md`, but SKILL.md still mandatory-loads it for `ship_pr_pre_push`. That reference tells the orchestrator to re-invoke `ship-pr.sh --resume-phase ship-pr-rrr-phase14`, which has no default Python contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-cross-doc-sweep: Default Python path: re-invoke the Step 8+ selector `python3 …/python/ship.py` foreground argv (with `--state-file`); keep `ship-pr.sh --resume-phase ship-pr-rrr-phase14` bash-only. Add this file to the plan’s updated-file list (minimal qualifier edits, same pattern as stall-recovery / SKILL Exit 4 bullets)

### FINDING_11: Consumer docs still describe ship-pr.sh as the live default writer/driver
- **Reviewer(s)**: Codex-dyn-cross-doc-sweep
- **Severity**: important
- **Concern**: The update list omits docs that still name `ship-pr.sh` as the active Step 8+ CI-fix, log-refresh, and final-summary writer. The planned grep sweep may not catch plain references, leaving consumer docs inconsistent with the Python default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-doc-sweep: Add docs/workflow-lifecycle.md and docs/run-logs.md to UPDATED, reword these passages to the active Step 8+ driver/default Python path, and qualify scripts/ship-pr.sh as the bash opt-in path where needed; skills/pause/SKILL.md needs no change.

### FINDING_12: Planned py-test coverage is underspecified for state merge and terminal finalize behavior
- **Reviewer(s)**: Cursor-dyn-test-pin-fidelity, Codex-dyn-test-pin-fidelity
- **Severity**: important
- **Concern**: The testing strategy names `_write_ship_state` merge and terminal finalize behavior, but does not specify concrete seeded fixtures, preserved key sets, or terminal-path assertions. Shallow tests could miss state-loss regressions and finalize gaps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-pin-fidelity: Add one focused test: pre-seed `STALL_TRACKING=true` (plus one other orchestrator-only key), call `_write_ship_state`, assert preserved keys; add parametrized terminal-path tests that assert `finalize-state.sh` exists for OOS, invalid tmpdir, and at least one exception path
  - From Codex-dyn-test-pin-fidelity: Add a concrete `python/test_ship.py` case: seed `ship-pr-state.sh` with representative preserved keys, call `_write_ship_state` or a short `run_ship` path, then assert those keys remain unchanged while Python-managed keys such as `PHASE`, `PR_NUMBER`, and counters are overwritten.

### FINDING_13: Negative structure pin is too exact-string dependent
- **Reviewer(s)**: Codex-dyn-test-pin-fidelity
- **Severity**: important
- **Concern**: The planned negative test only checks an exact string, so old bash-default selector semantics could survive with line wrapping or whitespace changes while passing the test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-pin-fidelity: Use a selector-scoped regex negative, e.g. fail if the Python selector paragraph matches `default[[:space:]]+\`LARCH_SHIP_PR_IMPL=bash\`[[:space:]]+runs[[:space:]]+the[[:space:]]+bash[[:space:]]+contract`.
