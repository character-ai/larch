### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/stall-recovery-report.sh:566-625
- **Concern**: FINDING_4 four-layer resolve is mandatory for classify but plan keeps the script update conditional. Scenario: Step 18a SKILL resolves STALL_TRACKING across finalize-state.sh yet classify still reads only ship-pr-state.sh and session-env.sh so stall metadata present only in Python-written finalize can yield RESUME_HINT=none or wrong FAILURE_CLASS before Step 18b restore
- **Proposed resolution**: Make stall-recovery-report.sh classify update mandatory (drop the if classify reads only three layers guard) and add a test-stall-recovery-report.sh case where finalize-state.sh alone carries STALL_TRACKING/STALL_STEP

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:468-469
- **Concern**: FINDING_5 fixes flush-skip stall finalize inside run_postmerge_phase but leaves the caller-side unconditional _write_ship_state(..., phase="done"). Scenario: Any STALLED return from run_postmerge_phase (postmerge failure or flush-skip) still writes PHASE=done into ship-pr-state.sh without STALL_* / EXIT_CODE overlays, contradicting stall-shaped finalize and breaking Step 18 restore skip / 18a classify (PHASE=done while finalize is stalled)
- **Proposed resolution**: Only call _write_ship_state(phase="done") when post.outcome is Outcome.OK; on STALLED delegate to _write_terminal_state (or skip the done write) so merged ship-pr-state matches terminal finalize; extend FINDING_12 to assert ship-pr-state stall keys after flush-skip/postmerge stall

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:~955-1038
- **Concern**: Python Exit 6 selector says 4th TRANSIENT failure is treated as Exit 4 stall but omits bash's STALL_TRACKING persistence step. Scenario: After the 4th python/ship.py Exit 6 the driver still emits TRANSIENT JSON (not STALLED); without a prompt-side key rewrite of STALL_TRACKING=true (and related stall keys) into ship-pr-state.sh, Step 18a four-layer gate can miss the stall and teardown may take the [DONE] branch
- **Proposed resolution**: Carry the bash Exit 6 escalation clause into the Python driver selector: on 4th ship-pr-net-retries-python.count failure set in-memory STALL_TRACKING=true and key-rewrite ship-pr-state.sh before continuing to Step 16/18

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:477-478
- **Concern**: FINDING_3/6 omit `run_ship` outer `except` for `Stalled`/`ShipError`. Scenario: `rebase.rebase_and_push` and other paths raise `Stalled`; handler returns JSON exit 4 with no `_write_terminal_state`, no stall keys in `ship-pr-state.sh`, and Step 18 restore/skip gate sees missing or success-shaped finalize
- **Proposed resolution**: Route caught `Stalled` (and other terminal errors you treat as exit 4) through the same `_write_terminal_finalize_if_terminal` helper when `_tmpdir_under_allowed_root`; keep `TransientNetworkError`/`NeedsUserInput` on the no-finalize list

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1035
- **Concern**: FINDING_9 verbatim carry-forward of Exit-3 step 10 keeps `SHIP_PR_STATE_FILE=$IMPLEMENT_TMPDIR/finalize-state.sh` on the Python path while FINDING_3/6 forbid `finalize-state.sh` on `NEEDS_USER_INPUT` / immediate re-entry. Scenario: After a default-path Exit 3 (`first-fixer-non-health`, `ci-fix-exhausted`, `oos-filing`, etc.), autonomous CI-fix step 10 calls `refresh-run-logs.sh` with a missing finalize file; the script fail-closes with `REFRESH_SKIPPED=true REASON=state-file-missing-fail-closed`, so token/timing/final-summary refresh before push is skipped on the now-default driver
- **Proposed resolution**: When editing Exit-3 prose, qualify step 10: on the default Python path use `--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"` (merged via `--state-file`); reserve `finalize-state.sh` for terminal outcomes or bash opt-in

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-state-key-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/ship.py:223-224
- **Concern**: Merge overlay still includes RESUME_PHASE and CALLER_KIND as empty strings in the Python-managed fields map. Scenario: Every --state-file refresh overwrites orchestrator handoff tokens (e.g. ship_pr_pre_push sets RESUME_PHASE=ship-pr-rrr-phase14) before the next selector re-invoke; Python-path conflict classification and Phase-4 recovery lose durable resume metadata
- **Proposed resolution**: Keep these keys in the preserved set only: omit them from routine phase overlays, or merge rule keep existing non-empty RESUME_PHASE/CALLER_KIND when the write set would blank them

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-pin-text-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:987-989
- **Concern**: Selector awk end anchor `Invoke:` is ambiguous: recovery blockquote at 987 contains `` `Invoke:` `` before the standalone `Invoke:` heading at 989. Scenario: Naive awk from `**Python driver selector:**` through "line before `Invoke:`" stops at 987, excluding pre-`Invoke:` routing/trailer (988+) and any full exit-3 carry-forward placed after recovery; window semantics drift from plan intent
- **Proposed resolution**: Pin the end delimiter to the standalone heading only (e.g. `^Invoke:[[:space:]]*$`) or reword bash-only recovery prose to drop the `` `Invoke:` `` token before the fenced heading; document the anchor in test-implement-structure.md

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-operator-rollout
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/installation-and-setup.md:30-44,279-285
- **Concern**: Operator notice lacks a doc anchor and Workflow automation prerequisites omit Python 3.12+. Scenario: FINDING_8 is free-floating prose with no placement under #### Upgrade (30-44), no tie-in to Plugin cache vs. working-tree (77-92), and no bullet under ### Workflow automation (279-285) where /implement --merge lists git/gh/jq only; operators can start /implement without seeing Step 8+ needs python3 3.12+ until Step 8 fails
- **Proposed resolution**: Anchor the notice in #### Upgrade after the restart guidance (38) and extend ### Workflow automation with python3 3.12+ plus LARCH_SHIP_PR_IMPL=bash escape; cross-link the cache subsection (77-92)
