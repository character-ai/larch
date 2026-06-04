### FINDING_1: Stall recovery classify must read finalize-layer stall metadata unconditionally
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The stall recovery classifier update is left conditional even though Step 18a requires four-layer resolution. If `STALL_TRACKING` / `STALL_STEP` exist only in `finalize-state.sh`, classify may still read only `ship-pr-state.sh` and `session-env.sh`, producing `RESUME_HINT=none` or the wrong `FAILURE_CLASS` before Step 18b restore.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Make stall-recovery-report.sh classify update mandatory (drop the if classify reads only three layers guard) and add a test-stall-recovery-report.sh case where finalize-state.sh alone carries STALL_TRACKING/STALL_STEP

### FINDING_2: Caller overwrites stalled postmerge state with PHASE=done
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: `run_postmerge_phase` may return `STALLED`, but the caller still unconditionally writes `phase="done"` to `ship-pr-state.sh`. This can erase or contradict terminal stall state, leaving `PHASE=done` without stall overlays and breaking Step 18 restore/skip and 18a classify behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Only call _write_ship_state(phase="done") when post.outcome is Outcome.OK; on STALLED delegate to _write_terminal_state (or skip the done write) so merged ship-pr-state matches terminal finalize; extend FINDING_12 to assert ship-pr-state stall keys after flush-skip/postmerge stall

### FINDING_3: Python Exit 6 escalation lacks stall-state persistence
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The Python Exit 6 selector treats the fourth transient failure as an Exit 4 stall but omits the bash path’s persistence of `STALL_TRACKING` and related stall keys. After the fourth Python Exit 6, the driver may still emit transient-shaped JSON and leave `ship-pr-state.sh` without durable stall metadata, causing Step 18a or teardown to miss the stall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Carry the bash Exit 6 escalation clause into the Python driver selector: on 4th ship-pr-net-retries-python.count failure set in-memory STALL_TRACKING=true and key-rewrite ship-pr-state.sh before continuing to Step 16/18

### FINDING_4: Outer Python terminal exceptions bypass terminal state writes
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The outer `run_ship` exception handler for `Stalled` / `ShipError` can return exit 4 JSON without writing terminal finalize or stall keys to `ship-pr-state.sh`. Paths such as `rebase.rebase_and_push` may therefore appear missing or success-shaped to Step 18 restore/skip logic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Route caught `Stalled` (and other terminal errors you treat as exit 4) through the same `_write_terminal_finalize_if_terminal` helper when `_tmpdir_under_allowed_root`; keep `TransientNetworkError`/`NeedsUserInput` on the no-finalize list

### FINDING_5: Exit 3 run-log refresh still points at missing finalize-state on Python path
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: Exit 3 prose still carries forward `SHIP_PR_STATE_FILE=$IMPLEMENT_TMPDIR/finalize-state.sh` for step 10, while the Python path intentionally avoids writing `finalize-state.sh` for `NEEDS_USER_INPUT` / immediate re-entry. As a result, `refresh-run-logs.sh` may fail-close with `state-file-missing-fail-closed`, skipping token, timing, and summary refresh before push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: When editing Exit-3 prose, qualify step 10: on the default Python path use `--state-file "$IMPLEMENT_TMPDIR/ship-pr-state.sh"` (merged via `--state-file`); reserve `finalize-state.sh` for terminal outcomes or bash opt-in

### FINDING_6: Python state overlay blanks durable resume metadata
- **Reviewer(s)**: Cursor-dyn-state-key-contract
- **Severity**: important
- **Concern**: The Python-managed merge overlay still includes `RESUME_PHASE` and `CALLER_KIND` as empty strings. Routine `--state-file` refreshes can overwrite non-empty orchestrator handoff values, causing selector re-entry, Python-path conflict classification, and Phase-4 recovery to lose durable resume metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-state-key-contract: Keep these keys in the preserved set only: omit them from routine phase overlays, or merge rule keep existing non-empty RESUME_PHASE/CALLER_KIND when the write set would blank them

### FINDING_7: Python selector extraction anchor can stop at quoted Invoke token
- **Reviewer(s)**: Cursor-dyn-pin-text-fidelity
- **Severity**: important
- **Concern**: The selector awk end anchor `Invoke:` is ambiguous because a recovery blockquote contains `` `Invoke:` `` before the standalone `Invoke:` heading. A naive extraction from `**Python driver selector:**` to the line before `Invoke:` may stop too early and omit routing or exit-3 carry-forward text.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-pin-text-fidelity: Pin the end delimiter to the standalone heading only (e.g. `^Invoke:[[:space:]]*$`) or reword bash-only recovery prose to drop the `` `Invoke:` `` token before the fenced heading; document the anchor in test-implement-structure.md

### FINDING_8: Operator rollout docs omit anchored Python prerequisite notice
- **Reviewer(s)**: Cursor-dyn-operator-rollout
- **Severity**: important
- **Concern**: The operator notice lacks clear placement and workflow automation prerequisites omit Python 3.12+. Operators may start `/implement --merge` after seeing only `git` / `gh` / `jq` requirements and not discover the Python requirement or bash escape hatch until Step 8 fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-operator-rollout: Anchor the notice in #### Upgrade after the restart guidance (38) and extend ### Workflow automation with python3 3.12+ plus LARCH_SHIP_PR_IMPL=bash escape; cross-link the cache subsection (77-92)
