### FINDING_1: Manual-merge reconciliation does not clear all terminal-state layers
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Recovery State Integrity
- **Severity**: major
- **Concern**: Reconciliation can mark `ship-pr-state.sh` as merged while stale stall/bail state remains in `finalize-state.sh`, `session-env.sh`, or orchestrator memory. Step 18 can therefore route to stall recovery or render a non-terminal outcome despite a verified merged PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In reconcile-manual-merge, after the merged probe succeeds, write terminal merged finalize-state via the same helper the driver uses (_write_terminal_finalize_if_terminal / write_finalize_state) and clear stall/bail overlays on all three disk layers (ship-pr-state.sh, finalize-state.sh, session-env.sh), reusing the clear_stall file-layer rewrite pattern; add unit/e2e coverage that seeds stale finalize/session stall rows and asserts step-18-gate-finalize reaches finalize-done
  - From Cursor-Arch: Extend the operator-bail / manual-recovery rewrite to require STALL_TRACKING=false (and pass --stall-tracking-memory false) before Steps 16-18 after a successful reconcile-manual-merge; pin this in test-implement-anti-halt and the manual-recovery offline fixture
  - From Cursor-Innovation: In `reconcile-manual-merge`, after the merged probe, reuse `stall-recovery clear-stall` or `_state_layer_paths` to clear `STALL_TRACKING`/`STALL_STEP`/bail keys on all three layers, then write merged terminal ship fields. Pin post-readback in `test_ship_recovery.py`.
  - From Cursor-Requirements: In `ship_recovery.py`, after the merged PR probe, reuse the driver terminal pair (`_write_ship_state(..., phase="done", terminal_outcome=Outcome.OK)` plus `_write_terminal_finalize_if_terminal` / `finalize.write_finalize_state_merged`) to clear stall/bail overlay fields and write merged PR fields into `finalize-state.sh`; extend `test_ship_recovery.py` with a pre-seeded stale `finalize-state.sh` case asserting normalized outcome `merged` and successful post-reconcile render.
  - From Cursor-dyn-Recovery State Integrity: Extend reconcile-manual-merge to clear stall/bail fields in every layer the Step 18 gate reads (at minimum session-env.sh and finalize-state.sh via sanctioned session writers, and document that orchestrator must bind STALL_TRACKING=false / pass --stall-tracking-memory false after RECONCILE_STATUS=ok); add harness coverage in test_ship_recovery.py and test-implement-anti-halt for disk+memory layers after reconcile


### FINDING_2: Assessment proceed path must bypass recovery stall and pre-fix-rebase routing
- **Reviewer(s)**: Cursor-Arch, Cursor-dyn-Recovery State Integrity
- **Severity**: major
- **Concern**: The assessment-unavailable proceed branch is underspecified: it may route through `reship` and pre-fix-rebase or seed Step 12d stall state before the resumed Step 8 run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin proceed-without-assessment to invoke the existing step-8-ship.sh bgjob start/wait pair directly from the operator-bail branch (no NEXT_ACTION=reship), keeping pre-fix-rebase forbidden; mirror the same wording in ship-pr-exit-matrix.md
  - From Cursor-dyn-Recovery State Integrity: In the SKILL and ship-pr-exit-matrix rewrite, make architectural-assessment-unavailable explicitly branch: proceed → waive-assessment + Step 8 reship with no Step 12d and no STALL_TRACKING seed; stop → Step 12d only; keep the global rule that Steps 16-18 run only after recovery completes (reconcile for manual merge, driver postmerge for reship)


### FINDING_6: Manual recovery must preserve durable post-merge records
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: Reconciliation may update only local state after the post-merge sentinel, while post-merge commits are forbidden, leaving committed shipping summaries and in-progress manifests inconsistent with the merged result.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add a compliant pre-merge durable handoff or an explicit reviewable follow-up repair PR, and document how it preserves NEVER #16


### FINDING_7: New ship KV verbs must bypass quiet-mode suppression
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: The new waiver and reconciliation verbs may have their machine-readable stdout suppressed under inherited quiet mode because they are absent from `_MACHINE_STDOUT_KEYS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add ("ship", "waive-assessment") and ("ship", "reconcile-manual-merge") to _MACHINE_STDOUT_KEYS beside the other ship KV verbs. Extend the existing quiet-mode machine-stdout test coverage in python/tests/test_cli.py if the repo pattern requires it.


### FINDING_9: Terminal merged results must override forked-dry-run normalization
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Preserving `FORKED_TARGET=true` can cause a proven manual merge to normalize as forked dry-run because fork handling is evaluated before `MERGE_RESULT=merged`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Update the plan and tests so proven terminal merge results override forked-dry-run without erasing the durable fork flag.


### FINDING_13: Manual reconciliation needs a verified success gate
- **Reviewer(s)**: Codex-dyn-Recovery State Integrity
- **Severity**: major
- **Concern**: Steps 16–18 may proceed after partial reconciliation, such as state and sentinel writes succeeding while manifest writing fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-Recovery State Integrity: Require RECONCILE_STATUS=ok and verified manifest/state postconditions before Steps 16-18; otherwise remain in recovery


### FINDING_2: Clear bail overlays during manual-merge reconciliation
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Reconciliation may leave stale bail-state keys, allowing a verified merged run to normalize back to `bailed-needs-user-input`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Name the bail keys reconcile must clear on all three layers (`BAIL_NEEDS_USER_INPUT`, `BAIL_REASON`, `BAIL_FAILURE_DETAIL_LOG`, etc.) or reuse the same terminal `phase=done` field set as `ship_state._write_ship_state`; post-read verification must fail if any bail overlay remains


